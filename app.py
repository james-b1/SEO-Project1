import os
import uuid

from flask import (
  Flask, flash, redirect, render_template, request, session, url_for
)

from src.spotify_client import search_artist, get_collaborators, rank_top_tracks
from src.genai_client import explain_artist
from src.database import (
  init_db, write_songs, write_recommended_artists,
  update_artist_explanations, write_playlist, clear_playlist,
  get_playlist, get_metrics,
)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")  # needed for session/flash

init_db()

SESSIONS = {}


def get_state():
  return SESSIONS.get(session.get("key"))


def new_state():
  key = str(uuid.uuid4())
  session["key"] = key
  SESSIONS[key] = {}
  return SESSIONS[key]


def build_recommendations(songs, size):
  """Steps 4-7 of the CLI pipeline: search artists, expand into
     collaborators, get GenAI explanations, rank playlist candidates."""
  artists = []
  missing = []
  for title, plays in songs:
    result = search_artist(title)
    if result:
      result["seed_plays"] = plays
      artists.append(result)
    else:
      missing.append(title)

  if not artists:
    return None, missing

  input_ids = {a['id'] for a in artists}
  pool, links, scores = {}, {}, {}
  for artist in artists:
    for collaborator in get_collaborators(artist, limit=10):
      cid = collaborator['id']
      if cid in input_ids:
        continue
      pool[cid] = collaborator
      links.setdefault(cid, set()).add(artist["name"])
      scores[cid] = scores.get(cid, 0) + artist.get("seed_plays", 0)

  recommended = sorted(
    pool.values(),
    key=lambda a: (scores.get(a["id"], 0), a.get("popularity", 0)),
    reverse=True
  )[:5]
  write_recommended_artists(recommended)

  explanations = []
  for artist in recommended:
    connected_to = sorted(links.get(artist['id'], []))
    try:
      text = explain_artist(artist, connected_to)
    except Exception:
      text = None
    artist["explanation"] = text
    if text:
      explanations.append((text, artist['id']))
  update_artist_explanations(explanations)

  candidates = rank_top_tracks(recommended, limit=(size * 2))

  state = new_state()
  state.update({
    "size": size,
    "recommended": recommended,
    "candidates": candidates,
    "playlist": candidates[:size],
    "rejected_albums": set(),
  })
  return state, missing


def remove_track(state, index):
  '''Dropping a song also drops same-album siblings, then refills
     from the candidate pool, skipping rejected albums.'''
  playlist = state["playlist"]
  removed = playlist[index]
  album = removed.get("album_id")
  state["rejected_albums"].add(album)

  if album:
    playlist = [t for t in playlist if t.get("album_id") != album]
  else:
    playlist = [t for t in playlist if t != removed]

  on_list = {t['track_id'] for t in playlist}
  for candidate in state["candidates"]:
    if len(playlist) >= state["size"]:
      break
    if candidate["album_id"] in state["rejected_albums"] \
        or candidate["track_id"] in on_list:
      continue
    playlist.append(candidate)
    on_list.add(candidate['track_id'])

  state["playlist"] = playlist
