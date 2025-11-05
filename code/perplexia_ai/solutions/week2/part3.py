"""
Assignment 2 — Part 3: Corrective RAG-Lite implementation using LangGraph

This workflow demonstrates intelligent routing between document knowledge
and web search.

Main steps:
1. Load and embed PDF documents into a persistent Chroma vector store.
2. Retrieve relevant document sections.
3. Grade document relevance to decide whether to answer from docs or web.
4. Perform fallback web search when documents are insufficient.
5. Generate concise answers with citations from the chosen source.

Notes:
- Reuses existing ChromaDB if embeddings are already stored.
"""

import json
import time
import os
import os.path as osp
from typing import Dict, List, Optional, TypedDict

from langchain_tavily import TavilySearch
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END
from langchain_community.document_loaders import PyPDFLoader
from langchain.chat_models import init_chat_model
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from perplexia_ai.core.chat_interface import ChatInterface
from perplexia_ai.solutions.week2.prompts import (
    WEB_SEARCH_SUMMARIZER_PROMPT,
    RagGenerationResponse,
    DOCUMENT_RAG_PROMPT,
    DOCUMENT_GRADING_PROMPT,
    DocumentGradingResponse,
)


# TODO: Update these paths to your own local paths
# Document paths
BASE_DIR = "/Users/aish/Downloads/rag_dataset"
FILE_PATHS = [
    osp.join(BASE_DIR, "2019-annual-performance-report.pdf"),
    osp.join(BASE_DIR, "2020-annual-performance-report.pdf"),
    osp.join(BASE_DIR, "2021-annual-performance-report.pdf"),
    osp.join(BASE_DIR, "2022-annual-performance-report.pdf")
]
CHROMA_PERSIST_DIRECTORY = "/Users/aish/chroma_db"


# Graph state definition
class CorrectiveRAGState(TypedDict):
    question: str
    retrieved_docs: str  # Formatted as pretty JSON string
    web_search_results: str  # Formatted as pretty JSON string
    answer: str


