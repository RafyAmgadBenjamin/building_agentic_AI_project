"""
Assignment 2 — Part 2: Document RAG using LangGraph

This script builds a simple Retrieval-Augmented Generation (RAG) workflow
that answers questions from PDF documents.

Main steps:
1. Load and chunk PDFs for embedding.
2. Create embeddings (OpenAI) and store them in a vector database (Chroma).
3. Build a LangGraph with retrieval and generation nodes.
4. Generate answers grounded in retrieved text with source citations.

Notes:
- Use smaller chunks (≈500-1000 tokens) for better recall and performance.
- ChromaDB can be replaced with InMemoryVectorStore if machine memory issues are faced.
"""

import json
import time
import os
import os.path as osp
from typing import Dict, List, Optional, TypedDict

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, START, END
from langchain_community.document_loaders import PyPDFLoader
from langchain.chat_models import init_chat_model
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from perplexia_ai.core.chat_interface import ChatInterface
from perplexia_ai.solutions.week2.prompts import DOCUMENT_RAG_PROMPT, RagGenerationResponse
from opik.integrations.langchain import OpikTracer


# TODO: Update these paths to your own local paths
# Set up document paths
BASE_DIR = "/Users/aish/Downloads/rag_dataset"
FILE_PATHS = [
    osp.join(BASE_DIR, "2019-annual-performance-report.pdf"),
    osp.join(BASE_DIR, "2020-annual-performance-report.pdf"),
    osp.join(BASE_DIR, "2021-annual-performance-report.pdf"),
    osp.join(BASE_DIR, "2022-annual-performance-report.pdf"),
]
CHROMA_PERSIST_DIRECTORY = "/Users/aish/chroma_db"


# Define the LangGraph state (shared between nodes)
class DocumentRAGState(TypedDict):
    question: str
    retrieved_docs: str  # Formatted as pretty JSON string
    answer: str


class DocumentRAGChat(ChatInterface):
    """LangGraph-based Document RAG system."""

    def __init__(self):
        self.llm = None
        self.embeddings = None
        self.vector_store = None
        self.document_paths = []
        self.graph = None

    # Initialize LLM, embeddings, and vector store
    def initialize(self) -> None:
        """
        Initializes all core components of the RAG pipeline.

        Includes:
        - LLM initialization
        - Embeddings model setup
        - Document loading and preprocessing
        - Vector database creation (Chroma)
        - LangGraph construction and compilation
        """
        print("Initializing Document RAG system...")

        # Initialize model
        # If performance issues occur, consider switching to "gpt-4o-mini"
        # Also even when setting reasoning_effort="minimal", some models (like gpt-5-nano)
        # may still consume large reasoning tokens when combined with structured outputs, 
        # so better to not to use it
        self.llm = init_chat_model("gpt-5-mini", model_provider="openai", reasoning_effort="minimal")

        # Initialize embeddings model
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        # Initialize persistent Chroma vector database
        # NOTE: If Chroma fails on low-memory machines, use:
        #   from langchain_core.vectorstores import InMemoryVectorStore
        #   self.vector_store = InMemoryVectorStore(self.embeddings)
        # InMemoryVectorStore avoids disk writes and works faster for small datasets,
        # while Chroma is preferred for persistence and enterprise-scale queries.

        self.vector_store = Chroma(
            embedding_function=self.embeddings,
            persist_directory=CHROMA_PERSIST_DIRECTORY,
            collection_name="opm_documents"
        )
        # NOTE: This is a quick way to check if the vector store has any documents
        # instead of loading many documents to check.
        has_existing_documents = len(self.vector_store.get(limit=1)['ids']) > 0
        if has_existing_documents:
            print("ChromaDB found - reusing existing documents.")
        else:
            print("No existing ChromaDB found - processing and embedding documents...")
            self.document_paths = FILE_PATHS
            docs = self._load_and_process_documents()
            print(f"Loaded and chunked {len(docs)} document pieces")
            self.vector_store.add_documents(docs)
            # self.vector_store.persist()

            # NOTE: If you are seeing rate limits from OpenAI, you can add documents in batches
            # instead of all at once to handle rate limits
            # batch_size = 100
            # for i in range(0, len(docs), batch_size):
            #     print(f"Adding documents {i}-{i + batch_size} to Chroma...")
            #     self.vector_store.add_documents(docs[i:i + batch_size])
            #     if i + batch_size < len(docs):
            #         time.sleep(10)
            print("Embeddings processed and stored in ChromaDB.")

        # Build LangGraph
        graph = StateGraph(DocumentRAGState)
        graph.add_node("retrieval", self._create_retrieval_node)
        graph.add_node("generation", self._create_generation_node)
        graph.add_edge(START, "retrieval")
        graph.add_edge("retrieval", "generation")
        graph.add_edge("generation", END)
        self.graph = graph.compile()

        # Optional: Opik tracing for visibility
        self.tracer = OpikTracer(
            graph=self.graph.get_graph(xray=True),
            project_name="document-rag-graph"
        )

        print("Initialization complete. Ready to process messages.")

    # Load and process documents
    def _load_and_process_documents(self) -> list[Document]:
        """
        Loads PDFs and splits them into smaller chunks suitable for embeddings.

        """
        docs = []
        for file_path in self.document_paths:
            print(f"Loading {osp.basename(file_path)}")
            loader = PyPDFLoader(file_path)
            page_docs = loader.load()

            combined_text = "\n".join([doc.page_content for doc in page_docs])

            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            chunks = text_splitter.split_text(combined_text)

            docs.extend([
                Document(page_content=chunk, metadata={"source": file_path})
                for chunk in chunks
            ])
        return docs

    # Define retrieval node
    def _create_retrieval_node(self, state: DocumentRAGState):
        """
        Retrieves the top relevant chunks based on the user's question.
        Formats documents as pretty JSON before storing in state.
        """
        docs = self.vector_store.similarity_search(state["question"], k=4)
        print(f"Retrieved {len(docs)} matching chunks")
        
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
        print(f"Formatted JSON: {formatted_json}")
        
        return {"retrieved_docs": formatted_json}

    # Define generation node
    def _create_generation_node(self, state: DocumentRAGState):
        """
        Generates the final response using retrieved documents.

        Important notes:
        - Using `with_structured_output()` enforces a schema and simplifies parsing
          but significantly increases reasoning token usage.

        Guidelines:
        - Keep `with_structured_output()` if working with smaller context sizes.
        - For long documents or slower models, comment it out and use the direct chain approach.
        """
        prompt = DOCUMENT_RAG_PROMPT

        # Option 1: Structured output (useful but can trigger heavy reasoning)
        llm_structured = self.llm.with_structured_output(RagGenerationResponse)
        chain = prompt | llm_structured

        # Option 2: Unstructured fallback (recommended if slow)
        # chain = prompt | self.llm

        print(f"Generating answer for question: {state['question']}")
        response = chain.invoke({
            "retrieved_docs": state["retrieved_docs"],
            "question": state["question"]
        })

        response_str = f"Answer: {response.answer}\n"
        if response.sources:
            clean_sources = [osp.basename(src) for src in response.sources]
            response_str += "\nSources:\n" + "\n".join(f"- {src}" for src in clean_sources)
        return {"answer": response_str}

    # Define chat interface method
    def process_message(self, message: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Executes the full RAG flow:
        - Retrieves relevant document sections
        - Generates an answer grounded in the documents
        - Returns a formatted, source-cited response
        """
        result = self.graph.invoke({"question": message}, config={"callbacks": [self.tracer]})
        return result["answer"]
