from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

# Import from our new modules
from . import models, schemas, agent
from .database import engine, get_db

# --- THIS IS THE FIX ---
# Correctly import CORSMiddleware from fastapi.middleware
from fastapi.middleware.cors import CORSMiddleware

# Create all database tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-First CRM API")

# Add CORS middleware to allow the frontend to connect
app.add_middleware(
    CORSMiddleware, # Use the correctly imported class
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Standard CRUD Endpoints ---
@app.post("/api/interactions", response_model=schemas.InteractionRead, summary="Save a New Interaction")
def save_interaction(interaction: schemas.InteractionCreate, db: Session = Depends(get_db)):
    db_interaction = models.Interaction(**interaction.model_dump())
    db.add(db_interaction)
    db.commit()
    db.refresh(db_interaction)
    return db_interaction

@app.get("/api/interactions", response_model=List[schemas.InteractionRead], summary="Get All Interactions")
def get_all_interactions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Interaction).order_by(models.Interaction.id.desc()).offset(skip).limit(limit).all()


# --- Main AI Agent Endpoint ---
agent_graph = agent.create_agent_graph()

@app.post("/api/agent/invoke", response_model=schemas.AgentResponse)
def invoke_agent(request: schemas.AgentInvokeRequest, db: Session = Depends(get_db)):
    context_info = ""
    if request.context and request.context.current_interaction_id:
        context_info = f"[System Context: The user is currently viewing interaction with ID {request.context.current_interaction_id}. If they say 'this interaction', use this ID.]\n\n"
    
    initial_state = {"user_input": request.text, "context_info": context_info}
    final_state = agent_graph.invoke(initial_state)

    if final_state.get('final_response'):
        return schemas.AgentResponse(response_type='text_message', data=final_state['final_response'])
    
    if not final_state.get('tool_calls'):
        return schemas.AgentResponse(response_type='text_message', data="I'm not sure how to handle that.")

    tool_call = final_state['tool_calls'][0]
    tool_name = tool_call['name']
    tool_args = tool_call['args']
    print(f"--- Executing logic for tool: {tool_name} ---")

    try:
        if tool_name == 'log_interaction':
            return schemas.AgentResponse(response_type='form_data', data=tool_args)

        elif tool_name == 'query_hcp_history':
            hcp_name = tool_args.get('hcp_name')
            interaction = db.query(models.Interaction).filter(models.Interaction.hcp_name.ilike(f"%{hcp_name}%")).order_by(models.Interaction.id.desc()).first()
            if not interaction:
                return schemas.AgentResponse(response_type='text_message', data=f"No history found for '{hcp_name}'.")
            return schemas.AgentResponse(response_type='form_data', data=schemas.InteractionRead.from_orm(interaction).model_dump())
        
        elif tool_name == 'edit_interaction':
            interaction_id = tool_args.get('interaction_id')
            updates = tool_args.get('updates', {})
            interaction = db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
            if not interaction:
                return schemas.AgentResponse(response_type='text_message', data=f"Error: Interaction {interaction_id} not found.")
            for field, value in updates.items():
                if hasattr(interaction, field):
                    setattr(interaction, field, value)
            db.commit(); db.refresh(interaction)
            return schemas.AgentResponse(response_type='form_data', data=schemas.InteractionRead.from_orm(interaction).model_dump())
        
        elif tool_name == 'suggest_next_best_action':
            hcp_name = tool_args.get('hcp_name')
            interactions = db.query(models.Interaction).filter(models.Interaction.hcp_name.ilike(f"%{hcp_name}%")).order_by(models.Interaction.id.desc()).all()
            if not interactions:
                return schemas.AgentResponse(response_type='text_message', data=f"No history for {hcp_name}. Suggestion: Schedule intro meeting.")
            latest = interactions[0]
            if latest.follow_up_actions:
                return schemas.AgentResponse(response_type='text_message', data=f"Last to-do was: '{latest.follow_up_actions}'. Suggestion: Complete this.")
            if latest.observed_sentiment == 'Negative':
                return schemas.AgentResponse(response_type='text_message', data="Last sentiment was Negative. Suggestion: Schedule call to address concerns.")
            return schemas.AgentResponse(response_type='text_message', data=f"Last interaction with {hcp_name} was on {latest.interaction_date}. Suggestion: Plan a check-in.")

        elif tool_name == 'fetch_clinical_data':
             product_name = tool_args.get('product_name')
             data = agent.MOCK_CLINICAL_DATA.get(product_name.lower(), "No data found for that product.")
             return schemas.AgentResponse(response_type='text_message', data=data)
        
        else: # Handle direct responses from the planner
            return schemas.AgentResponse(response_type='text_message', data="I'm not sure how to respond to that.")

    except Exception as e:
        print(f"Tool execution error: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while executing the tool.")
