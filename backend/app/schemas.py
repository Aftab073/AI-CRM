import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict

# --- Interaction Schemas ---
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

# --- Agent Schemas ---
class AgentContext(BaseModel):
    current_interaction_id: Optional[int] = None

class AgentInvokeRequest(BaseModel):
    text: str
    context: Optional[AgentContext] = None

class AgentResponse(BaseModel):
    response_type: str
    data: Any

# --- Tool Argument Schemas ---
class LogInteractionToolArgs(BaseModel):
    hcp_name: str = Field(description="Full name of the Healthcare Professional.")
    interaction_type: Optional[str] = Field(None, description="Must be one of: 'Scheduled Visit', 'Unscheduled Visit', 'Phone Call', 'Email', 'Conference'.")
    interaction_date: Optional[str] = Field(None, description=f"Date in YYYY-MM-DD format. Today is {datetime.datetime.now().strftime('%Y-%m-%d')}.")
    interaction_time: Optional[str] = Field(None, description="Time in 24-hour HH:mm format.")
    attendees: Optional[str] = Field(None, description="Other individuals present.")
    topics_discussed: Optional[str] = Field(None, description="A summary of what was talked about.")
    materials_shared: Optional[str] = Field(None, description="Specific materials, brochures, or samples given.")
    observed_sentiment: Optional[str] = Field(None, description="HCP's sentiment. Must be one of: 'Positive', 'Neutral', 'Negative', 'Inquisitive'.")
    outcomes: Optional[str] = Field(None, description="Key results or agreements from the interaction.")
    follow_up_actions: Optional[str] = Field(None, description="Explicit next steps for the sales rep.")

class EditInteractionToolArgs(BaseModel):
    interaction_id: int = Field(description="The ID of the interaction to be modified.")
    updates: Dict[str, Any] = Field(description="A dictionary of fields to update, where keys are the field names and values are the new values.")
