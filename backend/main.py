import os
import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Any

# Database Imports
from sqlalchemy import create_engine, Column, Integer, String, Date, Time, Text, TIMESTAMP, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# AI Agent Imports
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import tool
from langchain_groq import ChatGroq

# Environment and Config
from dotenv import load_dotenv
load_dotenv()

# --- 1. DATABASE SETUP & ORM MODEL ---
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class InteractionDB(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True, index=True); created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow); hcp_name = Column(String, index=True, nullable=False); interaction_type = Column(String); interaction_date = Column(Date); interaction_time = Column(Time); attendees = Column(Text); topics_discussed = Column(Text); materials_shared = Column(Text); observed_sentiment = Column(String); outcomes = Column(Text); follow_up_actions = Column(Text)

# --- 2. PYDANTIC SCHEMAS ---
class InteractionBase(BaseModel):
    hcp_name: str; interaction_type: Optional[str] = None; interaction_date: Optional[datetime.date] = None; interaction_time: Optional[datetime.time] = None; attendees: Optional[str] = None; topics_discussed: Optional[str] = None; materials_shared: Optional[str] = None; observed_sentiment: Optional[str] = None; outcomes: Optional[str] = None; follow_up_actions: Optional[str] = None
class InteractionCreate(InteractionBase): pass
class InteractionRead(InteractionBase):
    id: int; created_at: datetime.datetime
    class Config: from_attributes = True
class ChatMessage(BaseModel): text: str
class AgentResponse(BaseModel):
    response_type: str; data: Any

# --- 3. FastAPI APP & MIDDLEWARE ---
app = FastAPI(title="AI-First CRM API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- 4. DATABASE HELPERS & STARTUP ---
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.on_event("startup")
def on_startup(): Base.metadata.create_all(bind=engine)

# --- 5. CRUD ENDPOINTS ---
@app.post("/api/interactions", response_model=InteractionRead, summary="Save a New Interaction")
def save_interaction(interaction: InteractionCreate, db: Session = Depends(get_db)):
    db_interaction = InteractionDB(**interaction.model_dump()); db.add(db_interaction); db.commit(); db.refresh(db_interaction)
    return db_interaction

@app.get("/api/interactions", response_model=List[InteractionRead], summary="Get All Interactions")
def get_all_interactions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(InteractionDB).order_by(InteractionDB.id.desc()).offset(skip).limit(limit).all()

# --- 6. MOCK DATA & AI TOOL DEFINITIONS ---
MOCK_CLINICAL_DATA = { "valcor": "...", "aether-d": "...", "solara": "..." }

class LogInteractionToolArgs(BaseModel):
    hcp_name: str = Field(description="Full name of the Healthcare Professional."); interaction_type: Optional[str] = Field(None, description="Must be one of: 'Scheduled Visit', 'Unscheduled Visit', 'Phone Call', 'Email', 'Conference'."); interaction_date: Optional[str] = Field(None, description=f"Date in YYYY-MM-DD format. Today is {datetime.datetime.now().strftime('%Y-%m-%d')}."); interaction_time: Optional[str] = Field(None, description="Time in 24-hour HH:mm format."); attendees: Optional[str] = Field(None, description="Other individuals present."); topics_discussed: Optional[str] = Field(None, description="A summary of what was talked about."); materials_shared: Optional[str] = Field(None, description="Specific materials, brochures, or samples given."); observed_sentiment: Optional[str] = Field(None, description="HCP's sentiment. Must be one of: 'Positive', 'Neutral', 'Negative', 'Inquisitive'."); outcomes: Optional[str] = Field(None, description="Key results or agreements from the interaction."); follow_up_actions: Optional[str] = Field(None, description="Explicit next steps for the sales rep.")

# --- The tools are now simple definitions for the AI to understand. The actual logic is in the endpoint. ---
@tool(args_schema=LogInteractionToolArgs)
def log_interaction(**kwargs) -> dict:
    """Use this tool when the user wants to log a new interaction with an HCP. Extract all details from the user's text to call this tool."""
    return kwargs

@tool
def edit_interaction(interaction_id: int, field_to_edit: str, new_value: str) -> str:
    """Use this tool to modify a previously logged interaction. Requires the ID of the interaction."""
    # This tool's logic is now handled in the main endpoint
    return "Attempting to edit interaction..."

@tool
def query_hcp_history(hcp_name: str) -> str:
    """Use this tool to retrieve the interaction history for a specific Healthcare Professional (HCP)."""
    return "Attempting to query history..."

@tool
def suggest_next_best_action(hcp_name: str) -> str:
    """Use this tool when the user asks for a suggestion for an HCP."""
    return "Attempting to generate a suggestion..."

@tool
def fetch_clinical_data(product_name: str) -> str:
    """Use this tool to fetch clinical data for a product."""
    return "Attempting to fetch clinical data..."


# --- 7. MULTI-TOOL AGENT SETUP ---
llm = ChatGroq(model="gemma2-9b-it", temperature=0)
tools = [log_interaction, edit_interaction, query_hcp_history, suggest_next_best_action, fetch_clinical_data]
prompt = ChatPromptTemplate.from_messages([("system", "You are an AI assistant. Your job is to select the correct tool and arguments based on the user's request."), ("user", "{input}"), ("placeholder", "{agent_scratchpad}")])
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, return_intermediate_steps=True)


