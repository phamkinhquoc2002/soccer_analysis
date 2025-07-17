from abc import ABC
from typing import Annotated, List, Optional
from langchain_core.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from src.schemas import OrchestrationState
from src.prompts_template import agent_role_template, agent_tool_template, agent_instruction_template
from src.prompts import specialist_one_shot_prompt, specialist_system_prompt, orchestrator_instruction_prompt, orchestrator_system_prompt, orchestrator_tool_prompt
from abc import abstractmethod

class Agent(ABC):
    """
    Base Class for Agent.
    """
    def __init__(self, *args, **kwargs):
        pass
    
    @abstractmethod
    def __call__(self, *args, **kwargs):
        raise NotImplementedError

class Specialist(Agent):
    """
    Specialist in the system. Help retrieve essential metrics used for data analysis.
    """
    def __init__(self, llm: BaseChatModel, 
                 system_prompt: Optional[str] = None):
        
        if system_prompt is None:
            system_prompt = (
                agent_role_template.format(specialist_system_prompt)
                + agent_instruction_template.format(specialist_one_shot_prompt)
                )
        self.system_prompt = system_prompt
        self.llm = llm

    async def __call__(self, 
                       messages: Annotated[List[BaseMessage], "List of messages"]):
        if not isinstance(messages, list):
            raise TypeError("❌messages must be a list of BaseMessage")
        try:
            return await self.llm.ainvoke(
                [
                    {
                        "role":"system",
                        "content": self.system_prompt
                        }
                        ] + messages
                        )
        except Exception as e:
            raise RuntimeError(f"❌Specialist failed to invoke LLM: {e}")
        
class Orchestrator(Agent):
    """
    Orchestrator in the system. Help orchestrate the use of tools."""
    def __init__(self, llm: BaseChatModel, 
                 system_prompt: Optional[str] = None):
        
        if system_prompt is None:
            system_prompt = (
                agent_role_template.format(orchestrator_system_prompt) +
                agent_tool_template.format(orchestrator_tool_prompt) + agent_instruction_template.format(orchestrator_instruction_prompt)
            )
        self.system_prompt = system_prompt
        self.llm_with_structured_output = llm.with_structured_output(OrchestrationState) 

    async def __call__(self, 
                       messages: Annotated[List[BaseMessage], "List of messages"]) -> OrchestrationState:
        if not isinstance(messages, list):
            raise TypeError("❌messages need to be a list of Messages")
        
        try:
            return await self.llm_with_structured_output.ainvoke(
                [
                    {
                        "role": "system",
                        "content": self.system_prompt
                    }
                ] + messages
            )
        except Exception as e:
            raise RuntimeError(f"❌Orchestrator failed to invoke LLM: {e}")