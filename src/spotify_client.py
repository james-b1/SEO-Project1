import spotipy from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials
import os
import time
from dotenv import load_dotenv

load_dotenv()

def get_client():
  """Authenticate and return Spotify client"""

  auth_manager = SpotifyClientCredentials(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
  )
  return spotipy.Spotify(
    auth_manager=auth_manager,
    requests_timeout=10,
    retries=0,
    status_retries=0,
  )


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
    
    artist_ids = []
    for t in exact:
      primary_id = t["artists"][0]["id"]
      if primary_id not in artist_ids:
        artist_ids.append(primary_id)

    # full_artists = sp.artists(artist_ids)["artists"]
    full_artists = [sp.artist(aid) for aid in artist_ids]
    full_artists.sort(key=lambda a: a.get("popularity", 0), reverse=True)

    a = full_artists[0]

    return {
      "name": a["name"],
      "id": a["id"],
      "popularity": a.get("popularity", 0),
      "genres": a.get("genres", [])
    }
  except SpotifyException as err:
    if err.http_status == 429:
      print("Spotify rate limit reached. Try again later.")
      return None
    raise

def get_collaborators(artist, limit=5):
  """Returns a list of full collaborator artist objects"""
  sp = get_client()
  genres = artist.get("genres", [])

  if not genres:
    return []
  
  genre = genres[0]
  results = sp.search(
    q=f'genre:{genre}',
    type="artist",
    limit=limit
  )

  collaborators = []
  for item in results.get("artists", {}).get("items", []):
    if item["id"] == artist["id"]:
      continue

    collaborators.append({
      "name": item["name"],
      "id": item["id"],
      "popularity": item.get("popularity", 0),
      "genres": item.get("genres", [])
    })
    
  return collaborators


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

  results = sp.search(
    q=f'artist:{artist["name"]}',
    type="track",
    market=country,
    limit=limit
  )
  
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
  