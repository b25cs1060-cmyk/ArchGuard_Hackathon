import os
import json
from dotenv import load_dotenv
from typing import TypedDict, Dict, List

from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not GROQ_API_KEY or not PINECONE_API_KEY:
    print("ALERT: Missing API keys in your .env file!")


llm = ChatGroq(
    temperature=0, 
    model_name="llama-3.3-70b-versatile", 
    api_key=GROQ_API_KEY
)


print("Initializing LangGraph AI Agent & Vector Engine...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
index_name = os.getenv("PINECONE_INDEX_NAME", "archguard-logs")

try:

    vector_store = PineconeVectorStore.from_existing_index(
        index_name=index_name,
        embedding=embeddings
    )
    # Configure it to return the top 3 most relevant historical logs
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    db_available = True
    print("AI Agent connected to Pinecone Cloud!")
except Exception as e:
    print(f"Pinecone Connection Warning: {e}. Historical context will be skipped.")
    db_available = False



class AgentState(TypedDict):
    static_findings: List[Dict] 
    enriched_findings: str 
    questions: List[str] 
    developer_answers: str 
    historical_context: str 
    overall_risk: float 
    risk_scores: Dict
    should_rollback: bool



def code_analyzer(state: AgentState) -> AgentState:
    system_prompt = '''Identify interacting vulnerabilities from these findings and describe the resulting blast radius.'''
    static_findings = state.get("static_findings", [])
    
    if not static_findings:
        state["enriched_findings"] = "No structural vulnerabilities detected by static analysis."
        return state

    prompt = f'{system_prompt}\n\nFindings: {json.dumps(static_findings)}'
    response = llm.invoke(prompt)
    state["enriched_findings"] = response.content
    return state

def questionnaire_generator(state: AgentState) -> AgentState:
    system_prompt = '''Based on these specific risks, generate exactly 5 quantitative questions 
                       (e.g., Requests Per Second, Permitted Down Time) to determine if this architecture will fail.'''
    
    prompt = f'{system_prompt}\n\n{state.get("enriched_findings", "")}'
    response = llm.invoke(prompt)
    state["questions"] = [response.content]
    return state
    
def Historian(state: AgentState) -> AgentState:
    if not db_available:
        state["historical_context"] = "No historical logs available."
        return state


    query = f'Bugs: {state.get("enriched_findings", "")}, architecture context: {state.get("developer_answers", "")}'
    results = retriever.invoke(query)

    if not results:
        state["historical_context"] = 'No relevant historical records found.'
        return state


    historical_entries = [f"--- Historical Log Pattern {id+1} ---\n{i.page_content}" for id, i in enumerate(results)]
    state["historical_context"] = "\n\n".join(historical_entries)
    return state

def final_risk_scorer(state: AgentState) -> AgentState:
    system_prompt_combined = '''
     Score the deployment risk from 0.0 to 10.0 using the code flaws, expected traffic, and historical log precedents.
     The output MUST be strictly in JSON format with this exact shape, nothing else:
     {"overall_risk": 7.5, "risk_scores": {"code_quality_risk": 8.0, "traffic_capacity_risk": 6.5, "historical_context": 7.0}}
     '''

    query_combined = f'{system_prompt_combined}\n\nBugs: {state.get("enriched_findings", "")}\nDeveloper Context: {state.get("developer_answers", "")}\nHistory: {state.get("historical_context", "")}'

    try:
        response = llm.invoke(query_combined)
        text = response.content.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()
            
        data = json.loads(text)
        state["overall_risk"] = float(data.get("overall_risk", 5.0))
        state["risk_scores"] = data.get("risk_scores", {})
    except Exception as e:
        state["overall_risk"] = 5.0
        state["risk_scores"] = {"error": f"LLM failed to format JSON: {e}"}


    state["should_rollback"] = bool(state["overall_risk"] >= 8.0)
    return state



graph = StateGraph(AgentState)
graph.add_node("code_analyzer", code_analyzer)
graph.add_node("questionnaire_generator", questionnaire_generator)
graph.add_node("Historian", Historian)
graph.add_node("final_risk_scorer", final_risk_scorer)

graph.add_edge(START, "code_analyzer")
graph.add_edge("code_analyzer", "questionnaire_generator")
graph.add_edge("questionnaire_generator", "Historian")
graph.add_edge("Historian", "final_risk_scorer")
graph.add_edge("final_risk_scorer", END)

archguard_ai = graph.compile()



def run_archguard_review(static_findings: list, dev_context: str) -> dict:
    """Invokes the LangGraph AI Agent from the FastAPI server."""
    initial_state = {
        "static_findings": static_findings,
        "enriched_findings": "",
        "questions": [],
        "developer_answers": dev_context,
        "historical_context": "",
        "overall_risk": 0.0,
        "risk_scores": {},
        "should_rollback": False
    }
    
    print("AI Agent running full review pipeline...")
    result = archguard_ai.invoke(initial_state)
    return result