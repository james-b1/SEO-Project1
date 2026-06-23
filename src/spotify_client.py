import spotipy
from spotify.oauth2 import SpotifyClientCredentials
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

def search_artist(title):
  """
  Searching Spotify for a song title and returning primary artist's details

  Song title -> dictionary
  """
  
  sp = get_client()

  results = sp.search(q=title, type="track", limit=1)
  tracks = results.get("tracks", {}).get("items", [])

  if not tracks:
    print(f" No results found for '{title}', skipping.")
    return None
  
  artist_stub = tracks[0]["artists"][0]
  artist_id = artist_stub["id"]

  artist = sp.artist(artist_id)

  genres = artist.get("genres", [])


  return {
    "name": artist["Name"],
    "spotify_id": artist_id,
    "genre": genres[0] if genres else None,
    "popularity": artist.get("popularity", 0),
    "all_genres": genres,
    "explanation": None
  }
