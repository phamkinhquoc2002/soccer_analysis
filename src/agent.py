import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START
from langgraph.types import Command
from langchain.chat_models import init_chat_model
from schemas import CurrentState
from prompts import specialist_one_shot_prompt, specialist_system_prompt
from prompts_template import agent_role_template, agent_instruction_prompt, orchestrator_system_prompt, orchestrator_tool_prompt

try: 
    model_name = os.environ["MODEL_NAME"]
except Exception as e:
    raise ValueError("Cant find the model name defined in .env")

visualization_tool = MultiServerMCPClient(
    {
        "visualization": {
            "command":"python",
            "args": ["./mcp/visualizer_server.py"],
            "transport":"stdio"
        },
    }
)

database_tool = MultiServerMCPClient(
    {
        "database_manager": {
            "command":"python",
            "args": ["./mcp/sqlite_manager_server.py"],
            "transport":"stdio"
        }
    }
)

data_analyst_tool = MultiServerMCPClient(
    {
        "data_analyst_server": {
            "command":"python",
            "args": ["./mcp/data_analyst_server.py"],
            "transport":"stdio"
            }  
    }   
)

visualization_tools =  visualization_tool.get_tools()
database_tools = database_tool.get_tools()
data_analyst_tools = data_analyst_tool.get_tools()
llm = init_chat_model(model_name)

def tool_call():
    pass

class Builder():
    def __init__(self):
        self.model = llm
        graph = StateGraph(CurrentState)
        graph.add_node("specialist", self.reason)
        graph.add_node("orchestrator", self.orchestrator)
        graph.add_edge(START, "specialist")
        graph.add_edge("specialist", "orchestrator")

    def reason(self, state: CurrentState):
        response = self.model.invoke(
            [
                {"role": "system", "content": agent_role_template.format(specialist_system_prompt) + agent_instruction_prompt.format(specialist_one_shot_prompt)},
                {"role": "user", "content": state["messages"]},
            ]
        )
        state["messages"].append(response)
        return Command(
            goto="orchestrator",
            update={"messages":state["messages"]}
        )
    
    def orchestrate(self, state: CurrentState):
        response = self.model.invoke(
            [
                {"role": "system", "content": agent_role_template.format()},
                {"role": "user", "content": state["messages"]}
            ]
        )
    