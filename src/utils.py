import json
from langchain_core.messages import BaseMessage, AIMessage
from pydantic import BaseModel
from typing import Any

def parse_to_message(obj: Any) -> BaseMessage:
    """
    Parse any object into an AIMessage for logging/tracing in LangGraph.

    - If the object is a Pydantic model, dump as JSON.
    - If it's already a string, return as-is.
    - If it's a dict, serialize it.
    - Fallback: use str().
    """
    if isinstance(obj, BaseModel):
        content = obj.model_dump_json(indent=2)
    elif isinstance(obj, dict):
        content = json.dumps(obj, indent=2)
    elif isinstance(obj, str):
        content = obj
    else:
        # fallback to raw string
        content = str(obj)
    
    return AIMessage(content=content)
    
def show_graph(graph, xray=False):
    """Display a LangGraph mermaid diagram with fallback rendering.
    
    Handles timeout errors from mermaid.ink by falling back to pyppeteer.
    
    Args:
        graph: The LangGraph object that has a get_graph() method
    """
    from IPython.display import Image
    try:
        # Try the default renderer first
        return Image(graph.get_graph(xray=xray).draw_mermaid_png())
    except Exception as e:
        # Fall back to pyppeteer if the default renderer fails
        import nest_asyncio
        nest_asyncio.apply()
        from langchain_core.runnables.graph import MermaidDrawMethod
        return Image(graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.PYPPETEER))