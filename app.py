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
  for title, plays, artist in songs:
    result = search_artist(title, artist)
    if result:
      result["seed_plays"] = plays
      artists.append(result)
    else:
      missing.append(title or artist)

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

  if not recommended:
        return None, missing

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

  if not candidates:
    return None, missing

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


@app.route("/")
def index():
  return render_template("index.html")


@app.route("/create", methods=["GET", "POST"])
def create():
  if request.method == "POST":
    songs = []
    titles = request.form.getlist("song")
    plays_list = request.form.getlist("plays")
    artists = request.form.getlist("artist")
    for title, plays_raw, artist in zip(titles, plays_list, artists):
      title = title.strip()
      plays_raw = plays_raw.strip()
      artist = artist.strip()
      plays = int(plays_raw) if plays_raw.isdigit() else 0
      # A row counts if either the song or the artist is filled in.
      if title or artist:
        songs.append((title, plays, artist))
    songs = songs[:5]

    if not songs:
      flash("Please enter at least one song or artist.")
      return redirect(url_for("create"))

    size_raw = request.form.get("size", "").strip()
    size = int(size_raw) if size_raw.isdigit() and 1 <= int(size_raw) <= 50 else 10

    write_songs(songs)
    state, missing = build_recommendations(songs, size)
    for title in missing:
      flash(f"Could not find a Spotify match for {title!r}; skipped it.")
    if state is None:
      flash("Couldn't build any recommendations — try again or use different songs.")
    return redirect(url_for("create"))

  return render_template("create.html", state=get_state())


@app.route("/remove/<int:index>", methods=["POST"])
def remove(index):
  state = get_state()
  if state and 0 <= index < len(state["playlist"]):
    remove_track(state, index)

  if request.headers.get("X-Requested-With") == "fetch":
    if not state:
      return ("", 409)
    return render_template("_playlist_tracks.html", state=state)

  return redirect(url_for("create"))


@app.route("/finalize", methods=["POST"])
def finalize():
  state = get_state()
  if not state or not state["playlist"]:
    flash("Build a playlist first.")
    return redirect(url_for("create"))

  clear_playlist()
  write_playlist(state["playlist"])
  SESSIONS.pop(session.pop("key", None), None)   # done with this session
  return redirect(url_for("results"))


@app.route("/restart", methods=["POST"])
def restart():
  SESSIONS.pop(session.pop("key", None), None)
  return redirect(url_for("create"))


@app.route("/results")
def results():
  playlist = get_playlist()
  if not playlist:
    flash("No playlist yet — build one first.")
    return redirect(url_for("create"))

  breakdown = sorted(
    get_metrics().get("artist_breakdown", {}).items(),
    key=lambda x: x[1], reverse=True,
  )
  return render_template("results.html", playlist=playlist, breakdown=breakdown)


if __name__ == "__main__":
  app.run(debug=True)
