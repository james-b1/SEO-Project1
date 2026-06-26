"""Tiny ANSI color helpers for the CLI.

Color auto-disables when stdout isn't a terminal (piping, redirect, CI) or when
NO_COLOR is set, so output is never littered with raw escape codes — it just
falls back to plain text. Structural characters are kept ASCII so they render
anywhere a terminal does.
"""
import os
import sys

_CODES = {
  "reset": "\033[0m",
  "bold": "\033[1m",
  "dim": "\033[2m",
  "cyan": "\033[36m",
  "green": "\033[32m",
  "yellow": "\033[33m",
  "magenta": "\033[35m",
}


def _use_color():
  return sys.stdout.isatty() and os.getenv("NO_COLOR") is None


def c(text, *styles):
  """Wrap text in the given ANSI styles. No-op when color is disabled."""
  if not _use_color():
    return text
  prefix = "".join(_CODES[s] for s in styles)
  return f"{prefix}{text}{_CODES['reset']}"


def header(title):
  """Print a styled section header with a blank line above and an underline."""
  print()
  print(c(title, "bold", "cyan"))
  print(c("=" * len(title), "cyan"))


def banner():
  """Print the app title."""
  print()
  print(c("  PyTunes", "bold", "cyan"), c("- playlist recommender", "dim"))
