# Retail AI Software — Backend, Analytics, Storage, Dashboards

The software side of an SIH retail-intelligence project: real-time shopper
analytics, inventory visibility, and queue management, designed to run
entirely offline/local (no cloud dependency).

This repo covers analytics, storage, alerts, a Streamlit BI dashboard, and
a PySide6 live control room — all built and tested against mock
video/inference/tracking, so it runs completely standalone right now, with
clean seams for the hardware/AI team's real camera stream and Qualcomm
Detectron2 inference engine to plug in later without any of this code
changing.

## Prerequisites

- Python 3.11 or newer
- Git

No Node.js, no Docker, no external database server needed — everything
runs locally with SQLite.

## Setup

```bash
git clone <repo-url>
cd retail-ai-software

python -m venv venv
```

Activate it:
```bash
# Windows (PowerShell)
venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate
```

If PowerShell blocks the activation script:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Install dependencies:
```bash
pip install -r requirements.txt
```

## Verify it works

```bash
pytest tests/ -v
```
Expected: **79 passed**. This includes tests proving the single-writer/WAL
SQLite design is genuinely enforced (not just documented), the alert
cooldown mechanism actually suppresses repeat alerts, and the PySide6
control room genuinely receives live data from its background thread —
not just that things import without errors.

## Run it — three components, three terminals

All three read/write the same local SQLite file (`data/retail_ai.db`,
created automatically on first run — nothing to set up manually).

**Terminal 1 — continuous demo data generator:**
```bash
python -m simulation.demo_mode --seed 42
```
Leave running. Simulates all 6 cameras (3 shelf, entrance, 2 queue) with
varying footfall and occasional queue spikes, so there's always live data
to look at.

**Terminal 2 — Streamlit BI dashboard:**
```bash
streamlit run dashboard/app.py
```
Opens in your browser. 9 pages: overview, traffic, occupancy, queue,
shelf, visibility, monetization, alerts, reports.

**Terminal 3 — PySide6 live control room:**
```bash
python -m control_room.main
```
A desktop window with live KPIs and an active-alerts list, updating every
~2 seconds, with an audio beep on new critical alerts.

Remember to activate the venv (`venv\Scripts\Activate.ps1` /
`source venv/bin/activate`) in each new terminal — it's the same one
environment, just needs activating per terminal session.

## Project structure and architecture

```
core/          # Pydantic data contracts (Frame, Detection, Track, Event, Alert, ...)
interfaces/    # Protocol definitions — the seams hardware plugs into
adapters/      # Mock implementations now; real GStreamer/Qualcomm adapters plug in later
analytics/     # Pure Python business logic — people counting, entry/exit, occupancy,
               # queue, shelf, visibility, monetization, event engine
alerts/        # Alert manager with cooldown
storage/       # SQLAlchemy + SQLite, single-writer/WAL enforced, Alembic migrations
services/      # Orchestration layer — the only thing UIs/pipeline call directly
pipeline/      # The real-time loop (currently driven by mock adapters)
file_management/  # Export/report file handling
dashboard/     # Streamlit BI dashboard
control_room/  # PySide6 live desktop view
simulation/    # Demo data generator
tests/         # 79 tests — unit (pure logic, no I/O) + integration (full chains)
```

**Core rule this whole codebase follows:** `interfaces/` defines contracts,
`adapters/` implements them, and nothing outside `adapters/` ever knows
which concrete implementation it's talking to. This is what lets the
hardware/AI team's real `GStreamerVideoSource` and
`QualcommInferenceEngine` get built independently and plug in later
without touching `analytics/`, `storage/`, `services/`, `control_room/`,
or `dashboard/` at all.

**Zero cloud dependency, by design:** SQLite is local, the event bus is
in-process (RabbitMQ — self-hosted only when it's wired in later), and
Streamlit/PySide6 both run purely on your own machine. Nothing here talks
to the internet at runtime.

## Team split

- **Software side (this repo):** backend, database, analytics, alerts,
  both dashboards — built here
- **Hardware/AI side (not in this repo yet):** Raspberry Pi, cameras,
  GStreamer streaming, Qualcomm Detectron2 inference, object tracking

## Optional: Alembic migrations

The schema is stable, but Alembic is set up for when it needs to change:
```bash
# after editing storage/models.py
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```
