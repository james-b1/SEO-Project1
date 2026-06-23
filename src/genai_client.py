import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(apikeys=os.getenv("GEMINIT_API_KEY"))

SYSTEM_PROMPT = (
    "You write very short music recommendations. One or two sentences, "
    "direct and concrete, and no marketing fluff. Address the "
    "listener as 'you', and don't repeat the artist's name more than once."
)

def pitch_artist(artist, connected_to):
  """Return a one or two sentence reason a listener might like this artist
     based on 'connected_to', whcih is a list of the user's input artists."""
  genres = ", ".join(artist["genres"]) or "unlisted"
  seeds = ", ".join(connected_to) or "artists you already like"

  user_message = (
    f"Artist: {artist['name']}\n"
    f"Genres: {genres}\n"
    f"They have collaborated with and share a genre with: {seeds}.\n"
    f"Explain why the listener might enjoy them."
  )

  response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=user_message,
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        max_output_tokens=120,
    ),
  )
  return response.text.strip()