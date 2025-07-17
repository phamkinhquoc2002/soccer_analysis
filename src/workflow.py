import logging
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.prebuilt import ToolNode
from langchain_core.language_models import BaseChatModel
from src.schemas import CurrentState, Done, OrchestrationState
from src.prompts_template import agent_role_template
from src.agents import Orchestrator, Specialist
from src.utils import parse_to_message


# === Logger Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

class Workflow:
    """Agent builder; instantiate via ``await Builder.create(llm)``"""

    def __init__(self, llm: BaseChatModel, tools):

        self.llm_with_tools = llm.bind_tools(tools) 
        self.tool_node = ToolNode(tools=tools)
        self.specialist = Specialist(llm=llm)
        self.orchestrator = Orchestrator(llm=llm)

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
        try:
            tools = await mcp.get_tools()
        except Exception as e:
            logger.exception(f"{e}")
            raise TimeoutError("Tools take too much time to load")
        for tool in tools:
            logger.info(f"✅ TOOL: {tool.name}")
        tools.append(Done)
        return cls(llm, tools)

    async def llm_tool_call(self, state: OrchestrationState):
        """Invoke the orchestrator prompt with tool bindings and return the raw AIMessage."""
        try:        
            ai_msg = await self.llm_with_tools.ainvoke(
            [
                {
                    "role": "system",
                    "content": agent_role_template.format("You are a tool-calling agent. Only respond with tool-calling message.")
                },
                {
                    "role": "user", 
                    "content": state["tool_call_request"]
                }
            ]
        )
            if ai_msg.tool_calls:
                return Command(
                    goto="tool_node",
                    update={
                        "messages": state["messages"] + [ai_msg],
                    }
                )
            else:
                logger.error(f"❌LLM returned wrong content format at tool_call step — can't proceed to tool_node.")
                raise ValueError("❌LLM returned wrong content format at tool_call step — can't proceed to tool_node.")
        except Exception as e:
            logger.error(f"❌ TOOL: {e}")
            raise ValueError(f"❌ TOOL: {e}")
    
    async def specialize(self, state: CurrentState) -> Command:
        if not state["messages"][-1].content.strip():
            raise ValueError("LLM returned empty content at specialist step — can't proceed to orchestrator_step.")
        try:
            ai_msg = await self.specialist(state["messages"])
        except Exception as e:
            logger.exception(f"{e}")
            raise e
        state["messages"].append(ai_msg)
        return Command(
            goto="orchestrator",
            update={"messages":state["messages"]}
        )

    async def orchestrate(self, state: CurrentState) -> Command:
        """Run the orchestrator step, append AI message, and branch."""

        if not not state["messages"][-1].content.strip():
            raise ValueError("LLM returned wrong content at orchestrator step — can't proceed to tool_call.")
        try: 
            orchestrate_state = await self.orchestrator(state["messages"])
        except Exception as e:
            logger.exception(f"{e}")
            raise e

        return Command(
            goto="tool_call",
            update={
                "messages": state["messages"] + parse_to_message(orchestrate_state),
                "orchestration_state": state["orchestration_state"] + orchestrate_state
                }
            )