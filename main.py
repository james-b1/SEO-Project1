from src.spotify_client import (
  search_artist, 
  get_collaborators, 
  rank_top_tracks
)
from src.genai_client import explain_artist
from src.database import (
    init_db, write_songs,
    write_recommended_artists, update_artist_explanations,
    write_playlist, clear_playlist, get_metrics
)

def get_songs():
  '''Prompt for top 3 songs and play counts'''
  print("\nAnswer in this format: [Song Name] [Number of Plays]")
  input1 = input("What is your most played song? ")
  input2 = input("What is your 2nd most played song? ")
  input3 = input("What is your 3rd most played song? ")
  return [input1, input2, input3]

def get_playlist_size():
  '''Ask how many songs the playlist should have.'''
  answer = input("How many songs do you want in your playlist? "
  "(default 10, max 50) ").strip()

  if not answer:
    return 10

  if not answer.isdigit():
    return 10

  size = int(answer)
  return size if 1 <= size <= 50 else 10
  

def parse_songs(entries):
  '''Parse a list of "Name, Count" (str) into (title, plays) (tuple)'''
  songs = []
  for entry in entries:
    parts = entry.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].isdigit():
      title, plays = parts[0], int(parts[1])
    else:
      title, plays = entry, 0   # no valid count: keep the whole title
    songs.append((title, plays))
  return songs

def swap_songs(playlist, candidates):
  '''Lets the user drop songs they don't like. Removing a song also drops
     any same-album siblings, then the gaps refill from the candidate pool,
     skipping albums the user has already rejected.'''
  size = len(playlist)
  rejected_albums = set()

  while True:
    print("\n Your Playlist:")

    for i, track in enumerate(playlist, 1):
      tag = " (synthetic)" if track.get("synthetic") else ""
      print(f"{i}. {track['title']} by {track['artist_name']}{tag}")

    choice = input(
      "Number to remove a song or Enter to keep the playlist: "
      ).strip()

    if not choice:
      return playlist

    if not choice.isdigit() or not (1 <= int(choice) <= len(playlist)):
      print("Please enter a valid number from the list.")
      continue

    idx = int(choice)
    removed_track = playlist[idx - 1]
    album = removed_track['album_id']
    rejected_albums.add(album)

    if album:
      playlist = [t for t in playlist if t.get("album_id") != album]
    else:
      playlist = [t for t in playlist if t != removed_track]

    on_list = {t['track_id'] for t in playlist}
    for candidate in candidates:
      if len(playlist) >= size:
        break
      if candidate["album_id"] in rejected_albums or candidate["track_id"] in on_list:
        continue

      playlist.append(candidate)
      on_list.add(candidate['track_id'])
  return playlist

def main():
  """Run PyTunes CLI"""
  init_db()

  # Step 1: Get songs from user
  inputs = get_songs()

  # Step 2: Parse input into (title, plays) tuples
  songs = parse_songs(inputs)

  # Step 3: Write seed songs to database
  write_songs(songs)

  # Step 4: Search Spotify for each song's artist and genre
  artists = []
  for title, plays in songs:
    result = search_artist(title)
    print(result['images'])
    if result:
      result["seed_plays"] = plays
      artists.append(result)
    else:
      print(f"Could not find a spotify match for {title!r}; skipping it.")

  # Step 5: Expand each input artist into same-genre collaborators.
  input_ids = {a['id'] for a in artists}
  pool = {}
  links = {}

  scores = {}
  for artist in artists:
    for collaborator in get_collaborators(artist, limit=10): # track collaborators for next step
      cid = collaborator['id']
      if cid not in input_ids:
        pool[cid] = collaborator
        links.setdefault(cid, set()).add(artist["name"])
        scores[cid] = scores.get(cid, 0) + artist.get("seed_plays", 0)

  recommended = sorted(
    pool.values(), 
    key=lambda a: (scores.get(a["id"], 0), a.get("popularity", 0)),
    reverse=True
    )[:5] # set cap to 5 API calls
  write_recommended_artists(recommended)

  # Step 6: Get GenAI explanations for each recommended artist
  print("\n Recommended Artists: ")

  explanations = []
  for artist in recommended:
    connected_to = sorted(links.get(artist['id'], []))

    try:
      text = explain_artist(artist, connected_to)
    except Exception as err:
      print(f"  (skipped {artist['name']}: {err})")
      continue

    explanations.append((text, artist['id']))
    tag = " (synthetic)" if artist.get("synthetic") else ""
    print(f"  {artist['image']} {artist['name']}{tag}: {text}")

  update_artist_explanations(explanations)

  # Step 7: Build the playlist
  size = get_playlist_size()
  candidates = rank_top_tracks(recommended, limit=(size*2))
  playlist = candidates[:size]

  # Step 8: Let the user remove songs he doesn't like
  playlist = swap_songs(playlist, candidates)

  clear_playlist()
  write_playlist(playlist)

  # Step 9: Write final playlist to database
  print(f"\nFinal Playlist ({len(playlist)} songs):")
  for i, track in enumerate(playlist, 1):
    tag = " (synthetic)" if track.get("synthetic") else ""
    print(f"  {i}. {track['title']} by {track['artist_name']}{tag} "
          f"(popularity {track['popularity']})")

  # Step 10: Show metrics (genre %, artist %)
  metrics = get_metrics()
  breakdown = metrics.get("artist_breakdown", {})
  if breakdown:
    print("")
    for artist_name, pct in sorted(
      breakdown.items(), key=lambda x: x[1], reverse=True
    ):
      print(f"  {artist_name}: {pct}%")


if __name__ == "__main__":
  main()
