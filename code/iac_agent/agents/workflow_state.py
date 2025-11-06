from typing import Dict, List, Optional
from langgraph.graph import MessagesState


class WorkflowState(MessagesState):
    user_input: str
    terraform_files: Dict[str, str] 
    terraform_files_paths: List[str]
    is_valid_terraform_files: bool
    terraform_files_validation_errors: Optional[str]
    is_valid_user_requirements: bool
    user_requirements_validation_errors: Optional[str]
    user_message: List[str]
    validation_attempt_count: int = 0
    output_directory: str = ""
