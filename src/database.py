import sqlite3

DB_PATH= "recommender.db"

def getConnection():
  ''' Validate Connection '''
  return sqlite3.connect(DB_PATH)

def initDb():
  connection = getConnection()
  
  print("This is the DB")

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