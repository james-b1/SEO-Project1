# src/genai_client.py
import os
import json
import urllib.error
import urllib.request
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
GEMINI_MODEL = "gemini-2.5-flash"
OPENROUTER_MODEL = "meta-llama/llama-3.2-3b-instruct:free"

client = genai.Client(
  api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
)

SYSTEM_PROMPT = (
  "Write one short sentence explaining why user, address as 'you' might like the artist."
  "Maximum 18 words. Be direct. No marketing fluff."
)

def explain_artist(artist, connected_to):
  """Return (explanation, source) for an artist.

  source is which tier produced the text: 'gemini', 'openrouter', or
  'fallback' (the hard-coded sentence). Lets callers show where each
  explanation came from."""
  user_message = _build_prompt(artist, connected_to)

  text = _try_gemini(user_message)
  if text and _is_valid(text):
    return text, "gemini"

  text = _try_openrouter(user_message)
  if text and _is_valid(text):
    return text, "openrouter"

  return _fallback_explanation(artist, connected_to), "fallback"

def _try_gemini(user_message):
  """Call Gemini, returns _try_gemini(user_message)"""
  try:
    response = client.models.generate_content(
    model=GEMINI_MODEL,
    contents=user_message,
    config=types.GenerateContentConfig(
      system_instruction=SYSTEM_PROMPT,
      # gemini-2.5-flash thinks by default and would spend this whole budget on
      # hidden reasoning, returning empty visible text. Disable thinking and
      # give the answer real room so it isn't starved.
      max_output_tokens=100,
      temperature=0.4,
      thinking_config=types.ThinkingConfig(thinking_budget=0),
      ),
    )
    text = (response.text or "").strip()

    if not text: # prompt was blocked or empty response
      return "" # fail silently

    return text
  except Exception as err:
    if _is_quota_or_availability_error(err):
      return ""
    raise

def _try_openrouter(user_message):
  api_key = os.getenv("OPENROUTER_API_KEY")
  
  if not api_key:
    return ""
  
  body = json.dumps({
    "model": OPENROUTER_MODEL,
    "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_message},
    ],
    "max_tokens": 35,
      "temperature": 0.4,
  }).encode("utf-8")

  req = urllib.request.Request(
    "https://openrouter.ai/api/v1/chat/completions",
    data=body,
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Title": "PyTunes",
    },
      method="POST",
  )

  try:
    with urllib.request.urlopen(req, timeout=20) as resp:
      data = json.loads(resp.read().decode("utf-8"))
  except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
    print(f"  → OpenRouter request failed: {err}")
    return ""

  choices = data.get("choices", [])
  if not choices:
    return ""

  message = choices[0].get("message", {})
  return (message.get("content") or "").strip()


def _build_prompt(artist, connected_to):
  genres = ", ".join(artist.get("genres", [])) or "unlisted"
  seeds = ", ".join(connected_to) or "artists you already like"
  return(
    f"Artist: {artist['name']}\n"
    f"Genres:{genres}\n"
    f"Connected to: {seeds}\n"
    f"Explain why the listener might enjoy them."
  )


def _is_quota_or_availability_error(err):
  text = str(err).lower()
  return any(m in text for m in ("429", "503", "quota", "resource_exhausted", "unavailable"))


def _is_valid(text):
  return bool(text) and len(text.split()) >= 8 and text[-1] in ".!"


def _fallback_explanation(artist, connected_to):
  seeds = ", ".join(connected_to[:2]) if connected_to else "artists you already like"
  name = artist.get("name", "This artist")
  return (
    f"{name} shares with {seeds} while bringing their own distinct style."
  )