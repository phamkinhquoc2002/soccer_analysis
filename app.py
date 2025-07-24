import uvicorn
from typing import Annotated
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.errors import GraphRecursionError
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
import os
import logging
import asyncio

from src.workflow import Workflow
from langchain_core.messages import HumanMessage

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def model_configure():
    try:
        agent = await Workflow.create(
            gemini_model
        )
        logger.info("Successfully created agentic workflow.")
        return agent
    except Exception as e:
        logger.error("❌: {e}")
        raise e

try:
    google_api_key = os.environ["GOOGLE_API_KEY"]
    gemini_model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        google_api_key=google_api_key
    )
    agentic_workflow = asyncio.run(model_configure())
except Exception as e:
    logger.error(f"❌: {e}")
    
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/ask")
async def ask(
    query: Annotated[str, Form(...)],
    recursion_limit: Annotated[int, Form(...)]
):
    try:
        initial_state = {
            "messages": [HumanMessage(content=query)]
            }
        async for _ in agentic_workflow.graph.astream(initial_state, config={"recursion_limit": recursion_limit}):
            logger.info("🔁 CURRENT STATE:")
    except Exception as e:
        logger.error(f"❌: {e}")
        return JSONResponse(
            status_code=400,
            content=f"❌: {e}"
        )
    except GraphRecursionError as e:
        logger.error(f"❌: {e}")
        return JSONResponse(
            status_code=400,
            content=f"❌: You should increase the recursion limit. Current configuration is not enough for this task."
        )
if __name__ == "__main__":
    uvicorn.run(app=app, port=8000)