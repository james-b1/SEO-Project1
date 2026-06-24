import pytest

from src import database

@pytest.fixture
def db(tmp_path, monkeypatch):
  monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
  database.init_db()
  return database

#------------------------HELPERS------------------------

def _artist(name, spotify_id, genres, popularity):
  return {
    "name": name, 
    "id": spotify_id, 
    "genres": genres,
    "popularity": popularity
  }

def _track(title, track_id, artist_name, album_id, popularity):
  return {
    "title": title,
    "track_id": track_id,
    "artist_name": artist_name,
    "album_id": album_id,
    "popularity": popularity
  }


# ------------------------SCHEMA------------------------
def test_init_db_creates_expected_tables(db):
  connection = db.get_connection()
  names = {
    row[0]
    for row in connection.execute(
      "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
  }
  connection.close()
  assert {"songs", "recommended_artists", "playlist_entries"} <= names

def test_init_db_is_idempotent(db):
  db.write_songs([("Keep Me", 5)])
  db.init_db()
  assert db.get_songs() == [("Keep Me", 5)]

# ------------------------SONGS------------------------
def test_write_and_get_songs(db):
  db.write_songs([("Song A", 10), ("Song B", 3)])
  assert sorted(db.get_songs()) == sorted([("Song A", 10), ("Song B", 3)])

def test_get_songs_empty(db):
  assert db.get_songs() == []

def test_write_songs_empty_list(db):
  db.write_songs([])
  assert db.get_songs() == []

def test_write_songs_allows_duplicate_titles(db):
  db.write_songs([("Same", 1), ("Same", 2)])
  assert sorted(db.get_songs()) == sorted([("Same", 1), ("Same", 2)])

# --------------------RECOMMENDED ARTISTS--------------------
  
def test_recommended_artists_with_genres(db):
  db.write_recommended_artists([_artist("Tame Impala", "id1", 
  ["psych", "rock"], 80)])
  rows = db.get_recommended_artists()
  assert rows == [
    {
      "name": "Tame Impala",
      "id": "id1",
      "genres":["psych", "rock"],
      "popularity": 80,
      "explanation": None,
    }
  ]

def test_recommended_artists_no_genres(db):
  db.write_recommended_artists([_artist("No Genre", "id0", [], 10)])
  assert db.get_recommended_artists()[0]["genres"] == []

def test_recommended_artists_empty_list(db):
  db.write_recommended_artists([])
  assert db.get_recommended_artists() == []

def test_recommended_artists_ordered_by_popularity(db):
  db.write_recommended_artists([
    _artist("Low", "id1", ["pop"], 5),
    _artist("High", "id2", ["rock"], 500),
  ])
  rows = db.get_recommended_artists()
  assert [row["name"] for row in rows] == ["High", "Low"]

def test_recommended_artists_ignore_duplicate_spotify_ids(db):
  db.write_recommended_artists([
    _artist("Low", "same-id", ["pop"], 5),
    _artist("High", "same-id", ["rock"], 500),
    ])
  rows = db.get_recommended_artists()
  assert len(rows) == 1
  assert rows[0]["name"] == "Low"

def test_update_artist_explanations(db):
  db.write_recommended_artists([
    _artist("Artist A", "id1", ["pop"], 50)
  ])
  db.update_artist_explanations([
    ("You might like this artist.", "id1")
  ])
  rows = db.get_recommended_artists()
  assert rows[0]["explanation"] == "You might like this artist."


# ---------------------------PLAYLIST--------------------------

def test_write_and_get_playlist(db):
  tracks = [
    _track("Track A", "track1", "Artist A", "album1", 90),
    _track("Track B", "track2", "Artist B", "album2", 20)
  ]
  db.write_playlist(tracks)
  assert db.get_playlist() == tracks

def test_get_playlist_empty(db):
  assert db.get_playlist() == []

def test_playlist_ordered_by_popularity(db):
  db.write_playlist([
    _track("Low", "track1", "Artist A", "album1", 10),
    _track("High", "track2", "Artist B", "album2", 90),
  ])
  rows = db.get_playlist()
  assert [row["title"] for row in rows] == ["High", "Low"]

def test_playlist_ignores_duplicate_track_ids(db):
  db.write_playlist([
    _track("First", "same_id", "Artist A", "album1", 10),
    _track("Duplicate", "same_id", "Artist B", "album2", 90),
  ])
  rows = db.get_playlist()

  assert len(rows) == 1
  assert rows[0]["title"] == "First"


def test_clear_playlist(db):
  db.write_playlist([
    _track("Track A", "track1", "Artist A", "album1", 90)
  ])
  db.clear_playlist()

  assert db.get_playlist() == []

#---------------------------METRICS--------------------------


def test_get_metrics_empty_playlist(db):
  assert db.get_metrics() == {"artist_breakdown": {}}


def test_get_metrics_artist_breakdown(db):
  db.write_playlist([
    _track("Track A", "track1", "Artist A", "album1", 90),
    _track("Track B", "track2", "Artist A", "album2", 80),
    _track("Track C", "track3", "Artist B", "album3", 70),
  ])
  assert db.get_metrics() == {
    "artist_breakdown": {
      "Artist A": 66.7,
      "Artist B": 33.3,
    }
  }