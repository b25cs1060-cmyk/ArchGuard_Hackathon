import os
import json
from dotenv import load_dotenv
from typing import TypedDict, Dict, List

from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
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

    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    db_available = True
    print("AI Agent connected to Pinecone Cloud!")
except Exception as e:
    print(f"Pinecone Connection Warning: {e}. Historical context will be skipped.")
    db_available = False



class AgentState(TypedDict):
    static_findings: List[Dict] 
    enriched_findings: str 
    developer_answers: str    
    historical_context: str 
    questions: List[str]        
    scenarios: str              
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
    
def Historian(state: AgentState) -> AgentState:
    if not db_available:
        state["historical_context"] = "No historical logs available."
        return state

    query = f'Bugs: {state.get("enriched_findings", "")}, Developer Context: {state.get("developer_answers", "")}'
    results = retriever.invoke(query)

    if not results:
        state["historical_context"] = 'No relevant historical records found.'
        return state

    raw_logs = "\n\n".join([f"--- Historical Log {id+1} ---\n{i.page_content}" for id, i in enumerate(results)])
    

    system_prompt = '''You are a Senior DevOps Engineer analyzing past system incidents. 
    Read the following raw system logs retrieved from our database. 
    Summarize the historical cause of failure shown in these logs in 2 to 3 clear, human-readable sentences. 
    Explain what went wrong in the past so a developer can understand the precedent. 
    Do not output raw log lines or timestamps.'''
    
    prompt = f'{system_prompt}\n\nRaw Logs:\n{raw_logs}'
    
    try:
        response = llm.invoke(prompt)

        state["historical_context"] = response.content.strip()
    except Exception as e:
        state["historical_context"] = f"Historical logs found, but AI failed to summarize: {str(e)}"

    return state

def questionnaire_generator(state: AgentState) -> AgentState:

    system_prompt = '''Based on these specific risks, generate exactly 5 quantitative questions :
                       eg : -Requests Per Second ,
                            -Permitted Down Time ,
                            -Database size ,
                            -System Level Objective
                       to determine if this architecture will fail'''
                       
    enriched_findings = state.get("enriched_findings", "")

    prompt = f'{system_prompt}\n\n{enriched_findings}'
    

    response = llm.invoke(prompt)
    state["questions"] = [response.content]
    
    return state

def scenario_planner(state: AgentState) -> AgentState:
    """LAYER 4: Generates the Best vs Worst case scenarios for the dashboard."""
    prompt = f'''
    You are a Senior Site Reliability Engineer. Look at the code flaws and the historical system logs.
    Provide a realistic Best Case and Worst Case scenario if this Pull Request is merged into production.
    Keep them punchy and professional.
    
    Vulnerabilities: {state.get("enriched_findings")}
    Historical Logs: {state.get("historical_context")}
    
    Output strictly in this format:
    BEST CASE: [Your sentence here]
    WORST CASE: [Your sentence here]
    '''
    response = llm.invoke(prompt)
    state["scenarios"] = response.content
    return state

def final_risk_scorer(state: AgentState) -> AgentState:
 
    system_prompt_combined = '''
    Score the deployment risk from 0.0 to 10.0 using the 
     - code flaws 
     - the expected traffic,
     - the historical precedents provided.
    
    Also score the various deployment parameters like :
     -code_quality_risk
     -traffic_capacity_risk
     -historical_context
     
    based on arguments provided to you like :
     - code flaws
     - the expected traffic,
     - the historical precedents provided.
     
    The output should be strictly in JSON format with this exact shape:
    {"overall_risk": <float 0.0-10.0>, "risk_scores": {"code_quality_risk": <float>, "traffic_capacity_risk": <float>, "historical_context": <float>}}
    '''
    
    enriched_findings = state.get("enriched_findings", "")

    Interrogation_analysis = state.get("developer_answers", "")
    historical_context = state.get("historical_context", "")
    
 
    query_combined = f'{system_prompt_combined}\n\n Bugs :{enriched_findings}\n\n Interrogation analysis: {Interrogation_analysis} \n\n historical context: {historical_context}'
    
    try:
        response = llm.invoke(query_combined)

        text = response.content.strip().replace("```json", "").replace("```", "")
        data = json.loads(text)
        
        state["overall_risk"] = data.get("overall_risk", 5.0)
        state["risk_scores"] = data.get("risk_scores", {})
        
    except (json.JSONDecodeError, KeyError) as e:

        state["overall_risk"] = 5.0
        state["risk_scores"] = {"fallback_estimate": 5.0}
        state["note"] = f"LLM scoring failed ({e}), used fallback."
        

    if state.get("overall_risk", 0) >= 8.0:
        state["should_rollback"] = True
    else:
        state["should_rollback"] = False
        
    return state


graph = StateGraph(AgentState)
graph.add_node("code_analyzer", code_analyzer)
graph.add_node("questionnaire_generator", questionnaire_generator)
graph.add_node("Historian", Historian)
graph.add_node("scenario_planner", scenario_planner)
graph.add_node("final_risk_scorer", final_risk_scorer)


graph.add_edge(START, "code_analyzer")
graph.add_edge("code_analyzer", "questionnaire_generator")
graph.add_edge("questionnaire_generator", "Historian") 
graph.add_edge("Historian", "scenario_planner")
graph.add_edge("scenario_planner", "final_risk_scorer")
graph.add_edge("final_risk_scorer", END)


memory = MemorySaver()
archguard_ai = graph.compile(
    checkpointer=memory, 
    interrupt_after=["questionnaire_generator"] 
)



def start_review_and_ask_questions(static_findings: list, thread_id: str) -> dict:
    """Starts the graph and pauses after generating questions."""
    initial_state = {
        "static_findings": static_findings,
        "enriched_findings": "",
        "developer_answers": "",
        "historical_context": "",
        "questions": [],
        "scenarios": "",
        "overall_risk": 0.0,
        "risk_scores": {},
        "should_rollback": False
    }
    
    config = {"configurable": {"thread_id": thread_id}}
    print(f"Starting AI Agent for PR {thread_id}... Generating questions...")

    current_state = archguard_ai.invoke(initial_state, config)

    return {"questions": current_state.get("questions", [])}


def resume_review_with_answers(thread_id: str, user_answers: str) -> dict:
    """Wakes the graph up, injects the user's answers, and finishes the review."""
    config = {"configurable": {"thread_id": thread_id}}
    print(f"Resuming AI Agent for PR {thread_id} with developer context...")

    archguard_ai.update_state(config, {"developer_answers": user_answers})

    final_state = archguard_ai.invoke(None, config)
    return final_state