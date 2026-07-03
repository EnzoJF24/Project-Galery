"""Command-line entry point for indexing a project directory.

Usage:
    python scan.py --root <path>

Walks the given root directory, finds render images inside each top-level
project folder, and indexes them into the local SQLite database. Re-running
this command is safe and incremental: only new images are processed.
"""
