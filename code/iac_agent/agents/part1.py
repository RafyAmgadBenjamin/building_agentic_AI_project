"""Part 1.

This is the first iteration of the project focusing on having a full POC for generating
infrastructure as code based on user requirements using a tool-using agent approach.
"""

from typing import Dict, List, Optional
from iac_agent.core.chat_interface import ChatInterface
from iac_agent.tools.calculator import Calculator
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from datetime import datetime
import os
import json
import re
from pathlib import Path
from langgraph.graph import StateGraph, START, END

# Opik imports
from opik import track
from opik.integrations.langchain import OpikTracer
import opik

from iac_agent.agents.prompts import (
    USER_REQUIREMENTS_VALIDATION_PROMPT,
    TF_FILES_GENERATION_PROMPT,
)


from iac_agent.agents.workflow_state import WorkflowState


class IacAgentChat(ChatInterface):
    import logging
    logger = logging.getLogger("IacAgentChat")
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
        self.logger.info(f"Generating terraform files is called with this user input: {workflow_state['user_input']}")
        
        formated_prompted = TF_FILES_GENERATION_PROMPT.format_prompt(
            USER_INPUT=workflow_state["user_input"]
        )
        self.logger.debug(f"Formatted prompt: {formated_prompted.text}")
        response = self.llm.invoke(formated_prompted.text)

        response_content = response.content.strip()
        self.logger.info(f"Response content: {response_content}")
        
        # parse Terraform code blocks from the response
        terraform_files = self._parse_terraform_files(response_content)
        workflow_state["terraform_files"] = terraform_files
        
        self.logger.info(f"Parsed {len(terraform_files)} Terraform files")
        
        return workflow_state
    
    def _parse_terraform_files(self, response_content: str) -> Dict[str, str]:
        """Parse Terraform files from LLM response.
        
        Args:
            response_content: The LLM response containing Terraform code
            
        Returns:
            Dict mapping filename to file content
        """
        terraform_files = {}
        seen_filenames = {}
        
        # extract filenames 
        pattern = r'(?:#+\s+|\*\*)([^\n\*]+\.tf)(?:\*\*)?\s*\n?\s*```[^\n]*\n(.*?)```'
        matches = re.finditer(pattern, response_content, re.DOTALL)
        
        for match in matches:
            filename = match.group(1).strip()
            content = match.group(2).strip()
            
            # handle duplicate filenames
            if filename in seen_filenames:
                seen_filenames[filename] += 1
                base_name = filename.rsplit('.tf', 1)[0]
                filename = f"{base_name}_{seen_filenames[filename]}.tf"
            else:
                seen_filenames[filename] = 1
            
            terraform_files[filename] = content
        
        # extract code blocks without filenames
        if not terraform_files:
            code_block_pattern = r'```[^\n]*\n(.*?)```'
            matches = re.finditer(code_block_pattern, response_content, re.DOTALL)
            
            for i, match in enumerate(matches, 1):
                content = match.group(1).strip()
                terraform_files[f"main_{i}.tf"] = content
        
        return terraform_files

    def _write_terraform_files_to_disk(
        self, workflow_state: WorkflowState
    ) -> WorkflowState:
        """Write generated Terraform files to disk.

        Args:
            workflow_state: The current workflow state

        Returns:
            WorkflowState: The updated workflow state with file paths
        """
        terraform_files = workflow_state.get("terraform_files", {})
        
        if not terraform_files:
            self.logger.warning("No Terraform files to write")
            workflow_state["terraform_files_paths"] = []
            return workflow_state
        
        # create output directory with time
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("generated_tf") / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)
        
        written_paths = []
        
        for filename, content in terraform_files.items():
            file_path = output_dir / filename
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                written_paths.append(str(file_path))
                self.logger.info(f"Written Terraform file: {file_path}")
            except Exception as e:
                self.logger.error(f"Error writing file {filename}: {e}")
        
        workflow_state["terraform_files_paths"] = written_paths
        
        self.logger.info(f"Successfully wrote {len(written_paths)} Terraform files to {output_dir}")
        
        return workflow_state

    def _validate_terraform_files(self, workflow_state: WorkflowState) -> WorkflowState:
        """Validate the generated Terraform files.

        Args:
            workflow_state: The current workflow state

        Returns:
            WorkflowState: The updated workflow state with validation results
        """
        terraform_files_paths = workflow_state.get("terraform_files_paths", [])
        
        if not terraform_files_paths:
            workflow_state["is_valid_terraform_files"] = False
            workflow_state["terraform_files_validation_errors"] = "No Terraform files were generated."
            workflow_state["user_message"] = "Failed to generate Terraform files. Please try again with more specific requirements."
            return workflow_state

        # For now, assume terraform files are always valid if they were written
        workflow_state["is_valid_terraform_files"] = True
        workflow_state["terraform_files_validation_errors"] = ""
        
        # Create success message with file list
        files_list = "\n".join([f"  - {path}" for path in terraform_files_paths])
        workflow_state["user_message"] = (
            f"Terraform files have been successfully generated and saved!\n\n"
            f"Generated files ({len(terraform_files_paths)}):\n{files_list}\n\n"
            f"You can now review and apply these Terraform configurations."
        )
        
        return workflow_state
