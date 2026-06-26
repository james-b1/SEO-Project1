import pytest
from spotipy.exceptions import SpotifyException

from src import spotify_client

class FakeSpotify:
  def __init__(self, search_results):
    self.search_results = search_results

  def search(self, **kwargs):
    return self.search_results


class ThrottledSpotify:
  """A Spotify client that always raises a throttle/forbidden error."""
  def __init__(self, status=429):
    self.status = status

  def search(self, **kwargs):
    raise SpotifyException(self.status, -1, "throttled")

  def artist(self, artist_id):
    raise SpotifyException(self.status, -1, "throttled")


class SearchableSpotify:
  """A Spotify client that returns one exact-title track and one artist."""
  def __init__(self, track_name, artist_obj):
    self._track_name = track_name
    self._artist_obj = artist_obj

  def search(self, **kwargs):
    return {"tracks": {"items": [
      {"name": self._track_name, "popularity": 90,
       "artists": [{"id": self._artist_obj["id"]}]},
    ]}}

  def artist(self, artist_id):
    return self._artist_obj


class TrackCreditSpotify:
  """A Spotify client whose track search returns the given track list."""
  def __init__(self, tracks):
    self._tracks = tracks

  def search(self, **kwargs):
    return {"tracks": {"items": self._tracks}}


def _credit(seed_id, *collab_ids):
  artists = [{"id": seed_id, "name": "Seed"}]
  artists += [{"id": cid, "name": cid.upper()} for cid in collab_ids]
  return {"name": "song", "artists": artists}


def test_get_collaborators_ranks_by_co_credit_frequency(monkeypatch):
  # c1 features on two tracks, c2 on one -> c1 ranks first; seed excluded.
  tracks = [_credit("seed", "c1"), _credit("seed", "c1"), _credit("seed", "c2")]
  monkeypatch.setattr(spotify_client, "get_client", lambda: TrackCreditSpotify(tracks))

  result = spotify_client.get_collaborators({"name": "Seed", "id": "seed"})

  assert [c["id"] for c in result] == ["c1", "c2"]
  assert all(c["id"] != "seed" for c in result)
  assert result[0] == {"name": "C1", "id": "c1", "popularity": 0, "genres": []}


def test_get_collaborators_respects_limit(monkeypatch):
  tracks = [_credit("seed", f"c{i}") for i in range(10)]
  monkeypatch.setattr(spotify_client, "get_client", lambda: TrackCreditSpotify(tracks))

  result = spotify_client.get_collaborators({"name": "Seed", "id": "seed"}, limit=3)
  assert len(result) == 3


def test_get_collaborators_empty_when_no_features(monkeypatch):
  tracks = [_credit("seed"), _credit("seed")]  # solo tracks, no other credits
  monkeypatch.setattr(spotify_client, "get_client", lambda: TrackCreditSpotify(tracks))

  assert spotify_client.get_collaborators({"name": "Seed", "id": "seed"}) == []


def test_get_collaborators_uses_a_dev_mode_safe_limit(monkeypatch):
  # Dev-mode Spotify apps 400 on search limits above ~10; guard against regressions.
  captured = {}

  class Recorder:
    def search(self, **kwargs):
      captured.update(kwargs)
      return {"tracks": {"items": []}}

  monkeypatch.setattr(spotify_client, "get_client", lambda: Recorder())
  spotify_client.get_collaborators({"name": "Seed", "id": "seed"})
  assert captured["limit"] <= 10


def test_get_top_tracks_uses_search_results(monkeypatch):
  fake = FakeSpotify({
    "tracks": {
      "items": [
        {
          "name": "Track A",
          "id": "track-1",
          "popularity": 90,
          "album": {
            "id": "album-1",
            "name": "Album A"
          }
        }
      ]
    }
  })

  monkeypatch.setattr(spotify_client, "get_client", lambda: fake)
  
  artist = {
    "name": "Artist A",
    "id": "artist-1",
    "popularity": 100,
    "genres": ["hip hop"],
  }

  assert spotify_client.get_top_tracks(artist) == [
    {
      "title": "Track A",
      "track_id": "track-1",
      "popularity": 90,
      "artist_name": "Artist A",
      "album_id": "album-1",
      "album_name": "Album A"
    }
  ]


