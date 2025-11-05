from langchain_core.prompts import PromptTemplate
from pydanctic import BaseModel, Field

USER_REQUIREMENTS_VALIDATION_PROMPT = PromptTemplate.from_template(
    """
    You are an Infrastructure-as-Code assistant.

    Your task is to validate the user's requirements for Terraform automation.

    Check for:
    - Missing information (region, VPC CIDR, instance size, bucket names, networking rules, env)
    - Conflicts or ambiguity
    - Security / tagging / naming policy violations
    - Resource limits or constraints

    Output format:
    1. Summary of the request
    2. Validation result: VALID ✅ or NOT VALID ❌
    3. If NOT VALID: list missing or unclear requirements as bullet points

    User Requirement:
    {{USER_INPUT}}
    """

)