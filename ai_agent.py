import os
import json
from dotenv import load_dotenv
from typing import TypedDict , Sequence , Annotated , Optional , Dict , List
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage , AIMessage , BaseMessage
from langchain_community.document_loaders import CSVLoader
from langgraph.graph import StateGraph , START ,END
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
FILE_PATH="anomaly_label.csv"
persist_directory = "./vector_storage"
collection_name = "loghub_datase[HDFS1]"

llm = ChatAnthropic(model_name=MODEL_NAME)
embeddings = HuggingFaceEmbeddings(model_name =EMBEDDIING_MODEL_NAME)

loader = CSVLoader(
    file_path = FILE_PATH ,
    source_column=" BlockId" ,
    metadata_columns= ["Label"],
    csv_args={},
    encoding="utf-8"
)

loaded_dataset =loader.load()

if not loaded_dataset :
    print("There was a problem in processing the dataset file . Please try again")

chunkings = RecursiveCharacterTextSplitter(
    chunk_size = 4000 ,
    chunk_overlap =1000
)

splitted_dataset = chunkings.split_documents(loaded_dataset)

my_vectors = Chroma(
    embedding_function=embeddings,
    persist_directory= persist_directory ,
    collection_name= collection_name
    ) 
my_vectors.add_documents(splitted_dataset)

retriever = my_vectors.as_retriever(
    search_type ="similarity" ,
    search_kwargs ={"k":6}
)


def code_analyzer(state:AgentState)->AgentState:

    system_prompt = '''Identify interacting vulnerabilities from these findings and describe the resulting blast radius 
                       Args : system_findings :List[Dict]'''
    static_findings = state["static_findings"]
    prompt = f'{system_prompt}\n\n{static_findings}'
    response = llm.invoke(prompt)
    
    repsonse_json = response
    state["enriched_findings"] = response.content
    return state


def questionnaire_generator(state:AgentState)->AgentState:
    system_prompt =  '''Based on these specific risks, generate exactly 5 quantitative questions :
                        eg : -Requests Per Second ,
                             -Permitted Down Time , 
                             -Database size ,
                             -System Level Objective
                        to determine if this architecture will fail'''
    
    number_of_questions = 5
    enriched_findings =state["enriched_findings"]

    prompt = f'{system_prompt}\n\n{enriched_findings}'

    for i in range(number_of_questions):

        question = llm .invoke(prompt)
        state["questions"].append(
            f'Question {i+1} : {question.content}\n'
        )

        user_input =input("Enter your answer : ")

        state["developer_answers"].append ({
            "question  " : question ,
            "developer_answer " : user_input
        })
    return state
    
def Historian(state:AgentState)->AgentState:
    '''
                You are an SRE reviewing a code change against historical failure data.

                You are given:
                - enriched findings: vulnerabilities detected in the new code
                - Question-answer pairs : asked to the developer
               
                Your task: 
                 - Historical context: 3 real past incidents with similar failure patterns
                 Generate the Historical context
    '''
    enriched_findings= state["enriched_findings"]
    Interrogation_analysis =state["developer_answers"]
    query_to_retriever =f'Bugs found :{enriched_findings} , architectural expectations : {Interrogation_analysis}'

    results =retriever.invoke(query_to_retriever)

    if not results:
      state["historical_context"]=f'No relevant historical record was found based on the architectural demand of the user'
      return state

    historical_entries = []

    for id, i in enumerate(results):
       historical_entries.append(f" Historical Incident {id+1} :\n{i.page_content}")

    state["historical_context"] = "\n\n".join(historical_entries)

    return state

def final_risk_scorer(state:AgentState)->AgentState:
    system_prompt_combined ='''
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
      - the historical precedents provided,
        
      The output should be strictly in JSON format with this exact shape:
      {{"overall_risk": <float 0.0-10.0>, "risk_scores": {{"code_quality_risk": <float>, "traffic_capacity_risk": <float>, "historical_context": <float>}}}}
     '''

    enriched_findings= state["enriched_findings"]
    Interrogation_analysis =state["developer_answers"]
    historical_context =state["historical_context"]

    query_combined =f' {system_prompt_combined}\n\n Bugs :{enriched_findings}\n\n Interrogation analysis: {Interrogation_analysis} \n\n Historical context :{historical_context}'

    try:
        response = llm.invoke(query_combined)
        text = response.content.strip().replace("```json", "").replace("```", "")
        data = json.loads(text)
        state["overall_risk"] = data["overall_risk"]
        state["risk_scores"] = data["risk_scores"]

    except (json.JSONDecodeError, KeyError) as e:
        state["overall_risk"] = 5.0
        state["risk_scores"] = {"fallback_estimate": 5.0}
        state["note"] = f"LLM scoring failed ({e}), used fallback."

    if(state["overall_risk"] >=8.0):
        state["should_rollback"]=True

    else :
        state["should_rollback"]=False

    return state

graph =StateGraph(AgentState)
graph.add_node("code_analyzer", code_analyzer)
graph.add_node("questionnaire_generator" , questionnaire_generator)
graph.add_node("Historian", Historian)
graph.add_node("final_risk_scorer" ,final_risk_scorer)
graph.add_edge(START, "code_analyzer")
graph.add_edge("code_analyzer" ,"questionnaire_generator")
graph.add_edge("questionnaire_generator" ,"Historian")
graph.add_edge("Historian" ,"final_risk_scorer")
graph.add_edge("final_risk_scorer" ,END)

node3= graph.compile()
