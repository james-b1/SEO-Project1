import sqlite3

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
      play_count INTEGER NOT NULL,
      artist TEXT
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
      images TEXT,
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
    "INSERT INTO songs (title, play_count, artist) VALUES(?, ?, ?)",
    songs
  )
  connection.commit()
  connection.close()

def get_songs():
  connection = get_connection()
  writer = connection.cursor()
  writer.execute("SELECT title, play_count, artist FROM songs")
  rows = writer.fetchall()
  connection.close()
  return rows

# -------------------Recommendations----------------------
def write_recommended_artists(artists):
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

def update_artist_explanations(explanations):
  """
  Update GenAI explanations for recommended artists.
  """
  connection = get_connection()
  cursor = connection.cursor()

  cursor.executemany(
      """
      UPDATE recommended_artists
      SET explanation = ?
      WHERE spotify_id = ?
      """,
      explanations,
  )

  connection.commit()
  connection.close()

def get_recommended_artists():
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
def write_playlist(tracks):
  connection = get_connection()
  cursor = connection.cursor()

  rows = [
    (t["title"], t["track_id"], t["artist_name"], t["album_id"], t["popularity"], t.get('images'))
    for t in tracks
  ]

  cursor.executemany(
    """
    INSERT or IGNORE INTO playlist_entries
      (title, track_id, artist_name, album_id, popularity, images)
    VALUES (?, ?, ?, ?, ?, ?)
    """,
    rows,
    )
  connection.commit()
  connection.close()

def get_playlist():
  connection = get_connection()
  cursor = connection.cursor()

  cursor.execute(
    "SELECT title, track_id, artist_name, album_id, popularity, images "
    "FROM playlist_entries ORDER BY popularity DESC"
  )
  rows = cursor.fetchall()
  connection.close()
  return [
    {"title": title, "track_id": track_id, "artist_name": artist_name,
     "album_id":album_id, "popularity": popularity, "images": images}
     for (title, track_id, artist_name, album_id, popularity, images) in rows
  ]

def clear_playlist():
  connection = get_connection()
  cursor = connection.cursor()
  cursor.execute("DELETE FROM playlist_entries")
  connection.commit()
  connection.close()
  
# -----------------------------Metrics---------------------------
def get_metrics():
  connection = get_connection()
  writer = connection.cursor()

  writer.execute(
    "SELECT artist_name, COUNT(*) as count "
    "FROM playlist_entries GROUP BY artist_name"
  )

  rows = writer.fetchall()
  connection.close()

  total = sum(count for _, count in rows)
  if total == 0:
    return {"artist_breakdown": {}}
  
  artist_breakdown = {
    name: round((count / total) * 100, 1)
    for name, count in rows
  }

  return {"artist_breakdown": artist_breakdown}