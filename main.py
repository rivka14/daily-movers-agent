from langgraph.graph import END, START, StateGraph

from agents import analyst_node, research_node, strategist_node, supervisor_node
from output import generate_email_node, generate_report_node
from scraper import scraper_node
from state import Input, Output, State


def should_continue(state: State) -> str:
    if state.current_index < len(state.stocks):
        return "research"
    return "report"


async def output_node(state: State) -> Output:
    return Output(
        excel_path=state.excel_path,
        email_summary=state.email_summary,
        recommendations=state.recommendations,
    )


builder = StateGraph(State, input=Input, output=Output)

builder.add_node("scraper", scraper_node)
builder.add_node("research", research_node)
builder.add_node("analyst", analyst_node)
builder.add_node("strategist", strategist_node)
builder.add_node("supervisor", supervisor_node)
builder.add_node("report", generate_report_node)
builder.add_node("email", generate_email_node)
builder.add_node("output", output_node)

builder.add_edge(START, "scraper")
builder.add_conditional_edges(
    "scraper",
    should_continue,
    {"research": "research", "report": "report"},
)
builder.add_edge("research", "analyst")
builder.add_edge("analyst", "strategist")
builder.add_edge("strategist", "supervisor")
builder.add_conditional_edges(
    "supervisor",
    should_continue,
    {"research": "research", "report": "report"},
)
builder.add_edge("report", "email")
builder.add_edge("email", "output")
builder.add_edge("output", END)

graph = builder.compile()
