import os
from pathlib import Path

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv(Path(__file__).resolve().parents[1] / '.env')  # Load .env file

client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
def search_web(query: str, max_results: int = 3):
    return client.search(query=query, max_results=max_results)