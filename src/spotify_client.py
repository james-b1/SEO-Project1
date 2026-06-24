import spotipy
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials
import os
import time
from dotenv import load_dotenv

from src.synthetic import (
  synthetic_artist,
  synthetic_collaborators,
  synthetic_top_tracks,
)

load_dotenv()

_client = None

def get_client():
  """Authenticate and return Spotify client"""

  global _client
  if _client is None:
    auth_manager = SpotifyClientCredentials(
      client_id=os.getenv("SPOTIFY_CLIENT_ID"),
      client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    )
    _client = spotipy.Spotify(
      auth_manager=auth_manager,
      requests_timeout=10,
      retries=0,
      status_retries=0,
    )
  return _client


def search_artist(song_name, limit=10):
  """Find the most popular artist who released a track with the same
     title as input song. Returns a single artists, dictionaries, or None."""
  sp = get_client()

  try:
    results = sp.search(q=song_name, type="track", limit=limit)
    tracks = results["tracks"]["items"]

    exact = [t for t in tracks if t["name"].lower() == song_name.lower()]

    if not exact:
      return None
    
    best = max(exact, key=lambda t: t.get("popularity", 0))
    artist_id = best["artists"][0]["id"]
    a = sp.artist(artist_id)

    return {
      "name": a["name"],
      "id": a["id"],
      "popularity": a.get("popularity", 0),
      # Spotify returns [] for dev-mode apps; collaborators no longer rely on it.
      "genres": a.get("genres", []),
    }
  except SpotifyException as err:
    if err.http_status in (403, 429):
      reason = "rate limited" if err.http_status == 429 else "access forbidden"
      print(f"Spotify {reason} for {song_name!r}; generating a synthetic match with Gemini.")
      return synthetic_artist(song_name)
    raise

def get_collaborators(artist, limit=5):
  """Find real collaborators: other artists credited on this artist's tracks.

  Spotify no longer returns genres for dev-mode apps, so we discover related
  artists from actual track credits (features) instead of a genre search.
  Returns up to `limit` collaborators, ranked by how often they appear with
  this artist. We leave popularity at 0 rather than spend an extra API call per
  collaborator to fetch it — the playlist itself is still ranked by real track
  popularity downstream."""
  sp = get_client()

  try:
    # Dev-mode Spotify apps reject search `limit` above ~10 with a 400, so keep
    # it small (matches the other search calls in this module).
    results = sp.search(
      q=f'artist:{artist["name"]}',
      type="track",
      limit=10,
    )
  except SpotifyException as err:
    if err.http_status in (403, 429):
      print(f"Spotify unavailable for collaborators of {artist.get('name')!r}; "
            f"generating synthetic ones with Gemini.")
      return synthetic_collaborators(artist, limit)
    raise

  counts = {}
  names = {}
  for track in results.get("tracks", {}).get("items", []):
    for credited in track.get("artists", []):
      cid = credited.get("id")
      if not cid or cid == artist["id"]:
        continue
      counts[cid] = counts.get(cid, 0) + 1
      names[cid] = credited.get("name")

  ranked = sorted(counts, key=lambda cid: counts[cid], reverse=True)[:limit]
  return [
    {"name": names[cid], "id": cid, "popularity": 0, "genres": []}
    for cid in ranked
  ]


def same_genre(artist_a, artist_b):
  """True if the two artists share at least one genre."""
  return bool(set(artist_a.get("genres", [])) & set(artist_b.get("genres", [])))


def filter_by_genre(input_artist, collaborators):
  """Keep only collaborators who share a genre with the input artist."""
  return [c for c in collaborators if same_genre(input_artist, c)]


def collect_related_artists(artist):
  """Return same genre collaborators for an input artist"""
  collaborators = get_collaborators(artist)
  return filter_by_genre(artist, collaborators)
  

def get_top_tracks(artist, country="US", limit=10):
  """An artist's most popular tracks as dictionaries"""
  sp = get_client()

  try:
    results = sp.search(
      q=f'artist:{artist["name"]}',
      type="track",
      market=country,
      limit=limit
    )
  except SpotifyException as err:
    if err.http_status in (403, 429):
      print(f"Spotify unavailable for top tracks of {artist['name']!r}; "
            f"generating synthetic ones with Gemini.")
      return synthetic_top_tracks(artist, limit)
    raise

  spotify_tracks = results.get("tracks", {}).get("items", {})
  tracks = []

  for track in spotify_tracks[:limit]:
    album = track.get("album", {})
    tracks.append({
      "title": track["name"],
      "track_id": track["id"],
      "popularity": track.get("popularity", 0),
      "artist_name": artist["name"],
      "album_id": album.get("id"),
      "album_name": album.get("name"),
    })
  
  return tracks


def rank_top_tracks(artists, limit=10):
  """Pool every artist's top tracks, dedupe by track, and rank by
    popularity."""
  pool = {}
  for artist in artists:
    for track in get_top_tracks(artist):
      pool[track["track_id"]] = track # dedupe
    
  ranked = sorted(pool.values(), key=lambda t: t["popularity"], reverse=True)
  return ranked[:limit]
  