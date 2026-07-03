"""Streamlit entry point for the Project Gallery viewer.

Usage:
    streamlit run app.py

Reads exclusively from the SQLite index built by scan.py — this app never
scans the filesystem directly. Run a scan first if the gallery is empty.
"""
