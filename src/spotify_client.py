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

def getCollaborators(artist):
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
  uniqueAlbums = []
  for album in albums:
    key = album["name"].lower()
    if key not in seen:
      seen.add(key)
      uniqueAlbums.append(album)

  # get credited artists from each album's tracks
  collaboratorIds = set()
  for album in uniqueAlbums:
    for track in sp.album_tracks(album["id"])["items"]:
      for credited in track["artists"]:
        if credited["id"] != artistId:
          collaboratorIds.add(credited["id"])

  if not collaboratorIds:
    return []

  collaborators = []
  ids = list(collaboratorIds)
  for i in range(0, len(ids), 50):
    collaborators.extend(sp.artists(ids[i:i + 50])["artists"])

  return collaborators


def sameGenre(artistA, artistB):
  """True if the two artists share at least one genre."""
  return bool(set(artistA["genres"]) & set(artistB["genres"]))


def filterByGenre(inputArtist, collaborators):
  """Keep only collaborators who share a genre with the input artist."""
  return [c for c in collaborators if sameGenre(inputArtist, c)]


def collectRelatedArtists(artist):
  """Return same genre collaborators for an input artist"""
  collaborators = getCollaborators(artist)
  return filterByGenre(artist, collaborators)
  
