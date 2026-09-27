"""Shared Gemini client. Every agent imports `client` and `MODEL` from here."""
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing. Copy .env.example to .env and paste your key from Google AI Studio.")

# Model names change over time — check Google AI Studio for the current free-tier Flash model
# and set GEMINI_MODEL in your .env if the default stops working.
MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

client = genai.Client(api_key=API_KEY)
