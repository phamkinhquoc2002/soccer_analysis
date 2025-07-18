import logging
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.prebuilt import ToolNode
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from src.schemas import CurrentState, Done
from src.prompts_template import agent_role_template
from src.agents import Orchestrator, Specialist
from src.utils import parse_to_message
from src.prompts_template import tool_calling_prompt_template

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
    """
    After tool execution, decide whether to continue or finish.
    If the last tool-call result is 'Done', then finish.
    """
    last = state["messages"][-1]
    logger.info(f"🧭 Routing decision — last message: {type(last)}, content: {getattr(last, 'content', None)}")
    if isinstance(last, Done):
        return END
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tool_result_store"
    if getattr(last, "name", None) == "Done":
        return END
    if hasattr(last, "content") and "Done" in last.content:
        return END

    return "tool_result_store"

class Workflow:
    """Agent workflow builder; instantiate via ``await Workflow.create(llm)``"""

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
        graph.add_node("tool_result_store", self.tool_result_store)
        # graph edges
        graph.add_edge(START, "specialist")
        graph.add_edge("specialist", "orchestrator")
        graph.add_edge("orchestrator", "tool_call")
        graph.add_edge("tool_call", "tool_node")
        # After each tool_node execution, decide next step
        graph.add_conditional_edges(
            "tool_node",
            route_after_tool,
            {"tool_result_store": "tool_result_store", END: END},
        )
        graph.add_edge("tool_result_store", "orchestrator")
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

    async def llm_tool_call(self, state: CurrentState) -> Command:
        """Invoke the orchestrator prompt with tool bindings and return the raw AIMessage."""
        try: 
            if isinstance(state.get("prev_tool_call_request"), str):
                tool_call_request =  state.get("prev_tool_call_request")
            ai_msg = await self.llm_with_tools.ainvoke(
            [
                {
                    "role": "system",
                    "content": agent_role_template.format("You are a tool-calling agent. Only respond with tool-calling message.")
                },
                {
                    "role": "user", 
                    "content": tool_call_request
                }
            ]
        )
            if hasattr(ai_msg, "tool_calls") and ai_msg.tool_calls:
                logger.info(f"🔧 TOOL CALL | Tool Calls: {ai_msg.tool_calls}")
                state["messages"] = state["messages"] + [ai_msg]
                return Command(
                    goto="tool_node",
                    update={
                        "messages": state["messages"],
                    }
                )
            else:
                logger.error(f"❌LLM returned wrong content format at tool_call step — can't proceed to tool_node.")
                raise ValueError("❌Wrong format for ToolMessage.")
        except Exception as e:
            logger.error(f"❌: {e}")
            raise ValueError(f"❌ {e}")
        
    async def tool_result_store(self, state: CurrentState) -> Command:
        try:
            tool_msg = state["messages"][-1]
            tool_name = getattr(tool_msg, "name")
            content = getattr(tool_msg, "content")
            
            if hasattr(state, "insights") == False:
                state["insights"] = []
            state["insights"].append(f"🔧 TOOL CALL | Tool Name: {tool_name}  Tool Result: {content}")
            logger.info(f"🔧 TOOL CALL | Tool Name: {tool_name}  Tool Result: {content}")
            return Command(
                goto="orchestrator",
                update={
                    "prev_tool_name": tool_name,
                    "prev_tool_result": content,
                    "insights": state["insights"]
                    }
            )
        except Exception as e:
            logger.error(f"❌ {e}")
            raise ValueError(f"❌ {e}")
    
    async def specialize(self, state: CurrentState) -> Command:
        if not state["messages"][-1].content.strip():
            raise ValueError("LLM returned empty/malformed content at specialist step — can't proceed to orchestrator_step.")
        try:
            ai_msg = await self.specialist(state["messages"])
        except Exception as e:
            logger.exception(f"❌ {e}")
            raise ValueError(f"❌ {e}")
        state["messages"].append(ai_msg)
        logger.info(f"📦 SPECIALIST | Request: {ai_msg.content}")
        return Command(
            goto="orchestrator",
            update={"messages":state["messages"]}
        )

    async def orchestrate(self, state: CurrentState) -> Command:
        """Run the orchestrator step, append AI message, and branch."""

        if not state["messages"][-1].content.strip():
            raise ValueError("LLM returned wrong content at orchestrator step — can't proceed to tool_call.")
        try: 
            if (
                isinstance(state.get("prev_tool_result", None), str)
                and isinstance(state.get("prev_tool_name", None), str)
                and isinstance(state.get("prev_tool_reasoning", None), str)
                and isinstance(state.get("insights", None), list)
                ):
                tool_result = state["prev_tool_result"]
                tool_name = state["prev_tool_name"]
                tool_reasoning = state["prev_tool_reasoning"]
                insights = state["insights"]
                tool_calling_prompt = tool_calling_prompt_template.format(
                    '\n'.join(insight for insight in insights),
                    state["messages"][0].content,
                    state["messages"][1].content,
                    tool_reasoning,
                    tool_name,
                    tool_result
                )
            else:
                tool_calling_prompt = tool_calling_prompt_template.format(
                    "<not yet>",
                    state["messages"][0].content,
                    state["messages"][1].content,
                    "<not yet>",
                    "<not yet>",
                    "<not yet>"
                )
            orchestrate_state = await self.orchestrator([AIMessage(content=tool_calling_prompt)])
            ai_msg = parse_to_message(orchestrate_state)
            logger.info(f"🔧 TOOL CALL | Request: {orchestrate_state.get('tool_call_request', '[none]')}")
            logger.info(f"🧠 ORCHESTRATOR | Reasoning: {orchestrate_state.get('reasoning', '[none]')}")
        except Exception as e:
            logger.exception(f"❌: {e}")
            raise e
        state["messages"].append(ai_msg)
        return Command(
            goto="tool_call",
            update={
                "messages": state["messages"],
                "prev_tool_call_request": orchestrate_state["tool_call_request"],
                "prev_tool_reasoning": orchestrate_state["reasoning"]
                }
            )