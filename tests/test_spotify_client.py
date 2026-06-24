from src import spotify_client

class FakeSpotify:
  def __init__(self, search_results):
    self.search_results = search_results
  
  def search(self, **kwargs):
    return self.search_results
  
def test_get_collaborators_use_artist_genre_search(monkeypatch):
  fake = FakeSpotify({
    "artists": {
      "items": [
        {
          "name": "Original",
          "id": "artist-1",
          "popularity": 100,
          "genres": ["hip hop"],
        },
        {
          "name": "Collaborator",
          "id": "artist-2",
          "popularity": 80,
          "genres": ["hip hop"],
        },
      ]
    }
  })

  monkeypatch.setattr(spotify_client, "get_client", lambda: fake)

  artist = {
    "name": "Original",
    "id": "artist-1",
    "popularity": 100,
    "genres": ["hip hop"]
  }

  result = spotify_client.get_collaborators(artist)

  assert result == [
    {
      "name": "Collaborator",
      "id": "artist-2",
      "popularity": 80,
      "genres": ["hip hop"],
    }
  ]


def test_get_collaborators_returns_empty_without_genres(monkeypatch):
  monkeypatch.setattr(spotify_client, "get_client", lambda: None)

  artist = {
    "name": "No Genre",
    "id": "artist-1",
    "popularity": 50,
    "genres": []
  }

  assert spotify_client.get_collaborators(artist) == []


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
  def fake_get_top_tracks(artist):
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