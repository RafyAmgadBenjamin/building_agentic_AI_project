"""Part 1.

This is the first iteration of the project focusing on having a full POC for generating
infrastructure as code based on user requirements using a tool-using agent approach.
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
import json
from langgraph.graph import StateGraph, START, END

# Opik imports
from opik import track
from opik.integrations.langchain import OpikTracer
import opik

from perplexia_ai.week3.prompts import (
    USER_REQUIREMENTS_VALIDATION_PROMPT,
    TF_FILES_GENERATION_PROMPT,
)


from perplexia_ai.week3.workflow_state import WorkflowState


class ToolUsingAgentChat(ChatInterface):
    import logging
    logger = logging.getLogger("ToolUsingAgentChat")
    """Project iteration 1 implementation focusing on having full POC for generating infrastructure as code."""

    def __init__(self):
        # Initialize Opik client
        # self.opik_client = opik.Opik()

        model_kwargs = {"model": "gpt-4o-mini"}
        # Get environment variables at runtime
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_api_base = os.getenv("OPENAI_API_BASE")

        if openai_api_key:
            model_kwargs["api_key"] = openai_api_key
        if openai_api_base:
            model_kwargs["base_url"] = openai_api_base

        # Create OpikTracer for LangChain integration
        # self.opik_tracer = OpikTracer()
        self.llm = init_chat_model(**model_kwargs)

        builder = StateGraph(WorkflowState)
        builder.add_node("validate_user_requirements", self._validate_user_requirements)
        builder.add_node("generate_terraform_files", self._generate_terraform_files)
        builder.add_node(
            "write_terraform_files_to_disk", self._write_terraform_files_to_disk
        )
        builder.add_node("validate_terraform_files", self._validate_terraform_files)

        builder.add_edge(START, "validate_user_requirements")
        ## if user requirements are invalid, it will end the flow and pass the control to the user to refine the requirements
        builder.add_conditional_edges(
            "validate_user_requirements",
            self._route_after_requirements_validation,
            {"generate_terraform_files": "generate_terraform_files", END: END},
        )

        builder.add_edge("generate_terraform_files", "write_terraform_files_to_disk")
        builder.add_edge("write_terraform_files_to_disk", "validate_terraform_files")

        builder.add_conditional_edges(
            "validate_terraform_files",
            self._route_after_terraform_validation,
            {END: END, "generate_terraform_files": "generate_terraform_files"},
        )
        self.graph = builder.compile()

    def initialize(self) -> None:
        """Initialize components for the tool-using agent."""
        pass

    # @track(name="process_message", project_name="project_Iac_agent")
    def process_message(
        self, message: str, chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Process a message using the tool-using agent.

        Args:
            message: The user's input message
            chat_history: Previous conversation history

        Returns:
            str: The assistant's response
        """
        result = self.graph.invoke({"user_input": message})
        return result["user_message"]

    def _validate_user_requirements(
        self, workflow_state: WorkflowState
    ) -> WorkflowState:
        """Validate user requirements in the workflow state using LLM.

        Args:
            workflow_state: The current workflow state

        Returns:
            WorkflowState: The updated workflow state with validation results
        """
        self.logger.info(f"Validating user requirements is called with this user input: {workflow_state['user_input']}")
        formated_prompted = USER_REQUIREMENTS_VALIDATION_PROMPT.format_prompt(
            USER_INPUT=workflow_state["user_input"]
        )
        self.logger.debug(f"Formatted prompt: {formated_prompted.text}")

        response = self.llm.invoke(formated_prompted.text)
        self.logger.debug(f"LLM response: {response}")
        response_content = response.content.strip()
        self.logger.info(f"Response content: {response_content}")
        
        # TODO: hardening parsing logic to extract JSON from response
        if "NOT_VALID" in response_content:
            workflow_state["is_valid_user_requirements"] = False
            workflow_state["user_requirements_validation_errors"] = response_content
            workflow_state["user_message"] = response_content
        elif "VALID" in response_content:
            workflow_state["is_valid_user_requirements"] = True
            workflow_state["user_requirements_validation_errors"] = ""
            workflow_state["user_message"] = "Requirements are valid and ready for Terraform generation."
        else:
            raise ValueError("Unexpected response format from LLM.")


            
        return workflow_state

    def _route_after_requirements_validation(self, workflow_state: WorkflowState):
        """Control the routing condition for user requirements validation.

        Args:
            workflow_state: The current workflow state

        Returns:
            bool: True if the user requirements are valid, False otherwise
        """
        return (
            "generate_terraform_files"
            if workflow_state["is_valid_user_requirements"]
            else END
        )

    def _route_after_terraform_validation(self, workflow_state: WorkflowState):
        """Control the routing condition for Terraform files validation.

        Args:
            workflow_state: The current workflow state

        Returns:
            bool: True if the Terraform files are valid, False otherwise
        """
        return (
            END
            if workflow_state["is_valid_terraform_files"]
            else "generate_terraform_files"
        )

    def _generate_terraform_files(self, workflow_state: WorkflowState) -> WorkflowState:
        """Generate Terraform files based on user requirements Using LLM.

        Args:
            workflow_state: The current workflow state

        Returns:
            WorkflowState: The updated workflow state with generated file paths
        """
        # Implement file generation logic here
        self.logger.info(f"Generating terraform files is called with this user input: {workflow_state['user_input']}")
        formated_prompted = TF_FILES_GENERATION_PROMPT.format_prompt(
            USER_INPUT=workflow_state["user_input"]
        )
        self.logger.debug(f"Formatted prompt: {formated_prompted.text}")
        response = self.llm.invoke(formated_prompted.text)

        response_content = response.content.strip()
        self.logger.info(f"Response content: {response_content}")
        
        return workflow_state

    def _write_terraform_files_to_disk(
        self, workflow_state: WorkflowState
    ) -> WorkflowState:
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
        # For now, assume terraform files are always valid
        # You can implement actual validation logic later
        workflow_state["is_valid_terraform_files"] = True
        workflow_state["terraform_files_validation_errors"] = ""
        workflow_state["user_message"] = "Terraform files have been successfully generated and validated."
        return workflow_state
