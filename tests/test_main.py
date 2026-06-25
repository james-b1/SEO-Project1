import os

os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("SPOTIFY_CLIENT_ID", "test-client-id")
os.environ.setdefault("SPOTIFY_CLIENT_SECRET", "test-client-secret")

from main import parse_songs, swap_songs, get_playlist_size

def _track(title, track_id, artist_name, album_id, popularity):
  return{
    "title": title,
    "track_id": track_id,
    "artist_name": artist_name,
    "album_id": album_id,
    "popularity": popularity
  }


def test_parse_songs_with_play_counts():
  assert parse_songs(["DNA. 100", "DUCKWORTH. 80", "YAH. 60"]) == [
    ("DNA.", 100),
    ("DUCKWORTH.", 80),
    ("YAH.", 60),
  ]


def test_parse_songs_missing_count_defaults_to_zero():
  assert parse_songs(["DNA."]) == [("DNA.", 0)]


def test_parse_songs_keeps_numbers_inside_song_title():
  assert parse_songs(["99 Problems 99"]) == [("99 Problems", 99)]


def test_get_playlist_size_defaults_on_empty_input(monkeypatch):
  monkeypatch.setattr("builtins.input", lambda _: "")
  assert get_playlist_size() == 10


def test_get_playlist_size_defaults_on_invalid_input(monkeypatch):
  monkeypatch.setattr("builtins.input", lambda _: "ab")
  assert get_playlist_size() == 10


def test_get_playlist_size_accepts_positive_number(monkeypatch):
  monkeypatch.setattr("builtins.input", lambda _: "10")
  assert get_playlist_size() == 10

def test_get_playlist_size_defaults_when_above_limit(monkeypatch):
  monkeypatch.setattr("builtins.input", lambda _: "51")
  assert get_playlist_size() == 10

def test_swap_songs_keeps_playlist_when_input_is_enter(monkeypatch):
  playlist = [_track("A", "t1", "Artist", "album1", 90)]
  monkeypatch.setattr("builtins.input", lambda _: "")
  assert swap_songs(playlist, playlist) == playlist


def test_swap_songs_rejects_invalid_choice_then_keeps_playlist(monkeypatch):
  playlist = [_track("A", "t1", "Artist", "album1", 90)]
  answers = iter(["99", ""])
  monkeypatch.setattr("builtins.input", lambda _: next(answers))
  assert swap_songs(playlist, playlist) == playlist

def test_swap_songs_removes_same_album_and_refills(monkeypatch):
  playlist = [
    _track("A", "t1", "Artist", "album1", 90),
    _track("B", "t2", "Artist", "album1", 80)
  ]

  candidates = playlist + [
    _track("C", "t3", "Artist", "album2", 70),
    _track("D", "t4", "Artist", "album3", 60)
  ]

  answers = iter(["1", ""])
  monkeypatch.setattr("builtins.input", lambda _: next(answers))

  result = swap_songs(playlist, candidates)

  assert[track["title"] for track in result] == ["C", "D"]

