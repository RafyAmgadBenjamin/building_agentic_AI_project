"""Factory for creating Week 3 implementations.

This module contains factory methods for creating the appropriate chat implementation
based on the selected Week 3 mode.
"""

from enum import Enum
from iac_agent.core.chat_interface import ChatInterface
from iac_agent.week3.part1 import IacAgentChat
from iac_agent.week3.part2 import AgenticRAGChat
from iac_agent.week3.part3 import DeepResearchChat


class ProjectIteration(Enum):
    """Enum for different project iteration implementations."""
    IAC_AGENT = "part1"
    AGENTIC_RAG = "part2"
    DEEP_RESEARCH = "part3"


def create_chat_implementation(iteration: ProjectIteration) -> ChatInterface:
    """Create a chat implementation for the specified project iteration.
    
    Args:
        iteration: Which project iteration to use
    Returns:
        ChatInterface: The initialized chat implementation
    """
    if iteration == ProjectIteration.IAC_AGENT:
        return IacAgentChat()
    elif iteration == ProjectIteration.AGENTIC_RAG:
        return AgenticRAGChat()
    elif iteration == ProjectIteration.DEEP_RESEARCH:
        return DeepResearchChat()
    else:
        raise ValueError(f"Unknown iteration: {iteration}")

