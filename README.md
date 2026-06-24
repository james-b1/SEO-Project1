# PyTunes

A CLI playlist recommender. The user enters three songs and play counts, then the app uses Spotify and Gemini to recommend artists and build a playlist.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```bash
cp .env.example .env
```

Fill in:

```txt
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
GEMINI_API_KEY=
```

## Run

```bash
python main.py
```

## Test

```bash
pytest -q
```

## Clear Local Database

```bash
sqlite3 recommender.db "DELETE FROM playlist_entries; DELETE FROM recommended_artists; DELETE FROM songs; DELETE FROM sqlite_sequence;"
```