import sqlite3
from datetime import datetime

DB_PATH= "recommender.db"

def getConnection():
  ''' Validate Connection '''
  return sqlite3.connect(DB_PATH)

def initDb():
  connection = getConnection()
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
      artist_id INTEGER NOT NULL,
      added_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (artist_id) REFERENCES recommended_artists(id)
    );
  """)

  connection.commit()
  connection.close()

# --Songs--
def writeSongs(songs):
  pass

def getSongs():
  pass

# --Recommendations--
def writeRecommendedArtists(artists):
  pass

def getRecommendedArtists():
  pass

# --Playlist--
def writePlaylist(artists):
  pass

def getplaylist():
  pass

# --Metrics--
def getMetrics():
  pass