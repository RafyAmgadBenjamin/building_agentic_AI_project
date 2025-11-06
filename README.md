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

2. **Configure API Keys**
   - Set your OpenAI API key and base URL as environment variables:
     ```bash
     export OPENAI_API_KEY=your-key
     export OPENAI_API_BASE=https://api.openai.com/v1
     ```

3. **Run the Project**
   - Start the main application:
     ```bash
     uv run python code/run.py --week project --mode part1
     ```
   - You can select different project iterations using the factory in `iac_agent/agents/factory.py`.

## Project Iterations

- **IAC_AGENT (part1):** Validates requirements and generates Terraform files using a tool-using agent.
- **AGENTIC_RAG (part2):** Demonstrates retrieval-augmented generation with agentic workflows to load the organization playbook to deploy
the infrastructure.
- **performance and validation (part3):** Enhance the performance and
validate the terraform files to be ready for deployment on the infrastructure.

## Customization

- Extend agent workflows in `iac_agent/week3/` for new automation scenarios.

## License

MIT License

## Authors

- Rafy Amgad Benjamin
- Milad Afzal
- Contributors welcome!
