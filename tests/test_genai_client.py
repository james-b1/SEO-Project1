import os

# genai.Client is built at import time; give it a dummy key so importing works.
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import pytest

from src import genai_client

ARTIST = {"name": "Drake", "genres": ["hip hop"]}
VALID = "You will enjoy this artist for their sharp flow and proven hits."  # >=8 words, ends in .


def test_explain_artist_uses_gemini_when_valid(monkeypatch):
  monkeypatch.setattr(genai_client, "_try_gemini", lambda msg: VALID)
  monkeypatch.setattr(genai_client, "_try_openrouter",
                      lambda msg: pytest.fail("should not reach OpenRouter"))

  text, source = genai_client.explain_artist(ARTIST, ["Future"])
  assert source == "gemini"
  assert text == VALID


def test_explain_artist_falls_back_to_openrouter(monkeypatch):
  monkeypatch.setattr(genai_client, "_try_gemini", lambda msg: "")
  monkeypatch.setattr(genai_client, "_try_openrouter", lambda msg: VALID)

  text, source = genai_client.explain_artist(ARTIST, ["Future"])
  assert source == "openrouter"
  assert text == VALID


def test_explain_artist_uses_hardcoded_fallback_when_both_fail(monkeypatch):
  monkeypatch.setattr(genai_client, "_try_gemini", lambda msg: "")
  monkeypatch.setattr(genai_client, "_try_openrouter", lambda msg: "")

  text, source = genai_client.explain_artist(ARTIST, ["Future"])
  assert source == "fallback"
  assert "Drake" in text


def test_explain_artist_rejects_invalid_gemini_text(monkeypatch):
  # Too short (< 8 words) -> not accepted as a gemini answer, cascades onward.
  monkeypatch.setattr(genai_client, "_try_gemini", lambda msg: "Good rapper indeed.")
  monkeypatch.setattr(genai_client, "_try_openrouter", lambda msg: "")

  _, source = genai_client.explain_artist(ARTIST, ["Future"])
  assert source == "fallback"
