"""
Assignment 2 — Part 1: Web Search implementation using LangGraph with Tracing

This script builds a LangGraph workflow that:
1. Performs a live web search.
2. Summarizes search results through an LLM.
3. Records execution traces for observability via Opik.

Notes:
- Uses the WEB_SEARCH_SUMMARIZER_PROMPT defined in prompts.py for answer formatting.
- The search component (Tavily) can be replaced with another search API if desired like Exa
"""

import json
from typing import Dict, List, Optional, TypedDict
from perplexia_ai.core.chat_interface import ChatInterface
from langchain_tavily import TavilySearch
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langchain_core.output_parsers import StrOutputParser
from perplexia_ai.solutions.week2.prompts import WEB_SEARCH_SUMMARIZER_PROMPT
from opik.integrations.langchain import OpikTracer


# Step 1: Define the shared LangGraph state
class WebSearchState(TypedDict):
    query: str
    search_results: str  # Formatted as pretty JSON string
    answer: str


class WebSearchChat(ChatInterface):
    """LangGraph + Tavily web search workflow with Opik tracing."""

    def __init__(self):
        self.llm = None
        self.search_tool = None
        self.graph = None
        self.tracer = None

    # Step 2: Define graph nodes
    def web_search(self, state: WebSearchState):
        """
        Runs the web search tool and returns retrieved results.
        Formats results as pretty JSON before storing in state.
        """
        results = self.search_tool.invoke({"query": state["query"]})
        
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
        
        return {"search_results": formatted_json}

    def summarize_results(self, state: WebSearchState):
        """
        Summarizes search results using the LLM and WEB_SEARCH_SUMMARIZER_PROMPT.

        Expected output:
            Answer: <summary>
            References:
            - <url1>
            - <url2>
        """
        # search_results is already formatted as pretty JSON string
        chain = WEB_SEARCH_SUMMARIZER_PROMPT | self.llm | StrOutputParser()
        answer = chain.invoke({"query": state["query"], "search_results": state["search_results"]})
        return {"answer": answer}

    # Step 3: Initialization
    def initialize(self) -> None:
        """
        Initializes all workflow components:
        - Configures Opik tracing
        - Loads the LLM
        - Sets up the web-search tool
        - Builds and compiles the LangGraph
        """
        print("Initializing Web Search system...")

        self.llm = init_chat_model("gpt-5-mini", model_provider="openai", reasoning_effort="minimal")

        self.search_tool = TavilySearch(
            max_results=5,
            include_answer=True,
            include_raw_content=False,
            include_images=False,
            search_depth="advanced",
        )

        graph = StateGraph(WebSearchState)
        graph.add_node("web_search", self.web_search)
        graph.add_node("summarize_results", self.summarize_results)
        graph.add_edge(START, "web_search")
        graph.add_edge("web_search", "summarize_results")
        graph.add_edge("summarize_results", END)

        # Compile the graph and attach Opik tracer
        self.graph = graph.compile()
        self.tracer = OpikTracer(
            graph=self.graph.get_graph(xray=True), project_name="web-search-graph"
        )

        print("Initialization complete. Ready to process messages.")

    def process_message(
        self, message: str, chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Executes the full web-search workflow:
        1. Performs search using the configured tool.
        2. Summarizes retrieved content through the LLM.
        3. Returns a formatted answer string.
        """
        state = {"query": message}

        config = {
            "configurable": {"thread_id": "web_search_session"},
            "callbacks": [self.tracer],
        }

        result = self.graph.invoke(state, config=config)
        print(f"Final Graph State: {result}")
        return result["answer"]
