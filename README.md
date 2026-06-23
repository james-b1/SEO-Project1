## README file

Clear Database: 

```bash
sqlite3 recommender.db "DELETE FROM playlist_entries; DELETE FROM recommended_artists; DELETE FROM songs; DELETE FROM sqlite_sequence;"
```