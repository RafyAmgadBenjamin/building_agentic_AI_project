from langchain_core.prompts import PromptTemplate

USER_REQUIREMENTS_VALIDATION_PROMPT = PromptTemplate.from_template(
    """
    You are an Infrastructure-as-Code assistant.

    Your task is to validate the user's requirements for Terraform automation. 
    Be **lenient** — if you can reasonably fill in defaults for missing details, 
    the requirements are VALID. Only flag as NOT_VALID if critical information 
    is missing that cannot be defaulted.

    Check for:
    - Critical missing information (e.g. cloud provider, instance type, OS)
    - Conflicts or ambiguity
    - Security concerns (if obviously unsafe)

    Defaults you can assume:
    - AWS as provider if not specified
    - us-east-1 as region if not specified
    - Basic security groups (SSH, HTTP, HTTPS)
    - Standard AMI for the OS mentioned
    - t3.micro as default instance if not specified

    Output format:
    1. validation_result: VALID or NOT_VALID (stick to these two words only)
    2. terraform_errors: If NOT_VALID: list missing critical requirements as bullet points. If VALID: use empty list

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

TF_ERROR_FIXING_PROMPT = PromptTemplate.from_template(
    """You are a Terraform expert. Fix the validation errors in these files.

USER REQUIREMENTS:
{USER_INPUT}

VALIDATION ERRORS:
{VALIDATION_ERRORS}

CURRENT FILES:
{CURRENT_FILES}

Use this format for each file:

# filename.tf
```hcl
[corrected terraform code]
```

Fix ONLY the reported errors. Keep filenames and structure the same.
"""
)