"""
server.py — Aiven Data Signal
Zero external dependencies. Requires Python 3.6+.

Uses Server-Sent Events (SSE) — pure stdlib, no pip needed.

Usage:
    python3 server.py
Then open: http://localhost:8080
"""

import json
import time
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
EVENTS_FILE = SCRIPT_DIR / "events.json"
HOST = "localhost"
PORT = 8080

# ── Load events once at startup ───────────────────────────────────────────────

with open(EVENTS_FILE) as f:
    EVENTS = json.load(f)

print(f"[server] Loaded {len(EVENTS):,} events")


# ── Request handler ───────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # silence per-request logs

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")

    # ── SSE stream ──────────────────────────────────────────────────────────
    def stream_events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_cors_headers()
        self.end_headers()

        idx = random.randint(0, len(EVENTS) - 1)  # each client starts at a random offset
        n = len(EVENTS)

        try:
            while True:
                event = EVENTS[idx % n]
                idx += 1

                payload = f"data: {json.dumps(event)}\n\n"
                self.wfile.write(payload.encode())
                self.wfile.flush()

                # Use the pre-computed delay from data_prep (proportional to
                # real inter-event gaps, compressed to a 90-second loop).
                # Add a small jitter so multiple clients feel independent.
                delay_ms = event.get("delay_ms", 80)
                jitter   = random.uniform(-0.01, 0.01)
                time.sleep(delay_ms / 1000.0 + jitter)

        except (BrokenPipeError, ConnectionResetError):
            pass  # client disconnected

    # ── Static file serving ─────────────────────────────────────────────────
    def serve_file(self, path, content_type):
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_cors_headers()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_error(404)

    def do_GET(self):
        if self.path == "/events":
            self.stream_events()
        elif self.path in ("/", "/index.html"):
            self.serve_file(SCRIPT_DIR / "index.html", "text/html; charset=utf-8")
        elif self.path == "/events.json":
            self.serve_file(EVENTS_FILE, "application/json")
        else:
            self.send_error(404)


# ── Threaded server (each SSE client gets its own thread) ─────────────────────

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server = ThreadedHTTPServer((HOST, PORT), Handler)
    print(f"[server] Running — open http://{HOST}:{PORT}")
    print(f"[server] Press Ctrl-C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] Stopped")
