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
  return spotipy.Spotify(auth_manager=auth_manager)

sp = get_client()

def get_collaborators(artist):
  """Returns a list of full collaborator artist objects"""
  artistId = artist["id"]

  albums = []
  results = sp.artist_albums(artistId, album_type="album,single", limit=50)
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
      uniqueAlbums.append(album)

  # get credited artists from each album's tracks
  collaborator_ids = set()
  for album in unique_albums:
    for track in sp.album_tracks(album["id"])["items"]:
      for credited in track["artists"]:
        if credited["id"] != artistId:
          collaborator_ids.add(credited["id"])

  if not collaboratorIds:
    return []

  collaborators = []
  ids = list(collaborator_ids)
  for i in range(0, len(ids), 50):
    collaborators.extend(sp.artists(ids[i:i + 50])["artists"])

  return collaborators


def same_genre(artist_a, artist_b):
  """True if the two artists share at least one genre."""
  return bool(set(artist_a["genres"]) & set(artist_b["genres"]))


def filter_by_genre(input_artist, collaborators):
  """Keep only collaborators who share a genre with the input artist."""
  return [c for c in collaborators if sameGenre(input_artist, c)]


def collect_related_artists(artist):
  """Return same genre collaborators for an input artist"""
  collaborators = getCollaborators(artist)
  return filterByGenre(artist, collaborators)
  
def get_top_tracks(artist):
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

def rank_top_tracks(artists, country="US"):
  """Pool every artist's top tracks, dedupe by track, and rank by
    popularity."""
  pool = {}
  for artist in artists:
    for track in get_top_tracks(artist, country=country):
      pool[track["track_id"]] = track
      
  return sort(pool.values(), key=lambda t: t["popularity"], reverse=True)