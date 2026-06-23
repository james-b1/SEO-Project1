import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
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


sp = get_client()


def search_artist(song_name, limit=10):
  """Find the most popular artist who released a track with the same
     title as input song. Returns a single artists, dictionaries, or None."""
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

  full_artists = sp.artists(artist_ids)["artists"]
  full_artists.sort(key=lambda a: a.get("popularity", 0), reverse=True)

  a = full_artists[0]

  return {
    "name": a["name"],
    "id": a["id"],
    "popularity": a.get("popularity", 0),
    "genres": a.get("genres", [])
  }
  

def get_collaborators(artist):
  """Returns a list of full collaborator artist objects"""
  artist_id = artist["id"]

  albums = []
  results = sp.artist_albums(artist_id, album_type="album,single", limit=10)
  albums.extend(results["items"])
  while results["next"]:
    results = sp.next(results)
    albums.extend(results["items"])

  # spotify returns the same album many times across markets, so dedupe
  # by name to avoid a pile of redundant track lookups.
  seen = set()
  unique_albums = []
  for album in albums:
    key = album["name"].lower()
    if key not in seen:
      seen.add(key)
      unique_albums.append(album)

  # get credited artists from each album's tracks
  collaborator_ids = set()
  for album in unique_albums:
    for track in sp.album_tracks(album["id"])["items"]:
      for credited in track["artists"]:
        if credited["id"] != artist_id:
          collaborator_ids.add(credited["id"])

  if not collaborator_ids:
    return []

  collaborators = []
  ids = list(collaborator_ids)
  for i in range(0, len(ids), 50):
    batch = ids[i:i + 50]
    collaborators.extend(sp.artists(batch)["artists"])

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
  

def get_top_tracks(artist, country="US"):
  """An artist's most popular tracks as dictionaries"""
  results = sp.artist_top_tracks(artist["id"], country=country)


  return [
    {
      "title": t["name"],
      "track_id": t["id"],
      "popularity": t["popularity"],
      "artist_name": artist["name"],
      "album_id": t["album"]["id"], # for the same-album swap step
      "album_name": t["album"]["name"],
    }
    for t in results["tracks"]
  ]


def rank_top_tracks(artists, limit=10):
  """Pool every artist's top tracks, dedupe by track, and rank by
    popularity."""
  pool = {}
  for artist in artists:
    for track in get_top_tracks(artist):
      pool[track["track_id"]] = track # dedupe
    
  ranked = sorted(pool.values(), key=lambda t: t["popularity"], reverse=True)
  return ranked[:limit]
  