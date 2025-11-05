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
        if use_solution:
            from perplexia_ai.solutions.week3.factory import Week3Mode, create_chat_implementation as create_chat
        else:
            from perplexia_ai.week3.factory import Week3Mode, create_chat_implementation as create_chat

        # Convert string to enum
        mode_map = {
            "part1": Week3Mode.PART1_TOOL_USING_AGENT,
            "part2": Week3Mode.PART2_AGENTIC_RAG,
            "part3": Week3Mode.PART3_DEEP_RESEARCH
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
            "part1": "Your intelligent AI assistant that autonomously decides which tools to use.",
            "part2": "Your intelligent AI assistant that dynamically controls its search strategy.",
            "part3": "Your multi-agent research system that creates comprehensive research reports."
        }
        
        if mode_str == "part1":
            examples = [
                ["Calculate 156 * 42"],
                ["What's the current date?"],
                ["What's the weather like in San Francisco?"],
                ["If I have $85.60 and leave a 18% tip, how much will I pay in total?"]
            ]
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