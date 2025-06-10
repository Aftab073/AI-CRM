import os
import datetime
# FIX: Added 'Field' to the Pydantic import
from pydantic import BaseModel, Field
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware


# Database Imports
from sqlalchemy import create_engine, Column, Integer, String, Date, Time, Text, TIMESTAMP
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# AI Agent Imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from typing import TypedDict
from langgraph.graph import StateGraph, END

# Environment and Config
from dotenv import load_dotenv
load_dotenv()

# --- 1. DATABASE SETUP ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found in .env file")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 2.SQLALCHEMY ORM MODEL ---
class InteractionDB(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    hcp_name = Column(String, index=True, nullable=False)
    interaction_type = Column(String)
    interaction_date = Column(Date)
    interaction_time = Column(Time)
    attendees = Column(Text)
    topics_discussed = Column(Text)
    materials_shared = Column(Text)
    observed_sentiment = Column(String)
    outcomes = Column(Text)
    follow_up_actions = Column(Text)

# --- 3. PYDANTIC SCHEMAS ---
class InteractionBase(BaseModel):
    hcp_name: str
    interaction_type: Optional[str] = None
    interaction_date: Optional[datetime.date] = None
    interaction_time: Optional[datetime.time] = None
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[str] = None
    observed_sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None

class InteractionCreate(InteractionBase):
    pass

class InteractionRead(InteractionBase):
    id: int
    created_at: datetime.datetime
    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    text: str

# --- 4. FastAPI APP ---
app = FastAPI(title="AI-First CRM API")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 5. DATABASE DEPENDENCY & CRUD ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_interaction_in_db(db: Session, interaction: InteractionCreate):
    db_interaction = InteractionDB(**interaction.model_dump())
    db.add(db_interaction)
    db.commit()
    db.refresh(db_interaction)
    return db_interaction

# --- 6. API ENDPOINTS ---
@app.get("/api/interactions", response_model=List[InteractionRead], summary="Get All Interactions")
def get_all_interactions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    interactions = db.query(InteractionDB).order_by(InteractionDB.id.desc()).offset(skip).limit(limit).all()
    return interactions

@app.post("/api/interactions", response_model=InteractionRead, summary="Save a New Interaction")
def save_interaction(interaction: InteractionCreate, db: Session = Depends(get_db)):
    return create_interaction_in_db(db=db, interaction=interaction)

# --- 7. AI AGENT ---
class AIParsedInteraction(BaseModel):
    hcp_name: str = Field(description="Full name of the Healthcare Professional.")
    interaction_type: Optional[str] = Field(description="The type of interaction. Must be one of: 'Scheduled Visit', 'Unscheduled Visit', 'Phone Call', 'Email', 'Conference'.")
    interaction_date: Optional[str] = Field(description="Date in YYYY-MM-DD format.")
    interaction_time: Optional[str] = Field(description="Time in 24-hour HH:mm format. Must be null if not mentioned.")
    attendees: Optional[str] = Field(description="Other individuals present. Must be null if not mentioned.")
    topics_discussed: Optional[str] = Field(description="Summary of what was talked about.")
    materials_shared: Optional[str] = Field(description="Specific materials, brochures, or samples that were given. Must be null if not mentioned.")
    observed_sentiment: Optional[str] = Field(description="HCP's sentiment. Must be one of: 'Positive', 'Neutral', 'Negative', 'Inquisitive'.")
    outcomes: Optional[str] = Field(description="Key results or agreements reached.")
    follow_up_actions: Optional[str] = Field(description="Explicit next steps for the sales rep.")

structured_llm = ChatGroq(model="gemma2-9b-it", temperature=0).with_structured_output(AIParsedInteraction)

def get_agent_graph():
    class AgentState(TypedDict):
        raw_text: str
        extracted_data: Optional[AIParsedInteraction]

    def extract_details(state: AgentState):
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are a hyper-attentive data extraction robot. Your only purpose is to convert user text into a JSON object matching the `AIParsedInteraction` schema. You will follow these steps and rules without deviation.

Step 1: Analyze the user's text for key information corresponding to each field in the schema.
Step 2: For classification fields, you MUST choose from the provided list or set to null.
- For `interaction_type`, you MUST select one of: 'Scheduled Visit', 'Unscheduled Visit', 'Phone Call', 'Email', 'Conference'. If no keyword like 'met', 'call', 'email' is present, default to 'Unscheduled Visit'.
- For `observed_sentiment`, you MUST select one of: 'Positive', 'Neutral', 'Negative', 'Inquisitive'.

Step 3: For text fields, extract the relevant information. If no information is found for a field, its value MUST be `null`.
- For `materials_shared`, look for keywords like 'samples', 'brochures', 'data', 'packet', 'guide'. If none are present, it MUST be `null`.

Step 4: Format date and time precisely.
- Today's date is {datetime.datetime.now().strftime('%Y-%m-%d')}. Use it to resolve relative dates.
- `interaction_time` MUST be in 24-hour HH:mm format (e.g., '3:00 PM' becomes '15:00'). If no time is mentioned, it MUST be `null`.

Step 5: Construct the final JSON object. Every field from the schema must be present, with a value or `null`.
"""),
            ("human", "{text_input}")
        ])
        chain = prompt | structured_llm
        try:
            extracted_data = chain.invoke({"text_input": state['raw_text']})
            return {"extracted_data": extracted_data}
        except Exception as e:
            print(f"AI extraction failed: {e}")
            return {"extracted_data": None}

    workflow = StateGraph(AgentState)
    workflow.add_node("extractor", extract_details)
    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", END)
    return workflow.compile()

agent_graph = get_agent_graph()

@app.post("/api/ai_extract", response_model=AIParsedInteraction, summary="Extract Interaction Details via AI")
def ai_extract_interaction(message: ChatMessage):
    print(f"Received text for AI extraction: {message.text}")
    result = agent_graph.invoke({"raw_text": message.text})
    ai_data = result.get('extracted_data')
    if not ai_data:
        raise HTTPException(status_code=400, detail="AI could not extract details.")
    print("Returning extracted data to frontend for review.")
    return ai_data