class CorrectiveRAGChat(ChatInterface):
    """LangGraph workflow that routes between document RAG and web search."""

    def __init__(self):
        self.llm = None
        self.embeddings = None
        self.vector_store = None
        self.search_tool = None
        self.document_paths = []
        self.graph = None

    # Initialize
    def initialize(self) -> None:
        """
        Initializes components for Corrective RAG:
        - LLM and embeddings
        - Persistent Chroma vector store
        - Tavily search tool
        - LangGraph workflow with conditional routing
        """
        print("Initializing Corrective RAG-Lite system...")

        # Initialize LLM
        self.llm = init_chat_model("gpt-5-mini", model_provider="openai", reasoning_effort="minimal")

        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        # Initialize Tavily search tool
        self.search_tool = TavilySearch(
            max_results=5,
            include_answer=False,
            include_raw_content=False,
            include_images=False,
            search_depth="advanced",
        )

        self.vector_store = Chroma(
            embedding_function=self.embeddings,
            persist_directory=CHROMA_PERSIST_DIRECTORY,
            collection_name="opm_documents",
        )
        # NOTE: This is a quick way to check if the vector store has any documents
        # instead of loading many documents to check.
        has_existing_documents = len(self.vector_store.get(limit=1)['ids']) > 0
        if has_existing_documents:
            print("ChromaDB found - reusing existing embeddings.")
        else:
            print("No existing ChromaDB found - processing and embedding documents...")
            self.document_paths = FILE_PATHS
            docs = self._load_and_process_documents()
            print(f"Loaded and chunked {len(docs)} document pieces")
            self.vector_store.add_documents(docs)
            print("Embeddings processed and stored in ChromaDB.")

            # NOTE: If you are seeing rate limits from OpenAI, you can add documents in batches
            # instead of all at once to handle rate limits
            # batch_size = 100
            # for i in range(0, len(docs), batch_size):
            #     print(f"Adding documents {i}–{i + batch_size} to Chroma...")
            #     self.vector_store.add_documents(docs[i : i + batch_size])
            #     if i + batch_size < len(docs):
            #         time.sleep(10)

        # Build LangGraph workflow
        graph = StateGraph(CorrectiveRAGState)
        graph.add_node("retrieval", self._create_document_retrieval_node)
        graph.add_node("generation", self._create_generation_node)
        graph.add_node("web_search", self._web_search_node)
        graph.add_node("summarize_web_search", self._summarize_web_search_results)

        graph.add_edge(START, "retrieval")
        graph.add_conditional_edges(
            "retrieval",
            self._grade_relevance,
            {"YES": "generation", "NO": "web_search"},
        )
        graph.add_edge("web_search", "summarize_web_search")
        graph.add_edge("summarize_web_search", END)
        graph.add_edge("generation", END)

        self.graph = graph.compile()
        print("Initialization complete. Ready to process queries.")

    # Document loading
    def _load_and_process_documents(self) -> list[Document]:
        """Loads and splits PDF documents into smaller chunks for embedding."""
        docs = []
        for file_path in FILE_PATHS:
            print(f"Loading {osp.basename(file_path)}")
            loader = PyPDFLoader(file_path)
            pages = loader.load()

            combined_text = "\n".join(p.page_content for p in pages)
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200
            )
            chunks = splitter.split_text(combined_text)

            docs.extend(
                [
                    Document(page_content=chunk, metadata={"source": file_path})
                    for chunk in chunks
                ]
            )
        return docs

    # Retrieval
    def _create_document_retrieval_node(self, state: CorrectiveRAGState):
        """
        Retrieves relevant document sections from Chroma.
        Formats documents as pretty JSON before storing in state.
        """
        retriever = self.vector_store.as_retriever(search_kwargs={"k": 10})
        docs = retriever.invoke(state["question"])
        
        # Format retrieved documents as pretty JSON
        formatted_docs = []
        for idx, doc in enumerate(docs, 1):
            filename = osp.basename(doc.metadata.get("source", "unknown"))
            formatted_doc = {
                "id": idx,
                "filename": filename,
                "content": doc.page_content
            }
            formatted_docs.append(formatted_doc)
        
        # Convert to pretty JSON string with newlines between documents
        formatted_json = "\n\n".join([
            json.dumps(doc, indent=2) 
            for doc in formatted_docs
        ])
        
        return {"retrieved_docs": formatted_json}

    # Grading node
    def _grade_relevance(self, state: CorrectiveRAGState):
        """
        Grades the relevance of retrieved document chunks to decide
        whether the model should use document-based generation or
        perform a web search instead.

        Note:
        - Each one may implement this differently.
        For example:
            * Using an LLM with structured output (as shown below).
            * Computing average cosine similarity scores directly from embeddings.
            * Combining both (LLM + heuristic threshold).
        - The goal is to demonstrate conditional routing, not a fixed grading metric.
        """
        prompt = DOCUMENT_GRADING_PROMPT
        llm_struct = self.llm.with_structured_output(DocumentGradingResponse)
        chain = prompt | llm_struct

        # retrieved_docs is already formatted as pretty JSON string
        response = chain.invoke(
            {
                "question": state["question"],
                "retrieved_docs": state["retrieved_docs"],
            }
        )
        print(f"Document grading response: {response}")

        # Use the single binary value to make routing decision
        if response.is_sufficient == 1:
            return "YES"
        else:
            return "NO"

    # Generation node
    def _create_generation_node(self, state: CorrectiveRAGState):
        """Generates answers using retrieved document context."""
        prompt = DOCUMENT_RAG_PROMPT
        llm_struct = self.llm.with_structured_output(RagGenerationResponse)
        chain = prompt | llm_struct

        response = chain.invoke(
            {
                "retrieved_docs": state["retrieved_docs"],
                "question": state["question"],
            }
        )

        text = f"Answer: {response.answer}\n"
        if response.sources:
            names = [osp.basename(src) for src in response.sources]
            text += "\nSources:\n" + "\n".join(f"- {s}" for s in names)
        return {"answer": text}

    # Web search and summary
    def _web_search_node(self, state: CorrectiveRAGState):
        """
        Runs a web search query using Tavily.
        Formats results as pretty JSON before storing in state.
        """
        results = self.search_tool.invoke({"query": state["question"]})
        
        # Extract and format relevant fields from each result
        formatted_results = []
        for result in results['results']:
            formatted_result = {
                "url": result.get("url", ""),
                "title": result.get("title", ""),
                "content": result.get("content", ""),
                "raw_content": result.get("raw_content", "")
            }
            formatted_results.append(formatted_result)
        
        # Convert to pretty JSON string with newlines between results
        formatted_json = "\n\n".join([
            json.dumps(result, indent=2) 
            for result in formatted_results
        ])
        
        return {"web_search_results": formatted_json}

    def _summarize_web_search_results(self, state: CorrectiveRAGState):
        """Summarizes web search results into a final answer."""
        # web_search_results is already formatted as pretty JSON string
        chain = WEB_SEARCH_SUMMARIZER_PROMPT | self.llm | StrOutputParser()
        answer = chain.invoke(
            {
                "query": state["question"],
                "search_results": state["web_search_results"],
            }
        )
        return {"answer": answer}

    # Message handler
    def process_message(
        self, message: str, chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Executes the Corrective RAG-Lite pipeline:
        - Uses document knowledge when relevant.
        - Falls back to web search when documents are insufficient.
        - Returns a source-cited answer.
        """
        result = self.graph.invoke({"question": message})
        return result["answer"]
