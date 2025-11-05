"""Part 1 - Tool-Using Agent implementation.

This implementation focuses on:
- Converting tools from Assignment 1 to use with LangGraph
- Using the ReAct pattern for autonomous tool selection
- Comparing manual workflow vs agent approaches
"""

from typing import Dict, List, Optional
from perplexia_ai.core.chat_interface import ChatInterface
from perplexia_ai.tools.calculator import Calculator
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from datetime import datetime
import os
from langgraph.graph import StateGraph, MessagesState, START, END

# Opik imports
from opik import track
from opik.integrations.langchain import OpikTracer
import opik


class WorkflowState(MessagesState):
    user_input: str
    terraform_files_paths: List[str]
    is_valid_terraform_fils: bool
    terraform_files_validation_errors: Optional[str]
    is_valid_user_requirements: bool
    user_requirements_validation_errors: Optional[str]

class ToolUsingAgentChat(ChatInterface):
    """Project iteration 1 implementation focusing on having full POC for generating infrastructure as code."""
    
    def __init__(self):
         # Initialize Opik client
        self.opik_client = opik.Opik()
        
        model_kwargs = {"model": "gpt-4o-mini"}
        # Get environment variables at runtime
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_api_base = os.getenv("OPENAI_API_BASE")

        if openai_api_key:
            model_kwargs["api_key"] = openai_api_key
        if openai_api_base:
            model_kwargs["base_url"] = openai_api_base

        # Create OpikTracer for LangChain integration
        self.opik_tracer = OpikTracer()
        self.llm = init_chat_model(**model_kwargs)

        builder = StateGraph(WorkflowState)
        builder.add_node("validate_user_requirements", self._validate_user_requirements)
        builder.add_node("generate_terraform_files", self._generate_terraform_files)
        builder.add_node("write_terraform_files_to_disk", self._write_terraform_files_to_disk)
        builder.add_node("validate_terraform_files", self._validate_terraform_files)

        builder.add_edge(START, "validate_user_requirements")
        ## if user requirements are invalid, it will end the flow and pass the control to the user to refine the requirements
        builder.add_conditional_edges("validate_user_requirements", 
                                      self._route_after_requirements_validation,
                                      mapping = {"generate_terraform_files": "generate_terraform_files",
                                                  END: END}) 

        builder.add_edge("generate_terraform_files", "write_terraform_files_to_disk")
        builder.add_edge("write_terraform_files_to_disk", "validate_terraform_files")

        builder.add_conditional_edges("validate_terraform_files", 
                                      self._route_after_terraform_validation,
                                      mapping={END: END, "generate_terraform_files": "generate_terraform_files"})
        builder.add_edge("refine_user_requirements", END)
        self.graph = builder.compile()



    
    def initialize(self) -> None:
        """Initialize components for the tool-using agent.
        
        Students should:
        - Initialize the chat model
        - Define tools for calculator, DateTime, and weather
        - Create the ReAct agent using LangGraph
        """
        pass
    
    def process_message(self, message: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Process a message using the tool-using agent.
        
        Args:
            message: The user's input message
            chat_history: Previous conversation history
            
        Returns:
            str: The assistant's response
        """
        return "Not implemented yet. Please implement Week 3 Part 1: Tool-Using Agent."


    def _validate_user_requirements(self, workflow_state: WorkflowState) -> WorkflowState:
        """Validate user requirements in the workflow state using LLM.

        Args:
            workflow_state: The current workflow state

        Returns:
            WorkflowState: The updated workflow state with validation results
        """
        # Call LLM to validate user requirements
        # Update workflow_state.is_valid_user_requirements
        # add the validation errors to workflow_state.user_requirements_validation_errors

        # Implement validation logic here
        return workflow_state

    def _route_after_requirements_validation(self, workflow_state: WorkflowState):
        """Control the routing condition for user requirements validation.

        Args:
            workflow_state: The current workflow state

        Returns:
            bool: True if the user requirements are valid, False otherwise
        """
        return "generate_terraform_files" if workflow_state["is_valid_user_requirements"] else END

    def _route_after_terraform_validation(self, workflow_state: WorkflowState):
        """Control the routing condition for Terraform files validation.

        Args:
            workflow_state: The current workflow state

        Returns:
            bool: True if the Terraform files are valid, False otherwise
        """
        return END if workflow_state["is_valid_terraform_files"] else "generate_terraform_files"
         
    
    def _generate_terraform_files(self, workflow_state: WorkflowState) -> WorkflowState:
        """Generate Terraform files based on user requirements Using LLM.

        Args:
            workflow_state: The current workflow state

        Returns:
            WorkflowState: The updated workflow state with generated file paths
        """
        # Implement file generation logic here
        return workflow_state
    
    def _write_terraform_files_to_disk(self, workflow_state: WorkflowState) -> WorkflowState:
        """Write generated Terraform files to disk.

        Args:
            workflow_state: The current workflow state

        Returns:
            WorkflowState: The updated workflow state with file paths
        """
        # Implement file writing logic here
        return workflow_state
    
    def _validate_terraform_files(self, workflow_state: WorkflowState) -> WorkflowState:
        """Validate the generated Terraform files.

        Args:
            workflow_state: The current workflow state

        Returns:
            WorkflowState: The updated workflow state with validation results
        """
        # Implement file validation logic here
        return workflow_state