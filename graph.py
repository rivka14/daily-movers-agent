from langgraph.graph import END, START, StateGraph

from agents import analyst_node, research_node, strategist_node, supervisor_node
from output import generate_email_node, generate_report_node
from state import AgentState


def should_continue(state: AgentState) -> str:
    """Route back to research if more stocks remain, otherwise to report."""
    if state["current_index"] < len(state["stocks"]):
        return "research"
    return "report"


builder = StateGraph(AgentState)

builder.add_node("research", research_node)
builder.add_node("analyst", analyst_node)
builder.add_node("strategist", strategist_node)
builder.add_node("supervisor", supervisor_node)
builder.add_node("report", generate_report_node)
builder.add_node("email", generate_email_node)

builder.add_edge(START, "research")
builder.add_edge("research", "analyst")
builder.add_edge("analyst", "strategist")
builder.add_edge("strategist", "supervisor")

builder.add_conditional_edges(
    "supervisor",
    should_continue,
    {"research": "research", "report": "report"},
)

builder.add_edge("report", "email")
builder.add_edge("email", END)

graph = builder.compile()
