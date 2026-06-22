def getSongs():
  print("/n Answer in this format: [Song Name] [Number of Plays]")
  
  input1 = input("What is your most played song? ")
  input2 = input("What is your most 2nd played song? ")
  input3 = input("What is your most 3rd played song? ")

  print(song1, end=" ")
  print(song2, end=" ")
  print(song3)

def parseSongs(input):
  response = input.split(" ")
  return (response[0], response[1]) # song, plays


def main():
  # get songs from user + number of plays
  getSongs()

  # parse the input
  parseSongs()

  # write to database
  writeSongs()

  # build recommendations
  recommendSongs()

if __name__ == "__main__":
  main()