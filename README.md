# IAC Agent Project

This project demonstrates agentic AI for generating infrastructure as code (IaC) using a tool-using agent approach. It is organized into several iterations, each showcasing a different agentic workflow for automating cloud infrastructure provisioning.

## Project Structure

```
code/
├── iac_agent/
│   ├── app.py
│   ├── core/
│   │   └── chat_interface.py
│   ├── tools/
│   │   └── calculator.py
│   ├── week3/
│   │   ├── factory.py
│   │   ├── part1.py
│   │   ├── part2.py
│   │   ├── part3.py
│   │   ├── prompts.py
│   │   └── workflow_state.py
│   └── ...
├── run.py
└── README.md
```

## Main Features

- **Agentic Infrastructure Generation:** Uses LLMs and custom agents to validate user requirements, generate Terraform files, and automate cloud provisioning.
- **Modular Design:** Each project iteration (part1, part2, part3) demonstrates a different agentic workflow, accessible via the factory pattern.

- **Logging:** Uses Python logging for traceability and debugging.

## Usage

1. **Install Dependencies**
   - This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable Python package management.
   - Install uv if you haven't already:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```
   - Install project dependencies:
     ```bash
     uv sync
     ```

2. **Install Terraform**
   - This project requires Terraform CLI for validating generated infrastructure code.
   - Install Terraform:
     - **macOS (Homebrew):**
       ```bash
       brew tap hashicorp/tap
       brew install hashicorp/tap/terraform
       ```
     - **Linux:**
       ```bash
       wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
       echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
       sudo apt update && sudo apt install terraform
       ```
     - **Windows (Chocolatey):**
       ```bash
       choco install terraform
       ```
   - Verify installation:
     ```bash
     terraform --version
     ```

3. **Configure API Keys**
   - Set your OpenAI API key and base URL as environment variables:
     ```bash
     export OPENAI_API_KEY=your-key
     export OPENAI_API_BASE=https://api.openai.com/v1
     ```

4. **Run the Project**
   - Start the main application:
     ```bash
     uv run python code/run.py --week project --mode part1
     ```
   - You can select different project iterations using the factory in `iac_agent/agents/factory.py`.

## Project Iterations

### Part 1 - IaC Agent: 
Validates requirements and generates Terraform files using a tool-using agent with automatic Terraform validation.

**Terraform Validation Process**

Part1 automatically validates generated Terraform files through three stages:
1. **`terraform init`** - Initializes the Terraform working directory and downloads required providers
2. **`terraform validate`** - Validates the configuration syntax and internal consistency
3. **`terraform plan`** - Creates an execution plan to verify the configuration is deployable

If validation fails, the agent automatically attempts to fix errors up to 3 times before reporting failure.
  
```mermaid
graph TD
    Start([User Submits Requirements]) --> ValidateReq[Validate User Requirements]
    
    ValidateReq -->|Valid| GenFiles[Generate Terraform Files]
    ValidateReq -->|Invalid| EndInvalid([END: Show Validation Errors])
    
    GenFiles --> WriteFiles[Write Files to Disk]
    
    WriteFiles --> ValidateTF[Validate Terraform Files]
    
    ValidateTF --> TFInit[Run: terraform init]
    TFInit --> TFValidate[Run: terraform validate]
    TFValidate --> TFPlan[Run: terraform plan]
    
    TFPlan -->|Success| RouteSuccess{Route}
    TFPlan -->|Failed| CheckRetry{Attempt Count > 2?}
    
    CheckRetry -->|No| FixErrors[Fix Terraform Errors<br/>Increment Attempt Count]
    CheckRetry -->|Yes| RouteFailure{Route}
    
    FixErrors --> WriteFiles
    
    RouteSuccess -->|is_valid=true| Finalize[Finalize]
    RouteFailure -->|is_valid=false| Finalize
    
    Finalize -->|Success Path| ShowSuccess([END: Show Generated Files<br/>with File Contents])
    Finalize -->|Failure Path| ShowFailure([END: Show Validation Errors<br/>after 3 Attempts])
    
    style Start fill:#e1f5ff
    style ShowSuccess fill:#d4edda
    style ShowFailure fill:#f8d7da
    style EndInvalid fill:#f8d7da
    style ValidateReq fill:#fff3cd
    style GenFiles fill:#fff3cd
    style WriteFiles fill:#fff3cd
    style ValidateTF fill:#fff3cd
    style FixErrors fill:#ffeaa7
    style Finalize fill:#cfe2ff
    style RouteSuccess fill:#e7f3ff
    style RouteFailure fill:#e7f3ff
```
### Part 2 - IaC Agent with RAG :
Demonstrates retrieval-augmented generation with agentic workflows to load the organization playbook to deploy
the infrastructure.


```mermaid
graph TD
    %% Data Sources for Vector DB
    BestPractices[Best Practices<br/>Documentation] --> Ingestion[Document Ingestion<br/>+ Chunking]
    TFStandards[Terraform<br/>Standards] --> Ingestion
    CompanyRepo[Company IaC<br/>Repository] --> Ingestion
    CloudDocs[Cloud Provider<br/>Documentation] --> Ingestion
    
    Ingestion --> ChromaDB[(Chroma Vector DB<br/>Embedded Documents)]
    
    %% Main Workflow
    Start([User Submits Requirements]) --> QueryEmbedding[Create Query Embedding]
    
    QueryEmbedding --> ChromaDB
    
    ChromaDB --> RAG[RAG: Retrieve Top-K<br/>Relevant Contexts]
    
    RAG --> ValidateReq[Validate Requirements<br/>with Retrieved Context]
    
    ValidateReq -->|Valid| GenFiles[Generate Terraform Files<br/>+ Log Generation]
    ValidateReq -->|Invalid| EndInvalid([END: Validation Errors])
    
    GenFiles --> WriteFiles[Write Files to Disk]
    
    WriteFiles --> SecurityCheck[Security Check<br/>No Secrets/Public Buckets]
    
    SecurityCheck -->|Pass| TFValidate[Terraform Validate<br/>init + validate + plan]
    SecurityCheck -->|Fail| ShowFailure
    
    TFValidate -->|Success| CalcMetrics[Calculate Metrics<br/>+ Log Results]
    TFValidate -->|Failed| CheckRetry{Attempts > 2?}
    
    CheckRetry -->|No| FixErrors[Fix Errors<br/>Store Failed Generation<br/>Increment Count]
    CheckRetry -->|Yes| CalcMetrics
    
    FixErrors --> WriteFiles
    
    CalcMetrics --> ShowSuccess([END: Generated Files + Metrics])
    CalcMetrics --> ShowFailure([END: Errors After 3 Attempts])
    
    style Start fill:#e1f5ff
    style ShowSuccess fill:#d4edda
    style ShowFailure fill:#f8d7da
    style EndInvalid fill:#f8d7da
    style RAG fill:#e8daff
    style ValidateReq fill:#fff3cd
    style GenFiles fill:#fff3cd
    style SecurityCheck fill:#ffcccc
    style TFValidate fill:#cfe2ff
    style FixErrors fill:#ffeaa7
    style CalcMetrics fill:#d1f2eb
```
### Part3 - Performance and validation:
Enhance the performance and validate the terraform files to be ready for deployment on the infrastructure.

## Customization

- Extend agent workflows in `iac_agent/week3/` for new automation scenarios.

## License

MIT License

## Authors

- Rafy Amgad Benjamin
- Milad Afzal
- Contributors welcome!
