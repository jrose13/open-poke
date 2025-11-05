import os
from pathlib import Path

from composio import Composio
from composio_langchain import LangchainProvider
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

composio = Composio(
    api_key=os.getenv("COMPOSIO_API_KEY"),
    provider=LangchainProvider(),
)

openai = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-5",
)
