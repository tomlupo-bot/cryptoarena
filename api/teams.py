"""Vercel serverless function — /api/teams"""
import json
import os
from http.server import BaseHTTPRequestHandler
from pathlib import Path

DATA_PATH = Path(os.getenv("ARENA_DATA_PATH", "./data/arena_data"))

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        teams = []
        if DATA_PATH.exists():
            teams = [d.name for d in DATA_PATH.iterdir() if d.is_dir() and not d.name.startswith(".")]
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({"teams": teams}).encode())
