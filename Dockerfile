# ── Aiven Data Signal — art installation ─────────────────────────────────────
# Pure Python stdlib server — no pip installs required.
# Build:  docker build -t data-signal .
# Run:    docker run -p 8080:8080 data-signal
# Open:   http://localhost:8080

FROM python:3.11-slim

WORKDIR /app

# Copy only the runtime files.
# data_prep.py is a one-time preprocessing step; events.json is its output.
COPY index.html events.json server.py ./

# server.py binds to "localhost" by default, which is unreachable from outside
# the container. Patch it to 0.0.0.0 so Docker port-mapping works correctly.
RUN sed -i 's/HOST = "localhost"/HOST = "0.0.0.0"/' server.py

EXPOSE 8080

CMD ["python3", "server.py"]
