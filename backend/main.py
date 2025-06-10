import os
import datetime
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

# --- Pydantic Models with Finalized Descriptions ---
# These descriptions are aligned with the new, stricter prompt.
class Interaction(BaseModel):
    hcp_name: str = Field(..., description="Full name of the Healthcare Professional.")
    interaction_type: Optional[str] = Field(None, description="The type of interaction. Must be one of: 'Scheduled Visit', 'Unscheduled Visit', 'Phone Call', 'Email', 'Conference'.")
    interaction_date: Optional[str] = Field(None, description="The date of the interaction in YYYY-MM-DD format.")
    interaction_time: Optional[str] = Field(None, description="The time in 24-hour HH:mm format. Must be null if not mentioned.")
    attendees: Optional[str] = Field(None, description="Other individuals present, comma-separated. Must be null if not mentioned.")
    topics_discussed: Optional[str] = Field(None, description="A summary of what was talked about.")
    materials_shared: Optional[str] = Field(None, description="Specific materials, brochures, or samples that were given. Must be null if not mentioned.")
    observed_sentiment: Optional[str] = Field(None, description="The HCP's sentiment. Must be one of: 'Positive', 'Neutral', 'Negative', 'Inquisitive'.")
    outcomes: Optional[str] = Field(None, description="Key results or agreements from the interaction.")
    follow_up_actions: Optional[str] = Field(None, description="Explicit next steps or future tasks for the sales rep.")

class ChatMessage(BaseModel):
    text: str

# --- AI Agent Setup ---
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from typing import TypedDict
from langgraph.graph import StateGraph, END

llm = ChatGroq(model="gemma2-9b-it", temperature=0)
structured_llm = llm.with_structured_output(Interaction)

class AgentState(TypedDict):
    raw_text: str
    extracted_data: Optional[Interaction]

def extract_details(state: AgentState):
    print("---AGENT: EXTRACTING DETAILS (v4 - Final)---")
    raw_text = state['raw_text']

    # --- DEFINITIVE PROMPT - Overhauled for maximum precision ---
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""You are a highly precise data extraction engine. Your task is to convert a user's text into a structured JSON object based on the `Interaction` model. You MUST follow these rules precisely:

1.  **Extraction:** Read the user's text and identify values for each field in the `Interaction` schema.
2.  **Null Handling:** If a value for ANY field is not explicitly mentioned in the text, you MUST set its value to `null`. Do not infer or make up information.
3.  **Date Inference:** Today's date is {datetime.datetime.now().strftime('%Y-%m-%d')}. Use this to resolve 'today' or 'yesterday'.
4.  **Field-Specific Rules:**
    - `hcp_name`: Extract the doctor's or healthcare professional's full name.
    - `interaction_type`: Classify the interaction. Look for keywords like 'met with' (Scheduled Visit), 'dropped by' (Unscheduled Visit), 'phone call' or 'spoke with' (Phone Call), 'emailed' (Email).
    - `interaction_time`: Find the time and convert it to strict 24-hour HH:mm format (e.g., '2:30 PM' becomes '14:30'). If no time is mentioned, it MUST be `null`.
    - `attendees`: List any other people mentioned by name or role. If none, it MUST be `null`.
    - `topics_discussed`: Summarize the main points of the conversation.
    - `materials_shared`: Look for specific items mentioned like 'samples', 'brochures', 'formulary guide', 'trial data'. If none, it MUST be `null`.
    - `observed_sentiment`: Infer the HCP's attitude (Positive, Neutral, Negative, Inquisitive).
    - `outcomes`: Note any decisions or conclusions reached.
    - `follow_up_actions`: Extract any future tasks for the rep, like 'send an email' or 'follow up in 2 weeks'.
"""),
        ("human", "{text_input}")
    ])

    chain = prompt | structured_llm
    try:
        extracted_data = chain.invoke({"text_input": raw_text})
        return {"extracted_data": extracted_data}
    except Exception as e:
        print(f"Error during extraction: {e}")
        # Return a dictionary with a None value for the data to avoid breaking the graph
        return {"extracted_data": None}

# Using a simple sequential graph as the logic is now fully contained in the prompt
workflow = StateGraph(AgentState)
workflow.add_node("extractor", extract_details)
workflow.set_entry_point("extractor")
workflow.add_edge("extractor", END)
agent_graph = workflow.compile()


# --- FastAPI Application ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/chat_interaction")
async def chat_interaction_endpoint(message: ChatMessage):
    print(f"Received text for AI processing: {message.text}")
    try:
        result = agent_graph.invoke({"raw_text": message.text})
        extracted_data = result.get('extracted_data')
        if not extracted_data:
            raise HTTPException(status_code=400, detail="AI could not extract details. Please be more specific or check the format.")
        print("Returning extracted data to frontend:")
        print(extracted_data.dict())
        return extracted_data
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "AI-First CRM Backend is running."}