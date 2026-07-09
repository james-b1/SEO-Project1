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

_client = None


def _get_client():
  """Build the Gemini client lazily. Constructing it eagerly at import time
  raises ValueError when no key is set — which would crash the whole app on
  startup. Deferring lets `_try_gemini` catch the failure and fall back."""
  global _client
  if _client is None:
    _client = genai.Client(
      api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )
  return _client

SYSTEM_PROMPT = (
  "Write one short sentence explaining why user, address as 'you' might like the artist."
  "Maximum 18 words. Be direct. No marketing fluff."
)

def explain_artist(artist, connected_to):
  """Return a one or two sentence reason a listener might like this artist."""
  user_message = _build_prompt(artist, connected_to)
  text = _try_gemini(user_message)

  if not text or not _is_valid(text):
    text = _try_openrouter(user_message)

  if not text or not _is_valid(text):
    return _fallback_explanation(artist, connected_to)

  return text

def _try_gemini(user_message):
  """Call Gemini, returns _try_gemini(user_message)"""
  try:
    response = _get_client().models.generate_content(
    model=GEMINI_MODEL,
    contents=user_message,
    config=types.GenerateContentConfig(
      system_instruction=SYSTEM_PROMPT,
      # gemini-2.5-flash is a *thinking* model: without disabling it the token
      # budget is spent on hidden reasoning and response.text comes back empty.
      thinking_config=types.ThinkingConfig(thinking_budget=0),
      max_output_tokens=80,
      temperature=0.4,
      ),
    )
    text = (response.text or "").strip()

    if not text: # prompt was blocked or empty response
      return "" # fail silently

    return text
  except Exception as err:
    # Any provider error (quota, bad request, network) should degrade to the
    # next provider / local fallback — never break the whole recommendation build.
    print(f"  → Gemini request failed: {err}")
    return ""

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


def _is_valid(text):
  return bool(text) and len(text.split()) >= 8 and text[-1] in ".!"


def _fallback_explanation(artist, connected_to):
  seeds = ", ".join(connected_to[:2]) if connected_to else "artists you already like"
  name = artist.get("name", "This artist")
  return (
    f"{name} shares with {seeds} while bringing their own distinct style."
  )