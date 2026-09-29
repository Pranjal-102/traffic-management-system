from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
import os
import asyncio
import json
import logging
from dotenv import load_dotenv
from datetime import datetime
from contextlib import asynccontextmanager
from analysis import run_analysis_loop
import threading

load_dotenv()

# ── Logging ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


# ── Start analysis engine in background thread ───────────────────
def start_analysis_background():
    """Runs analysis loop in a separate thread so it doesn't block FastAPI."""
    thread = threading.Thread(
        target=run_analysis_loop,
        kwargs={"interval_seconds": 10},
        daemon=True
    )
    thread.start()
    log.info("Analysis engine thread started.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_analysis_background()
    yield


# ── App init ─────────────────────────────────────────────────────
app = FastAPI(
    title="Traffic Management System API",
    description="Real-time traffic data collection, analysis and management",
    version="1.0.0",
    lifespan=lifespan
)

# Allow React frontend to call this API (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── DB helper ─────────────────────────────────────────────────────
def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


def query(sql: str, params=None) -> list[dict]:
    """Run a SELECT and return list of dicts."""
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(sql, params or ())
    rows = [dict(r) for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return rows


# ── Helper: serialize datetimes in dicts ──────────────────────────
def serialize(rows: list[dict]) -> list[dict]:
    for row in rows:
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.isoformat()
    return rows


# ════════════════════════════════════════════════════════════════
#  ENDPOINTS
# ════════════════════════════════════════════════════════════════

# ── Health check ──────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "message": "Traffic API is running"}


# ── All intersections with latest status ──────────────────────────
@app.get("/api/intersections")
def get_intersections():
    """
    Returns all 8 intersections with their latest
    congestion level, speed, and vehicle count.
    """
    rows = query("""
        SELECT
            i.id,
            i.name,
            i.latitude,
            i.longitude,
            ar.congestion_level,
            ar.avg_speed_1min   AS avg_speed,
            ar.vehicle_count_1min AS vehicle_count,
            ar.is_anomaly,
            ar.computed_at
        FROM intersections i
        LEFT JOIN LATERAL (
            SELECT *
            FROM analysis_results
            WHERE intersection_id = i.id
            ORDER BY computed_at DESC
            LIMIT 1
        ) ar ON TRUE
        ORDER BY i.id;
    """)
    return {"intersections": serialize(rows)}


# ── Single intersection detail ────────────────────────────────────
@app.get("/api/intersections/{intersection_id}")
def get_intersection(intersection_id: str):
    """Returns one intersection's full detail."""
    rows = query("""
        SELECT
            i.id, i.name, i.latitude, i.longitude,
            ar.congestion_level,
            ar.avg_speed_1min   AS avg_speed,
            ar.vehicle_count_1min AS vehicle_count,
            ar.is_anomaly,
            ar.anomaly_reason,
            ar.computed_at
        FROM intersections i
        LEFT JOIN LATERAL (
            SELECT * FROM analysis_results
            WHERE intersection_id = i.id
            ORDER BY computed_at DESC LIMIT 1
        ) ar ON TRUE
        WHERE i.id = %s;
    """, (intersection_id.upper(),))

    if not rows:
        return {"error": "Intersection not found"}
    return {"intersection": serialize(rows)[0]}


# ── Historical readings ───────────────────────────────────────────
@app.get("/api/history")
def get_history(
    id: str = Query(..., description="Intersection ID e.g. IN_001"),
    mins: int = Query(60, description="How many minutes back to fetch")
):
    """
    Returns raw readings for one intersection
    over the last `mins` minutes.
    """
    rows = query("""
        SELECT timestamp, vehicle_count, avg_speed_kmh, direction
        FROM readings
        WHERE intersection_id = %s
          AND timestamp >= NOW() - INTERVAL '%s minutes'
        ORDER BY timestamp ASC;
    """, (id.upper(), mins))
    return {"intersection_id": id.upper(), "minutes": mins, "readings": serialize(rows)}


# ── Active alerts ─────────────────────────────────────────────────
@app.get("/api/alerts")
def get_alerts(limit: int = Query(20, description="Max number of alerts to return")):
    """Returns the most recent unresolved alerts."""
    rows = query("""
        SELECT
            a.id,
            a.intersection_id,
            i.name AS intersection_name,
            a.severity,
            a.message,
            a.triggered_at,
            a.resolved
        FROM alerts a
        JOIN intersections i ON i.id = a.intersection_id
        WHERE a.resolved = FALSE
        ORDER BY a.triggered_at DESC
        LIMIT %s;
    """, (limit,))
    return {"alerts": serialize(rows)}


# ── Signal timing recommendations ────────────────────────────────
@app.get("/api/recommendations")
def get_recommendations():
    """Returns the latest signal timing recommendation per intersection."""
    rows = query("""
        SELECT DISTINCT ON (intersection_id)
            r.intersection_id,
            i.name AS intersection_name,
            r.ns_green_secs,
            r.ew_green_secs,
            r.reason,
            r.generated_at
        FROM recommendations r
        JOIN intersections i ON i.id = r.intersection_id
        ORDER BY intersection_id, generated_at DESC;
    """)
    return {"recommendations": serialize(rows)}


# ── System summary ────────────────────────────────────────────────
@app.get("/api/summary")
def get_summary():
    """
    Returns system-wide stats:
    total intersections, congestion counts, active alerts,
    and average system speed.
    """
    totals = query("SELECT COUNT(*) AS total FROM intersections;")
    total_count = totals[0]["count"]

    congestion = query("""
        SELECT congestion_level, COUNT(*) AS count
        FROM (
            SELECT DISTINCT ON (intersection_id)
                intersection_id, congestion_level
            FROM analysis_results
            ORDER BY intersection_id, computed_at DESC
        ) latest
        GROUP BY congestion_level;
    """)
    congestion_map = {r["congestion_level"]: r["count"] for r in congestion}

    alerts_count = query("""
        SELECT COUNT(*) AS count FROM alerts WHERE resolved = FALSE;
    """)

    avg_speed = query("""
        SELECT ROUND(AVG(avg_speed_1min)::numeric, 1) AS avg_speed
        FROM (
            SELECT DISTINCT ON (intersection_id)
                intersection_id, avg_speed_1min
            FROM analysis_results
            ORDER BY intersection_id, computed_at DESC
        ) latest;
    """)

    return {
        "total_intersections": total_count,
        "congestion": {
            "low":    congestion_map.get("low",    0),
            "medium": congestion_map.get("medium", 0),
            "high":   congestion_map.get("high",   0),
        },
        "active_alerts": alerts_count[0]["count"],
        "avg_system_speed_kmh": float(avg_speed[0]["avg_speed"] or 0),
    }


# ── WebSocket: live updates every 5s ─────────────────────────────
@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    Pushes live intersection status to the frontend
    every 5 seconds without polling.
    """
    await websocket.accept()
    log.info("WebSocket client connected.")
    try:
        while True:
            rows = query("""
                SELECT
                    i.id, i.name, i.latitude, i.longitude,
                    ar.congestion_level,
                    ar.avg_speed_1min   AS avg_speed,
                    ar.vehicle_count_1min AS vehicle_count,
                    ar.is_anomaly,
                    ar.computed_at
                FROM intersections i
                LEFT JOIN LATERAL (
                    SELECT * FROM analysis_results
                    WHERE intersection_id = i.id
                    ORDER BY computed_at DESC LIMIT 1
                ) ar ON TRUE
                ORDER BY i.id;
            """)
            await websocket.send_text(json.dumps({
                "type": "live_update",
                "data": serialize(rows)
            }))
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        log.info("WebSocket client disconnected.")