import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
MODEL = "claude-sonnet-4-6"
PORT = int(os.environ.get("PORT", 5000))
RAG_ENABLED = os.environ.get("RAG_ENABLED", "1") != "0"
