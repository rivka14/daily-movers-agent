from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_core.tools import tool

search = GoogleSerperAPIWrapper()


@tool
def search_stock_news(query: str) -> str:
    """Search for recent news about a stock."""
    return search.run(query)
