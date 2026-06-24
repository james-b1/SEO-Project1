"""Gemini-generated stand-ins for Spotify data (403/429)
"""
import json
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = "gemini-2.5-flash"

_client = None


def _get_client():
  """build the Gemini client ."""
  global _client
  if _client is None:
    _client = genai.Client(
      api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    )
  return _client


def _generate_json(prompt):
  """Ask Gemini for a JSON object. Returns the parsed value, or None on failure."""
  try:
    response = _get_client().models.generate_content(
      model=MODEL,
      contents=prompt,
      config=types.GenerateContentConfig(
        response_mime_type="application/json",
        max_output_tokens=1024,
      ),
    )
    text = (response.text or "").strip()
    return json.loads(text) if text else None
  except Exception as err:  # network error, bad JSON, etc. — degrade gracefully
    print(f"  (synthetic generation failed: {err})")
    return None


def _slug(text):
  s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
  return s or "unknown"


def _clamp_pop(value):
  try:
    return max(0, min(100, int(value)))
  except (TypeError, ValueError):
    return 50


def _clean_genres(genres):
  if not isinstance(genres, list):
    return []
  return [str(g).lower() for g in genres if g][:3]


def _artist_dict(name, genres, popularity):
  return {
    "name": name,
    "id": f"synthetic:artist:{_slug(name)}",
    "popularity": _clamp_pop(popularity),
    "genres": _clean_genres(genres),
    "synthetic": True,
  }


def synthetic_artist(song_name):
  """Invent one plausible artist for a song title. Returns a dict or None."""
  prompt = (
    "A music recommendation app could not reach Spotify. Invent ONE plausible, "
    f"real-sounding music artist who could have recorded a song titled {song_name!r}. "
    "Return a JSON object with keys: "
    'name (string), genres (array of 1-3 lowercase genre strings), '
    "popularity (integer 0-100)."
  )
  data = _generate_json(prompt)
  if not isinstance(data, dict):
    return None
  name = data.get("name") or song_name
  return _artist_dict(name, data.get("genres"), data.get("popularity"))


def synthetic_collaborators(artist, limit=5):
  """Invent same-genre collaborators for an artist. Returns a list (possibly empty)."""
  name = artist.get("name", "this artist")
  genres = ", ".join(artist.get("genres", [])) or "various genres"
  prompt = (
    "A music recommendation app could not reach Spotify. Invent "
    f"{limit} plausible, real-sounding music artists similar to {name!r} in these "
    f"genres: {genres}. Return a JSON object: "
    '{"artists": [{"name": string, "genres": [string], "popularity": integer 0-100}]}.'
  )
  data = _generate_json(prompt)
  items = data.get("artists", []) if isinstance(data, dict) else []

  collaborators = []
  for item in items[:limit]:
    if not isinstance(item, dict) or not item.get("name"):
      continue
    collaborators.append(
      _artist_dict(item["name"], item.get("genres"), item.get("popularity"))
    )
  return collaborators


def synthetic_top_tracks(artist, limit=10):
  """Invent an artist's top tracks. Returns a list (possibly empty)."""
  name = artist.get("name", "this artist")
  prompt = (
    "A music recommendation app could not reach Spotify. Invent "
    f"{limit} plausible song titles by the artist {name!r}, grouped across a few "
    "albums. Return a JSON object: "
    '{"tracks": [{"title": string, "album_name": string, "popularity": integer 0-100}]}.'
  )
  data = _generate_json(prompt)
  items = data.get("tracks", []) if isinstance(data, dict) else []

  tracks = []
  for item in items[:limit]:
    if not isinstance(item, dict) or not item.get("title"):
      continue
    title = item["title"]
    album_name = item.get("album_name") or f"{name} Singles"
    tracks.append({
      "title": title,
      "track_id": f"synthetic:track:{_slug(name)}:{_slug(title)}",
      "popularity": _clamp_pop(item.get("popularity")),
      "artist_name": name,
      # same album name -> same album_id, so swap_songs album-grouping still works
      "album_id": f"synthetic:album:{_slug(name)}:{_slug(album_name)}",
      "album_name": album_name,
      "synthetic": True,
    })
  return tracks