# --- 8. AGENT ENDPOINT (with final, robust logic) ---
@app.post("/api/agent/invoke", response_model=AgentResponse)
def invoke_agent(message: ChatMessage, db: Session = Depends(get_db)):
    """
    This endpoint now manages the agent and executes tool logic within a single DB session.
    """
    print(f"--- Invoking agent with input: {message.text} ---")
    try:
        result = agent_executor.invoke({"input": message.text})
        
        if 'intermediate_steps' not in result or not result['intermediate_steps']:
            # If the agent responds directly without a tool
            return AgentResponse(response_type='text_message', data=result['output'])

        # --- TOOL EXECUTION LOGIC ---
        # The agent has decided on a tool. We execute the logic here.
        agent_action = result['intermediate_steps'][-1][0]
        tool_name = agent_action.tool
        tool_args = agent_action.tool_input
        
        print(f"--- Agent selected tool: {tool_name} with args: {tool_args} ---")

        if tool_name == 'log_interaction':
            print("Returning 'form_data' response type.")
            return AgentResponse(response_type='form_data', data=tool_args)

        elif tool_name == 'query_hcp_history':
            hcp_name = tool_args.get('hcp_name')
            search_term = f"%{hcp_name.lower()}%"
            interactions = db.query(InteractionDB).filter(func.lower(InteractionDB.hcp_name).like(search_term)).order_by(InteractionDB.id.asc()).all()
            if not interactions:
                return AgentResponse(response_type='text_message', data=f"No interaction history found for an HCP matching '{hcp_name}'.")
            summary = f"Found {len(interactions)} interaction(s) for '{hcp_name}':\n"
            for i, record in enumerate(interactions):
                summary += f"\n{i+1}. ID: {record.id} on {record.interaction_date} - Topics: {record.topics_discussed}"
            return AgentResponse(response_type='text_message', data=summary)

        elif tool_name == 'edit_interaction':
            interaction_id = tool_args.get('interaction_id')
            field_to_edit = tool_args.get('field_to_edit')
            new_value = tool_args.get('new_value')
            interaction = db.query(InteractionDB).filter(InteractionDB.id == interaction_id).first()
            if not interaction:
                return AgentResponse(response_type='text_message', data=f"Error: Interaction with ID {interaction_id} not found.")
            if not hasattr(interaction, field_to_edit):
                return AgentResponse(response_type='text_message', data=f"Error: Invalid field '{field_to_edit}'.")
            setattr(interaction, field_to_edit, new_value)
            db.commit()
            return AgentResponse(response_type='text_message', data=f"Success! Interaction {interaction_id} has been updated.")
        
        # Add placeholders for the other tools
        elif tool_name == 'suggest_next_best_action':
            # You could build out the logic here using the 'db' session
            return AgentResponse(response_type='text_message', data="Suggestion logic is being processed...")

        elif tool_name == 'fetch_clinical_data':
             product_name = tool_args.get('product_name')
             data = MOCK_CLINICAL_DATA.get(product_name.lower(), "No data found.")
             return AgentResponse(response_type='text_message', data=data)

        # Fallback for any other case
        return AgentResponse(response_type='text_message', data=result['output'])

    except Exception as e:
        print(f"Agent execution error: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred in the AI agent: {e}")