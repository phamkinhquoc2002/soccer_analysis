import os
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.prebuilt import ToolNode
from langchain_core.language_models import BaseChatModel
from src.schemas import CurrentState, Done
from typing import Literal
from src.prompts import specialist_one_shot_prompt, specialist_system_prompt, orchestrator_system_prompt, orchestrator_tool_prompt, orchestrator_instruction_prompt
from src.prompts_template import agent_role_template, agent_instruction_prompt, agent_tool_prompt

mcp = MultiServerMCPClient(
    {
        "visualization": {
            "command":"python",
            "args": ["./src/mcp/visualizer_server.py"],
            "transport":"stdio",
            "env": {"DB_PATH": "./etl/soccer_analysis.db", "SERVING_DIR": "./etl/serving"},
        },

        "database_manager": {
            "command":"python",
            "args": ["./src/mcp/sqlite_manager_server.py"],
            "transport":"stdio",
            "env": {"DB_PATH": "./etl/soccer_analysis.db", "SERVING_DIR": "./etl/serving"},
        },

        "data_analyst_server": {
            "command":"python",
            "args": ["./src/mcp/data_analyst_server.py"],
            "transport":"stdio",
            "env": {"DB_PATH": "./etl/soccer_analysis.db", "SERVING_DIR": "./etl/serving"},
        },
    }
)

def route_after_tool(state: CurrentState):
    """After tool execution decide whether to continue or finish.
    If the last message is a Done tool-call result, finish; otherwise go to tool_call for next step."""
    last = state["messages"][-1]
    if isinstance(last, Done):
        return END
    return "orchestrator"

class Builder:
    """Agent builder; instantiate via ``await Builder.create(llm)``"""

    def __init__(self, llm: BaseChatModel, tools):
        self.model = llm
        self.tools = tools
        self.llm_with_tools = llm.bind_tools(tools) 
        # tool execution handler
        self.tool_node = ToolNode(tools=tools)

        graph = StateGraph(CurrentState)
        graph.add_node("specialist", self.specialize)
        graph.add_node("orchestrator", self.orchestrate)
        graph.add_node("tool_call", self.llm_tool_call)
        graph.add_node("tool_node", self.tool_node)
        # graph edges
        graph.add_edge(START, "specialist")
        graph.add_edge("specialist", "orchestrator")
        graph.add_edge("orchestrator", "tool_call")
        graph.add_edge("tool_call", "tool_node")
        # After each tool_node execution, decide next step
        graph.add_conditional_edges(
            "tool_node",
            route_after_tool,
            {"orchestrator": "orchestrator", END: END},
        )
        self.graph = graph.compile()

    @classmethod
    async def create(cls, llm: BaseChatModel):
        tools = await mcp.get_tools()
        tools.append(Done)
        for tool in tools:
            print("✅ TOOL:", tool)
        return cls(llm, tools)

    async def llm_tool_call(self, state: CurrentState):
        """Invoke the orchestrator prompt with tool bindings and return the raw AIMessage."""
        try:        
            response = await self.llm_with_tools.ainvoke(
            [
                {
                    "role": "system",
                    "content": agent_role_template.format("You are a tool-calling agent. Only respond with tool-calling message.")
                },
                {
                    "role": "user", 
                    "content": state["tool_call_reasoning"]
                }
            ]
        )
            if response.tool_calls:
                
                return Command(
                    goto="tool_node",
                    update={
                        "messages": state["messages"] + [response],
                    }
                )
            else:
                raise ValueError("LLM returned wrong content format at tool_call step — can't proceed to tool_node.")
        except Exception as e:
            raise ValueError(f"❌ TOOL: {e}")
    
    async def specialize(self, state: CurrentState):
        if not state["messages"][-1].content.strip():
            raise ValueError("LLM returned empty content at specialist step — can't proceed to orchestrator_step.")
        response = await self.model.ainvoke(
            [
                {"role": "system", "content": agent_role_template.format(specialist_system_prompt) +
                 agent_instruction_prompt.format(specialist_one_shot_prompt)},
            ] + state["messages"]
        )
        state["messages"].append(response)
        return Command(
            goto="orchestrator",
            update={"messages":state["messages"]}
        )

    async def orchestrate(self, state: CurrentState):
        """Run the orchestrator step, append AI message, and branch."""
        ai_msg = await self.model.ainvoke(
            [
                {
                    "role": "system",
                    "content": (
                        agent_role_template.format(orchestrator_system_prompt)
                        + agent_tool_prompt.format(orchestrator_tool_prompt)
                        + agent_instruction_prompt.format(orchestrator_instruction_prompt)
                    ),
                }
            ] + state["messages"]
        )

        state["messages"].append(ai_msg)
        if not ai_msg.content.strip():
            raise ValueError("LLM returned empty content at orchestrator step — can't proceed to tool_call.")

        return Command(
            goto="tool_call",
            update={
                "messages": state["messages"],
                "tool_call_reasoning": ai_msg.content.strip()
                }
            )