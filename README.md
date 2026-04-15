# Aiven — Data Signal
### A Generative Art Installation

A living visual representation of the Aiven platform's API traffic.
Inspired by Refik Anadol's *Machine Hallucinations* — data as a breathing, moving organism.

---

## What you see

| Visual element | Meaning |
|---|---|
| Particle color | HTTP method (blue=GET, amber=POST, purple=PUT, rose=DELETE, mint=PATCH) |
| Particle burst size | Request volume (log-scaled) |
| Direction of travel | API endpoint group (Services → right, Auth → left, Metrics → upper-right…) |
| Red flash | Error response (4xx / 5xx) |
| Central core | The Aiven API gateway — origin of all signals |
| Trailing drift | Perlin noise field — gives organic, non-deterministic motion |

---

## Quick start

### 1. Generate the event stream (first time only)

```bash
python3 data_prep.py
```

This reads the CSV and produces `events.json` (~570 KB, 4 000 events).

### 3. Start the server

```bash
python3 server.py
```

### 4. Open the artwork

Navigate to **http://localhost:8080** in your browser.
Full-screen it for the full effect (F11 / Cmd+Ctrl+F).

---

## Architecture

```
CSV (aggregate_acorn_events)
       │
       ▼
  data_prep.py  ──►  events.json
                          │
                     server.py  (WebSocket :8765 + HTTP :8080)
                          │
                    index.html  (p5.js frontend)
                          │
                    ┌─────▼──────┐
                    │  Browser   │
                    │ generative │
                    │    art     │
                    └────────────┘
```

### Connecting to real Aiven API data

When ready to swap in live data, replace the `stream_events()` method in `server.py`
with a Kafka consumer (e.g. using `kafka-python` or `confluent-kafka`) reading from
your Aiven for Kafka topic that contains the `aggregate_acorn_events` stream.

The event schema the frontend expects:

```json
{
  "method":       "GET",
  "route_group":  "service",
  "interface":    "python",
  "status_code":  200,
  "is_error":     false,
  "num_particles": 8,
  "weight":       0.45
}
```

---

## Files

| File | Purpose |
|---|---|
| `data_prep.py` | Pre-processes CSV → `events.json` |
| `server.py` | WebSocket broadcaster + HTTP static server |
| `index.html` | p5.js generative art frontend |
| `events.json` | Generated stream data (4 000 events, loops continuously) |

---

*Built for the Aiven Hackathon — April 2026*
