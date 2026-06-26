"""Offline demo of the synthetic (Gemini) fallback.

Both Spotify and Gemini are easy to throttle, which makes the fallback hard to
watch live. This script forces the Spotify 403/429 path and feeds the synthetic
generators *canned* JSON (instead of calling Gemini), so the whole main() flow
runs deterministically with zero network calls. The real fallback logic — id
synthesis, the `synthetic:` tagging, album grouping, playlist building — all
runs unchanged; only the two network calls (Spotify search, Gemini generate)
are stubbed.

    python demo_synthetic.py

Nothing here touches your real recommender.db or your API keys.
"""
import os

from spotipy.exceptions import SpotifyException

import main
import src.database as database
import src.spotify_client as spotify_client
import src.synthetic as synthetic


# 1) Force Spotify to always throttle, so every call takes the fallback path.
class _Throttled:
  def search(self, **kwargs):
    raise SpotifyException(429, -1, "throttled (demo)")

  def artist(self, artist_id):
    raise SpotifyException(429, -1, "throttled (demo)")


spotify_client.get_client = lambda: _Throttled()


# 2) Stub Gemini: return canned JSON instead of calling the API. The real
#    synthetic_* functions still run (building ids, tags, album grouping).
_seed_artists = iter([
  {"name": "Neon Verge", "genres": ["synth-pop"], "popularity": 72},
  {"name": "Midnight Atlas", "genres": ["indie pop"], "popularity": 65},
  {"name": "The Gold Hour", "genres": ["pop rock"], "popularity": 58},
])


def _fake_generate(prompt):
  if "Invent ONE" in prompt:
    return next(_seed_artists, {"name": "Encore", "genres": ["pop"], "popularity": 50})
  if "similar to" in prompt:
    return {"artists": [
      {"name": "Echo Tide", "genres": ["synth-pop"], "popularity": 68},
      {"name": "Paper Lanterns", "genres": ["indie pop"], "popularity": 61},
      {"name": "Velvet Signal", "genres": ["pop rock"], "popularity": 55},
    ]}
  if "song titles by the artist" in prompt:
    return {"tracks": [
      {"title": "Afterglow", "album_name": "Halcyon", "popularity": 80},
      {"title": "Paper Moon", "album_name": "Halcyon", "popularity": 74},
      {"title": "Citylight", "album_name": "Halcyon", "popularity": 69},
      {"title": "Undertow", "album_name": "Drift", "popularity": 66},
      {"title": "Slow Burn", "album_name": "Drift", "popularity": 61},
      {"title": "Northbound", "album_name": "Drift", "popularity": 58},
    ]}
  return None


synthetic._generate_json = _fake_generate


# 3) Skip the live Gemini blurb call and the interactive prompts.
main.explain_artist = lambda artist, connected_to: ("A canned blurb (live Gemini skipped in the demo).", "stub")
main.get_songs = lambda: ["Views 500", "Goodbyes 400", "Congratulations 300"]
main.get_playlist_size = lambda: 8
main.swap_songs = lambda playlist, candidates: playlist  # skip interactive removal


# 4) Use a throwaway database so the demo never touches recommender.db.
database.DB_PATH = "demo_recommender.db"

try:
  main.main()
finally:
  if os.path.exists("demo_recommender.db"):
    os.remove("demo_recommender.db")
