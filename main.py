import os
from dotenv import load_dotenv
from typing import TypedDict , Sequence , Annotated , Optional , Dict , List
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage , AIMessage , BaseMessage
from langgraph import StateGraph , START ,END
from langgraph.graph import add_messages
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.tools import tool
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_anthropic import ChatAnthropic

load_dotenv()

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

if not CLAUDE_API_KEY:
    print ("ALERT: Missing api key !")

class AgentState(TypedDict):
    static_findings : List[Dict] 
    enriched_findings : str 
    questions : List[str] 
    developer_answers : Dict 
    historical_context : str 
    overall_risk :float 
    risk_scores :Dict
    should_rollback :bool

MODEL_NAME = "claude-sonnet-4-6"
EMBEDDIING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
llm = ChatAnthropic(model_name=MODEL_NAME)
embeddings = HuggingFaceEmbeddings(EMBEDDIING_MODEL_NAME)

@tool
def code_analyser(state:AgentState):

    system_prompt = '''Identify interacting vulnerabilities from these findings and describe the resulting blast radius.'''
    query = state["static_findings"]
    prompt = f'{system_prompt}\n\n{query}'
    response = llm.invoke()
    
    repsonse_json = response
    state["enriched_findings"] = response.content