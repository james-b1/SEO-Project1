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
