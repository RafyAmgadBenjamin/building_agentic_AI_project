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
from iac_agent.core.logger_configuration import get_logger


class IacAgentChat(ChatInterface):
    logger = get_logger()
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
        builder.add_node(
            "write_terraform_files_to_disk", self._write_terraform_files_to_disk
        )
        builder.add_node("validate_terraform_files", self._validate_terraform_files)
        builder.add_node("fix_terraform_errors", self._fix_terraform_errors)
        builder.add_node("finalize", self._finalize)

        builder.add_edge(START, "validate_user_requirements")
        ## if user requirements are invalid, it will end the flow and pass the control to the user to refine the requirements
        builder.add_conditional_edges(
            "validate_user_requirements",
            self._route_after_requirements_validation,
            {"generate_terraform_files": "generate_terraform_files", END: END},
        )

        builder.add_edge("generate_terraform_files", "write_terraform_files_to_disk")
        builder.add_edge("write_terraform_files_to_disk", "validate_terraform_files")

        # enhanced routing after validation with retry logic
        builder.add_conditional_edges(
            "validate_terraform_files",
            self._route_after_terraform_validation,
            {"finalize": "finalize", "fix_terraform_errors": "fix_terraform_errors"},
        )

        # Loop back to write files after fixing
        builder.add_edge("fix_terraform_errors", "write_terraform_files_to_disk")

        # finalize goes to END
        builder.add_edge("finalize", END)

        self.graph = builder.compile()

    @track(name="process_message", project_name="project_Iac_agent")
    def process_message(self, message: str, chat_history: Optional[List[Dict[str, str]]] = None):
        """Process a message using the tool-using agent with streaming.

        Args:
            message: The user's input message
            chat_history: Previous conversation history

        Yields:
            str: Progress updates and final response
        """
        for event in self.graph.stream({"user_input": message}):
            node_name = list(event.keys())[0]
            state = event[node_name]
            
            # Yield progress update for each node
            yield f"🔄 **{node_name.replace('_', ' ').title()}**\n"
            
            # Log for debugging
            self.logger.debug(f"Node {node_name} completed, user_message: {state.get('user_message', 'N/A')[:100]}")
        
        # Yield final message
        final_message = state.get('user_message', 'Processing complete')
        yield f"\n---\n\n{final_message}"

    @track(name="validate_user_requirements", project_name="project_Iac_agent")
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

        response = self.llm.invoke(formated_prompted.text)
        response_content = response.content.strip()
        
        # TODO: hardening parsing logic to extract JSON from response
        if "NOT_VALID" in response_content:
            workflow_state["is_valid_user_requirements"] = False
            workflow_state["user_requirements_validation_errors"] = response_content
            workflow_state["user_message"] = response_content
            self.logger.warning(f"User requirements validation failed: {response_content}")
        elif "VALID" in response_content:
            workflow_state["is_valid_user_requirements"] = True
            workflow_state["user_requirements_validation_errors"] = ""
            workflow_state["user_message"] = "Requirements are valid and ready for Terraform generation."
            self.logger.info("User requirements validated successfully")
        else:
            raise ValueError("Unexpected response format from LLM.")
            
        return workflow_state

    @track(name="route_after_requirements_validation", project_name="project_Iac_agent")
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
        
    @track(name="fix_terraform_errors", project_name="project_Iac_agent")
    def _fix_terraform_errors(self, workflow_state: WorkflowState) -> WorkflowState:
        """Use LLM to analyze validation errors and regenerate fixed files.

        Args:
            workflow_state: The current workflow state

        Returns:
            WorkflowState: The updated workflow state with regenerated files
        """
        workflow_state["validation_attempt_count"] = workflow_state.get("validation_attempt_count", 0) + 1
        
        attempt_count = workflow_state["validation_attempt_count"]
        self.logger.info(f"Analyzing errors and fixing (attempt {attempt_count}/3)")
        
        # format current files for prompt
        current_files_str = "\n\n".join([
            f"# {filename}\n```hcl\n{content}\n```"
            for filename, content in workflow_state["terraform_files"].items()
        ])
        
        # create fix prompt
        from iac_agent.agents.prompts import TF_ERROR_FIXING_PROMPT
        
        fix_prompt = TF_ERROR_FIXING_PROMPT.format_prompt(
            USER_INPUT=workflow_state["user_input"],
            VALIDATION_ERRORS=workflow_state["terraform_files_validation_errors"],
            CURRENT_FILES=current_files_str
        )
        
        self.logger.debug(f"Fix prompt created for attempt {attempt_count}")
        
        # Get LLM to fix errors
        response = self.llm.invoke(fix_prompt.text)
        response_content = response.content.strip()
        
        self.logger.debug(f"LLM fix response: {response}")
        self.logger.debug(f"LLM fix response content: {response_content}")
        
        # parse regenerated files
        fixed_files = self._parse_terraform_files(response_content)
        
        if not fixed_files:
            self.logger.warning("LLM did not generate any files, keeping original")
            return workflow_state
        
        workflow_state["terraform_files"] = fixed_files
        
        self.logger.info(f"Attempt {attempt_count}: Regenerated {len(fixed_files)} files")
        
        return workflow_state
        
    @track(name="finalize", project_name="project_Iac_agent")
    def _finalize(self, workflow_state: WorkflowState) -> WorkflowState:
        """Create final message with all details (success or failure).

        Args:
            workflow_state: The current workflow state

        Returns:
            WorkflowState: The updated workflow state with final message
        """
        attempt_count = workflow_state.get("validation_attempt_count", 0)
        files_list = "\n".join([
            f"  - {path}"
            for path in workflow_state.get("terraform_files_paths", [])
        ])
        
        if workflow_state["is_valid_terraform_files"]:
            # Success path
            attempt_msg = f" (fixed in {attempt_count} attempts)" if attempt_count > 0 else ""
            
            terraform_files = workflow_state.get("terraform_files", {})
            files_content = "\n\n".join([
                f"### {filename}\n```hcl\n{content}\n```"
                for filename, content in terraform_files.items()
            ])
            
            workflow_state["user_message"] = (
                f"Terraform files validated successfully{attempt_msg}!\n\n"
                f"**Generated Files:**\n{files_list}\n\n"
                f"**File Contents:**\n\n{files_content}\n\n"
                f"You can now review and apply these configurations."
            )
            self.logger.info("Workflow completed successfully")
        else:
            # Failure path
            workflow_state["user_message"] = (
                f"Failed to generate valid Terraform files after {attempt_count} attempts.\n\n"
                f"**Last Validation Errors:**\n```\n{workflow_state['terraform_files_validation_errors']}\n```\n\n"
                f"**Generated Files (with errors):**\n{files_list}\n\n"
                f"Please refine your requirements and try again."
            )
            self.logger.error(f"Max retries reached. Last error: {workflow_state['terraform_files_validation_errors']}")
        
        return workflow_state

    @track(name="route_after_terraform_validation", project_name="project_Iac_agent")
    def _route_after_terraform_validation(self, workflow_state: WorkflowState):
        """Route based on validation result and retry count.

        Args:
            workflow_state: The current workflow state

        Returns:
            str: Next node to execute (finalize or fix_terraform_errors)
        """
        if workflow_state["is_valid_terraform_files"]:
            return "finalize"
        
        attempt_count = workflow_state.get("validation_attempt_count", 0)
        
        if attempt_count > 2:
            return "finalize"
        
        self.logger.info(f"Routing to error fixing (attempt {attempt_count + 1}/3)")
        return "fix_terraform_errors"

    @track(name="generate_terraform_files", project_name="project_Iac_agent")
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
        self.logger.debug(f"LLM response: {response}")
        self.logger.debug(f"Response content: {response_content}")
        
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
        

        if not terraform_files:
            code_block_pattern = r'```[^\n]*\n(.*?)```'
            matches = list(re.finditer(code_block_pattern, response_content, re.DOTALL))
            
            if len(matches) == 1:
                content = matches[0].group(1).strip()
                terraform_files["main.tf"] = content
            else:
                # Multiple files, add number suffix
                for i, match in enumerate(matches, 1):
                    content = match.group(1).strip()
                    terraform_files[f"main_{i}.tf"] = content
        
        return terraform_files

    @track(name="write_terraform_files_to_disk", project_name="project_Iac_agent")
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
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        attempt_count = workflow_state.get("validation_attempt_count", 0)
        
        if attempt_count > 0:
            dir_name = f"{timestamp}_attempt{attempt_count}"
        else:
            dir_name = timestamp
            
        output_dir = Path("generated_tf") / dir_name
        output_dir.mkdir(parents=True, exist_ok=True)

        workflow_state["output_directory"] = str(output_dir.absolute())
        self.logger.info(f"Created new output directory: {output_dir.absolute()}")
        
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
        
        self.logger.info(f"Successfully wrote {len(written_paths)} Terraform files")
        
        return workflow_state

    @track(name="validate_terraform_files", project_name="project_Iac_agent")
    def _validate_terraform_files(self, workflow_state: WorkflowState) -> WorkflowState:
        """Run terraform validate on generated files.

        Args:
            workflow_state: The current workflow state

        Returns:
            WorkflowState: The updated workflow state with validation results
        """
        import subprocess
        
        output_dir = workflow_state.get("output_directory")
        if not output_dir:
            workflow_state["is_valid_terraform_files"] = False
            workflow_state["terraform_files_validation_errors"] = "No output directory found"
            return workflow_state
        
        self.logger.info(f"Validating Terraform files in {output_dir}")
        
        try:
            # run terraform init
            self.logger.info("Running terraform init...")
            init_result = subprocess.run(
                ['terraform', 'init','-backend=false'],
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if init_result.returncode != 0:
                error_msg = init_result.stderr or init_result.stdout or "Unknown terraform init error"
                workflow_state["is_valid_terraform_files"] = False
                workflow_state["terraform_files_validation_errors"] = f"Terraform init failed:\n{error_msg}"
                self.logger.warning(f"Terraform init failed: {error_msg}")
                return workflow_state
                
            self.logger.debug(f"Init output: {init_result.stdout}")

            # run terraform validate
            self.logger.info("Running terraform validate...")
            validate_result = subprocess.run(
                ['terraform', 'validate'],
                cwd=output_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if validate_result.returncode != 0:
                error_msg = validate_result.stderr or validate_result.stdout or "Unknown terraform validate error"
                workflow_state["is_valid_terraform_files"] = False
                workflow_state["terraform_files_validation_errors"] = f"Terraform validate failed:\n{error_msg}"
                self.logger.warning(f"Terraform validation failed: {error_msg}")
                return workflow_state
            
            self.logger.info("Terraform validate passed!")

            workflow_state["is_valid_terraform_files"] = True
            workflow_state["terraform_files_validation_errors"] = ""
            self.logger.info("Terraform plan successful!") 
            
            # # run terraform plan dry-run
            # self.logger.info("Running terraform plan...")
            # plan_result = subprocess.run(
            #     ['terraform', 'plan', '-input=false', '-refresh=false', '-no-color'],
            #     cwd=output_dir,
            #     capture_output=True,
            #     text=True,
            #     timeout=120
            # )
            
            # if plan_result.returncode == 0:
            #     workflow_state["is_valid_terraform_files"] = True
            #     workflow_state["terraform_files_validation_errors"] = ""
            #     self.logger.info("Terraform plan successful!")
            # else:
            #     error_msg = plan_result.stderr or plan_result.stdout or "Unknown terraform plan error"
            #     workflow_state["is_valid_terraform_files"] = False
            #     workflow_state["terraform_files_validation_errors"] = f"Terraform plan failed:\n{error_msg}"
            #     self.logger.warning(f"Terraform plan failed: {error_msg}")
        except subprocess.TimeoutExpired:
            workflow_state["is_valid_terraform_files"] = False
            workflow_state["terraform_files_validation_errors"] = "Terraform command timed out"
            self.logger.error("Terraform validation timed out")
        except FileNotFoundError:
            workflow_state["is_valid_terraform_files"] = False
            workflow_state["terraform_files_validation_errors"] = "Terraform CLI not found. Please install Terraform."
            self.logger.error("Terraform CLI not found")
        except Exception as e:
            workflow_state["is_valid_terraform_files"] = False
            workflow_state["terraform_files_validation_errors"] = f"Unexpected error: {str(e)}"
            self.logger.error(f"Terraform validation error: {e}")
        
        return workflow_state