def test_rank_top_tracks_dedupes_and_sorts(monkeypatch):
  def fake_get_top_tracks(artist, limit=None):
    if artist["name"] == "Artist A":
      return[
        {
          "title": "Low",
          "track_id": "same-track",
          "artist_name": "Artist A",
          "album_id": "album-1",
          "album_name": "Album A",
          "popularity": 10
        }
      ]
    
    return [
      {
        "title": "High",
        "track_id": "track-2",
        "artist_name": "Artist B",
        "album_id": "album-2",
        "album_name": "Album B",
        "popularity": 100
      }
    ]
    
  monkeypatch.setattr(spotify_client, "get_top_tracks", fake_get_top_tracks)

  artists = [
    {"name": "Artist A"},
    {"name": "Artist B"}
  ]

  result = spotify_client.rank_top_tracks(artists)

  assert [track["title"] for track in result] == ["High", "Low"]


# ------------------- search_artist happy path -------------------

def test_search_artist_returns_best_match(monkeypatch):
  fake = SearchableSpotify(
    "Hello", {"name": "Adele", "id": "adele-1", "popularity": 88, "genres": []}
  )
  monkeypatch.setattr(spotify_client, "get_client", lambda: fake)

  assert spotify_client.search_artist("Hello") == {
    "name": "Adele",
    "id": "adele-1",
    "popularity": 88,
    "genres": [],
  }


# ------------------- synthetic fallback on throttle -------------------

@pytest.mark.parametrize("status", [429, 403])
def test_search_artist_falls_back_to_synthetic_on_throttle(monkeypatch, status):
  monkeypatch.setattr(spotify_client, "get_client", lambda: ThrottledSpotify(status))
  sentinel = {"name": "Synth", "id": "synthetic:artist:synth", "synthetic": True}
  monkeypatch.setattr(spotify_client, "synthetic_artist", lambda song: sentinel)

  assert spotify_client.search_artist("DNA.") is sentinel


def test_search_artist_reraises_non_throttle_errors(monkeypatch):
  monkeypatch.setattr(spotify_client, "get_client", lambda: ThrottledSpotify(500))
  monkeypatch.setattr(spotify_client, "synthetic_artist",
                      lambda song: pytest.fail("should not fall back on 500"))

  with pytest.raises(SpotifyException):
    spotify_client.search_artist("DNA.")


def test_get_collaborators_falls_back_to_synthetic_on_throttle(monkeypatch):
  monkeypatch.setattr(spotify_client, "get_client", lambda: ThrottledSpotify(429))
  sentinel = [{"name": "Synth", "id": "synthetic:artist:synth", "synthetic": True}]
  monkeypatch.setattr(spotify_client, "synthetic_collaborators",
                      lambda artist, limit=5: sentinel)

  artist = {"name": "Seed", "id": "seed-1", "genres": ["hip hop"]}
  assert spotify_client.get_collaborators(artist) is sentinel


def test_get_top_tracks_falls_back_to_synthetic_on_throttle(monkeypatch):
  monkeypatch.setattr(spotify_client, "get_client", lambda: ThrottledSpotify(429))
  sentinel = [{"title": "T", "track_id": "synthetic:track:x", "synthetic": True}]
  monkeypatch.setattr(spotify_client, "synthetic_top_tracks",
                      lambda artist, limit=10: sentinel)

  artist = {"name": "Artist A", "id": "a-1", "genres": ["pop"]}
  assert spotify_client.get_top_tracks(artist) is sentinel


def test_get_top_tracks_reraises_non_throttle_errors(monkeypatch):
  monkeypatch.setattr(spotify_client, "get_client", lambda: ThrottledSpotify(500))
  monkeypatch.setattr(spotify_client, "synthetic_top_tracks",
                      lambda artist, limit=10: pytest.fail("should not fall back on 500"))

  artist = {"name": "Artist A", "id": "a-1", "genres": ["pop"]}
  with pytest.raises(SpotifyException):
    spotify_client.get_top_tracks(artist)