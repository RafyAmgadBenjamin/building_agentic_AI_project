import os
import gradio as gr
from typing import List, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_demo(week: str = "project", mode_str: str = "part1", use_solution: bool = False):
    """Create and return a Gradio demo with the specified week and mode.
    
    Args:
        week: Which week implementation to use (1, 2, or 3)
        mode_str: String representation of the mode ('part1', 'part2', or 'part3')
        use_solution: If True, use solution implementation; if False, use student code
        
    Returns:
        gr.ChatInterface: Configured Gradio chat interface
    """
    # Determine code type label
    code_type = "Solution" if use_solution else "Student"
    
    # Week 3 implementation
    if week == "project":
        # Import the appropriate factory based on use_solution flag
        from iac_agent.week3.factory import ProjectIteration, create_chat_implementation as create_chat

        # Convert string to enum
        mode_map = {
            "part1": ProjectIteration.IAC_AGENT,
            "part2": ProjectIteration.AGENTIC_RAG,
            "part3": ProjectIteration.DEEP_RESEARCH
        }
        
        if mode_str not in mode_map:
            raise ValueError(f"Unknown mode: {mode_str}. Choose from: {list(mode_map.keys())}")
        
        mode = mode_map[mode_str]
        chat_interface = create_chat(mode)
        
        # Initialize the chat implementation (Week 3 requires explicit initialization)
        chat_interface.initialize()
        
        titles = {
            "part1": f"Perplexia AI - Week 3: Tool-Using Agent ({code_type})",
            "part2": f"Perplexia AI - Week 3: Agentic RAG ({code_type})",
            "part3": f"Perplexia AI - Week 3: Deep Research ({code_type})"
        }
        
        descriptions = {
            "part1": "Your intelligent AI agent that should be able to generate TF files based on user requirements.",
            "part2": "Your intelligent AI assistant that dynamically controls its search strategy.",
            "part3": "Your multi-agent research system that creates comprehensive research reports."
        }
        
        if mode_str == "part1":
            examples = [
                ["""
                    Deploy a web server with:
                    - Ubuntu 22.04 LTS
                    - AWS EC2 t3.medium instance
                    - In us-west-2 region
                    - Open port 80 (HTTP) and 443 (HTTPS)
                    - 20GB SSD storage
                    - Basic security group
                """],
                ["""
                    Deploy a MySQL database:
                    - AWS RDS instance
                    - Engine: MySQL 8.0
                    - Instance class: db.t3.micro
                    - Region: us-west-1
                    - Database name: myapp_db
                    - Username: admin
                    - Storage: 20GB General Purpose SSD
                    - Enable auto-backup (7 days retention)
                    - Public access: No (private subnet only)
                    - VPC: default VPC
                    - Security group: Allow MySQL access from 10.0.1.0/24
                    - Enable encryption at rest
                    - Set backup window to 03:00-04:00 UTC
                 """],
                ["""
                    Deploy a web application stack:
                    - AWS region: us-east-1
                    - VPC: Create new VPC with 2 subnets (public and private)
                    - EC2 instance:
                    - OS: Ubuntu 22.04 LTS
                    - Type: t3.small
                    - Public IP: Yes (for web access)
                    - Security group: Allow HTTP (80) and SSH (22) from anywhere
                    - RDS database:
                    - Engine: MySQL 8.0
                    - Instance: db.t3.micro
                    - Database name: app_db
                    - Username: admin
                    - Private subnet only (no public access)
                    - Storage: 50GB General Purpose SSD
                    - Security group: Allow MySQL (3306) from EC2 security group
                    - Networking:
                    - EC2 and RDS must be able to communicate
                    - SSH access to EC2 from my IP only
                    - Tags: Environment=staging, Project=webapp
                """]            ]
        elif mode_str == "part2":
            examples = [
                ["What strategic goals did OPM outline in the 2022 report?"],
                ["How did OPM's performance metrics evolve from 2018 to 2022?"],
                ["What major challenges did OPM face in implementing its strategic plans?"],
                ["Compare OPM's approach to workforce development across different fiscal years"]
            ]
        else:  # part3
            examples = [
                ["Research the current state and future prospects of quantum computing"],
                ["Create a comprehensive report on climate change adaptation strategies"],
                ["Analyze the impact of artificial intelligence on healthcare delivery"],
                ["Frameworks for building LLM agents: an enterprise guide"]
            ]
    else:
        raise ValueError(f"Unknown week: {week}. Choose from: [1, 2, 3]")
    
    # Create the respond function that uses our chat implementation
    def respond(message: str, history: List[Tuple[str, str]]) -> str:
        """Process the message and return a response.
        
        Args:
            message: The user's input message
            history: List of previous (user, assistant) message tuples
            
        Returns:
            str: The assistant's response
        """
        # Get response from our chat implementation
        return chat_interface.process_message(message, history)
    
    # Create the Gradio interface
    demo = gr.ChatInterface(
        fn=respond,
        title=titles[mode_str],
        type="messages",
        description=descriptions[mode_str],
        examples=examples,
        theme=gr.themes.Soft()
    )
    
    return demo