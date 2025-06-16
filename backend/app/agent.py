from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, List
from .schemas import LogInteractionToolArgs, EditInteractionToolArgs

# --- 1. MOCK DATA ---
MOCK_CLINICAL_DATA = {
    "valcor": "Valcor (VAL-123) Phase 3 trials showed a 45% reduction in primary endpoints vs. placebo...", 
    "aether-d": "Aether-D is a combination therapy approved for type-2 diabetes...", 
    "solara": "Solara is an immunomodulator currently in Phase 2 for treating rheumatoid arthritis...",
    "paracetamol": "Paracetamol is a widely used analgesic and antipyretic that provides effective relief from mild to moderate pain and fever. It is available over the counter and recommended by WHO as an essential medicine.",
    "dolo-650": "Dolo 650 is a high-strength formulation of paracetamol (650 mg) used for managing fever and body aches. Clinically trusted in India, it is frequently prescribed during viral infections and post-vaccination symptoms."

}

# --- 2. TOOL DEFINITIONS ---
# These tools only define the interface for the agent. The real logic is executed in main.py.
@tool(args_schema=LogInteractionToolArgs)
def log_interaction(**kwargs) -> dict:
    """Use this tool to log a new interaction note about a meeting, call, or visit with an HCP."""
    return kwargs

@tool(args_schema=EditInteractionToolArgs)
def edit_interaction(interaction_id: int, updates: dict) -> dict:
    """Use this tool to modify or update one or more fields of a previously logged interaction, referenced by its ID."""
    return {"status": "Editing interaction", "id": interaction_id, "updates": updates}

@tool
def query_hcp_history(hcp_name: str) -> dict:
    """Use this tool to retrieve the most recent interaction history for a specific HCP by their name."""
    return {"status": "Querying history", "name": hcp_name}

@tool
def suggest_next_best_action(hcp_name: str) -> str:
    """Use this tool ONLY when the user explicitly asks for a 'suggestion', 'what to do next', or 'next best action' for a specific HCP."""
    return "Generating suggestion..."

@tool
def fetch_clinical_data(product_name: str) -> str:
    """Use this tool ONLY when the user explicitly asks for 'clinical data', 'trial results', or 'information' on a specific product name like 'Valcor' or 'Solara'."""
    return "Fetching clinical data..."


# --- 3. AGENT & GRAPH SETUP ---
def create_agent_graph():
    """Factory function to create the LangGraph agent."""
    llm = ChatGroq(model="gemma2-9b-it", temperature=0)
    tools = [log_interaction, edit_interaction, query_hcp_history, suggest_next_best_action, fetch_clinical_data]
    llm_with_tools = llm.bind_tools(tools)

    class AgentState(TypedDict):
        user_input: str
        context_info: str
        tool_calls: Optional[List[dict]]
    
    def planner_node(state: AgentState):
        """The 'Planner' node. It calls the LLM to decide which tool to use."""
        print("--- Planner Node ---")
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant... (full prompt here)"""), # Using abbreviated prompt for clarity
            ("user", "{input}"),
        ])
        chain = prompt | llm_with_tools
        
        final_input_for_agent = state['context_info'] + state['user_input']
        result = chain.invoke({"input": final_input_for_agent})
        
        if hasattr(result, 'tool_calls') and result.tool_calls:
            print(f"--- Planner decided to call tools: {[tc['name'] for tc in result.tool_calls]} ---")
            return {"tool_calls": result.tool_calls}
        else:
            # This case is now handled in main.py
            return {"tool_calls": [{"name": "direct_response", "args": {"content": result.content}}]}

    workflow = StateGraph(AgentState)
    workflow.add_node("planner", planner_node)
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", END)
    
    return workflow.compile()
