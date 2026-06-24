from src import synthetic


# ------------------------- synthetic generators -------------------------

def test_synthetic_artist_normalizes_and_marks(monkeypatch):
  monkeypatch.setattr(
    synthetic, "_generate_json",
    lambda prompt: {"name": "The Echoes", "genres": ["Indie Rock", "Dream Pop"], "popularity": 73},
  )

  artist = synthetic.synthetic_artist("Some Song")
  assert artist == {
    "name": "The Echoes",
    "id": "synthetic:artist:the-echoes",
    "popularity": 73,
    "genres": ["indie rock", "dream pop"],
    "synthetic": True,
  }


def test_synthetic_artist_returns_none_on_failure(monkeypatch):
  monkeypatch.setattr(synthetic, "_generate_json", lambda prompt: None)
  assert synthetic.synthetic_artist("Some Song") is None


def test_synthetic_artist_clamps_and_defaults_popularity(monkeypatch):
  monkeypatch.setattr(
    synthetic, "_generate_json",
    lambda prompt: {"name": "X", "genres": "not a list", "popularity": 999},
  )
  artist = synthetic.synthetic_artist("Song")
  assert artist["popularity"] == 100      # clamped
  assert artist["genres"] == []           # non-list coerced to empty


def test_synthetic_collaborators_builds_list(monkeypatch):
  monkeypatch.setattr(
    synthetic, "_generate_json",
    lambda prompt: {"artists": [
      {"name": "Band A", "genres": ["hip hop"], "popularity": 60},
      {"name": "Band B", "genres": ["hip hop"], "popularity": 40},
      {"genres": ["no name -> skipped"]},
    ]},
  )

  result = synthetic.synthetic_collaborators({"name": "Seed", "genres": ["hip hop"]})
  assert [c["name"] for c in result] == ["Band A", "Band B"]
  assert all(c["id"].startswith("synthetic:artist:") for c in result)
  assert all(c["synthetic"] for c in result)


def test_synthetic_collaborators_respects_limit(monkeypatch):
  monkeypatch.setattr(
    synthetic, "_generate_json",
    lambda prompt: {"artists": [{"name": f"A{i}"} for i in range(10)]},
  )
  result = synthetic.synthetic_collaborators({"name": "Seed", "genres": ["pop"]}, limit=3)
  assert len(result) == 3


def test_synthetic_collaborators_empty_on_failure(monkeypatch):
  monkeypatch.setattr(synthetic, "_generate_json", lambda prompt: None)
  assert synthetic.synthetic_collaborators({"name": "Seed", "genres": ["pop"]}) == []


def test_synthetic_top_tracks_shape_and_album_grouping(monkeypatch):
  monkeypatch.setattr(
    synthetic, "_generate_json",
    lambda prompt: {"tracks": [
      {"title": "Track One", "album_name": "First LP", "popularity": 80},
      {"title": "Track Two", "album_name": "First LP", "popularity": 70},
      {"title": "Track Three", "album_name": "Second LP", "popularity": 60},
    ]},
  )

  tracks = synthetic.synthetic_top_tracks({"name": "Artist Z"})
  assert tracks[0] == {
    "title": "Track One",
    "track_id": "synthetic:track:artist-z:track-one",
    "popularity": 80,
    "artist_name": "Artist Z",
    "album_id": "synthetic:album:artist-z:first-lp",
    "album_name": "First LP",
    "synthetic": True,
  }
  # same album name -> same album_id (so swap_songs grouping works)
  assert tracks[0]["album_id"] == tracks[1]["album_id"]
  assert tracks[0]["album_id"] != tracks[2]["album_id"]


def test_synthetic_top_tracks_defaults_album_name(monkeypatch):
  monkeypatch.setattr(
    synthetic, "_generate_json",
    lambda prompt: {"tracks": [{"title": "Lonely Single", "popularity": 50}]},
  )
  tracks = synthetic.synthetic_top_tracks({"name": "Solo"})
  assert tracks[0]["album_name"] == "Solo Singles"


def test_synthetic_top_tracks_empty_on_failure(monkeypatch):
  monkeypatch.setattr(synthetic, "_generate_json", lambda prompt: None)
  assert synthetic.synthetic_top_tracks({"name": "Solo"}) == []
