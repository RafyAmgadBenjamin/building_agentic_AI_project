from langchain_core.prompts import PromptTemplate

USER_REQUIREMENTS_VALIDATION_PROMPT = PromptTemplate.from_template(
    """
    You are an Infrastructure-as-Code assistant.

    Your task is to validate the user's requirements for Terraform automation, you should be able
    to work with the minimal necessary requirements.

    Check for:
    - Missing information
    - Conflicts or ambiguity
    - Security / tagging / naming policy violations
    - Resource limits or constraints

    Output format:
    1. validation_result: VALID or NOT_VALID stick to this two words only in validation_result
    2. terraform_errors:  If NOT_VALID: list missing or unclear requirements as bullet points and
      file this variable with an empty list if VALID

    User Requirement:
    {USER_INPUT}
    """

)

TF_FILES_GENERATION_PROMPT = PromptTemplate.from_template(
    """
        You are an expert Terraform generator.

        Generate .tf files based ONLY on the validated requirements and organizational standards below.

        Rules:
        - Do NOT invent resource names, modules, variables, or values
        - Use only what is described in the provided context
        - Follow tagging, naming, environment, and security rules

        Output format:
        - Short explanation of what infrastructure will be created
        - Terraform code in .tf syntax
        - No commentary inside code blocks unless required by policy

        User Requirements:
        {USER_INPUT}
    """)