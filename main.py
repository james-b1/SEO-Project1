from src.database import write_songs, init_db

def get_songs():
  '''Prompt for top 3 songs and play counts'''
  print("\n Answer in this format: [Song Name] [Number of Plays]")
  input1 = input("What is your most played song? ")
  input2 = input("What is your most 2nd played song? ")
  input3 = input("What is your most 3rd played song? ")
  return [input1, input2, input3]

def parse_songs(input):
  '''Parse a list of Name, Count into (title, plays)'''
  songs = []
  for entry in input:
    parts = entry.rsplit(" ", 1)
    title = parts[0]
    plays = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else 0
    songs.append((title, plays))
  return songs

def main():
  init_db()
  
  # Step 1: Get songs from user
  inputs = get_songs()

  # Step 2: Parse input into (title, plays) tuples
  songs = parse_songs(inputs)

  # Step 3: Write seed songs to database
  write_songs(songs)

  # Step 4: Search Spotify for each song's artist and genre

  # Step 5: Filter by genre, rank by popularity

  # Step 6: Get GenAI explanations for each recommended artist

  # Step 7: Show recommendations, user can swap if they want

  # Step 8: Display final list with explanations
  
  # Step 9: Write final playlist to database

  # Step 10: Show metrics (genre %, artist %)


if __name__ == "__main__":
  main()