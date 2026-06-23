import sqlite3
from datetime import datetime

DB_PATH= "recommender.db"

def get_connection():
  ''' Opens Connection '''
  return sqlite3.connect(DB_PATH)

def init_db():
  connection = get_connection()
  writer = connection.cursor()

  writer.executescript("""
    CREATE TABLE IF NOT EXISTS songs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      play_count INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS recommended_artists (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      spotify_id TEXT UNIQUE NOT NULL,
      genre TEXT,
      popularity INTEGER,
      explanation TEXT
    );

    CREATE TABLE IF NOT EXISTS playlist_entries (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      track_id TEXT UNIQUE NOT NULL,
      artist_name TEXT NOT NULL,
      album_id TEXT,
      popularity INTEGER,
      added_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
  """)

  connection.commit()
  connection.close()

# ----------------------Songs-------------------------
def write_songs(songs):
  connection = get_connection()
  writer = connection.cursor()
  writer.executemany(
    "INSERT INTO songs (title, play_count) VALUES(?, ?)",
    songs
  )
  connection.commit()
  connection.close()

def get_songs():
  connection = get_connection()
  writer = connection.cursor()
  writer.execute("SELECT title, play_count FROM songs")
  rows = writer.fetchall()
  connection.close()
  return rows

# -------------------Recommendations----------------------
def writeRecommendedArtists(artists):
  connection = get_connection()
  cursor = connection.cursor()
  rows = [
      (
        artist["name"],
        artist["id"],
        ", ".join(artist["genres"]),  # list -> text for storage
        artist["popularity"],
        None,  # explanation gets filled in later (step 6)
      )
      for artist in artists
  ]
  cursor.executemany(
      """
      INSERT OR IGNORE INTO recommended_artists
          (name, spotify_id, genre, popularity, explanation)
      VALUES (?, ?, ?, ?, ?)
      """,
      rows,
  )
  connection.commit()
  connection.close()

def getRecommendedArtists():
    connection = get_connection()
  cursor = connection.cursor()
  cursor.execute(
    "SELECT name, spotify_id, genre, popularity, explanation "
    "FROM recommended_artists ORDER BY popularity DESC"
  )
  rows = cursor.fetchall()
  connection.close()
  return [
    {
      "name": name,
      "id": spotify_id,
      "genres": genre.split(", ") if genre else [],  # text -> list
      "popularity": popularity,
      "explanation": explanation,
    }
    for (name, spotify_id, genre, popularity, explanation) in rows
  ]

# ---------------------------Playlists---------------------------
def writePlaylist(tracks):
  connection = get_connection()
  cursor = connection.cursor()

  rows = [
    (t["title"], t["track_id"], t["artist_name"], t["album_id"], t["popularity"])
    for t in tracks
  ]

  cursor.executemany(
    """
    INSERT or IGNORE INTO playlist_entries
      (title, track_id, artist_name, album_id, popularity)
    VALUES (?, ?, ?, ?, ?)
    """
    rows,
    )
  connection.comit()
  connection.close()

def getplaylist():
  conenction = get_connection()
  cursor = connection.cursor()

  cursor.execute(
    "SELECT title, track_id, artist_name, album_id, popularity"
    "FROM playlist_entries ORDER BY popularity DESC"
  )
  rows = cursor.fetchall()
  connection.close()
  return [
    {"title": title, "track_id": track_id, "artist_name": artist_name,
     "album_id":album_id, "popularity": popularity}
     for (title, track_id, artist_name, album_id, popularity) in rows
  ]

# -----------------------------Metrics---------------------------
def getMetrics():
  pass