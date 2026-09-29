import psycopg2
import os
import time
import logging
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ── Logging setup ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


# ── DB connection ───────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


# ── Congestion thresholds ───────────────────────────────────────
# These are the rules that define what "congested" means.
# Adjust these numbers to tune sensitivity.
CONGESTION_RULES = {
    "low":    {"max_count": 20,  "min_speed": 40},
    "medium": {"max_count": 40,  "min_speed": 20},
    # anything above medium thresholds = high
}

def compute_congestion_level(avg_count: float, avg_speed: float) -> str:
    """
    Rule-based congestion detection.
    Returns 'low', 'medium', or 'high'.
    """
    if avg_count <= 20 and avg_speed >= 40:
        return "low"
    elif avg_count <= 40 and avg_speed >= 20:
        return "medium"
    else:
        return "high"


# ── Anomaly detection ───────────────────────────────────────────
def detect_anomaly(current_count: int, rolling_avg: float) -> tuple[bool, str]:
    """
    Flags a reading as anomalous if vehicle count deviates
    sharply from the recent rolling average.
    Returns (is_anomaly, reason_string).
    """
    if rolling_avg == 0:
        return False, ""

    ratio = current_count / rolling_avg

    if ratio >= 3.0:
        return True, f"Spike detected: count {current_count} is {ratio:.1f}x the rolling avg ({rolling_avg:.0f})"
    elif ratio <= 0.1:
        return True, f"Drop detected: count {current_count} is near zero vs rolling avg ({rolling_avg:.0f})"

    return False, ""


# ── Signal timing recommendation ────────────────────────────────
def compute_signal_timing(ns_count: float, ew_count: float) -> tuple[int, int, str]:
    """
    Adaptive signal timing based on vehicle density ratio.
    Total cycle = 90 seconds split between N-S and E-W.
    Returns (ns_green_secs, ew_green_secs, reason).
    """
    total_cycle = 90
    total_count = ns_count + ew_count

    if total_count == 0:
        return 45, 45, "No traffic detected — equal split"

    ns_ratio = ns_count / total_count
    ew_ratio = ew_count / total_count

    ns_green = max(20, min(70, int(total_cycle * ns_ratio)))
    ew_green = total_cycle - ns_green

    reason = (
        f"N-S: {ns_count:.0f} vehicles ({ns_ratio*100:.0f}%) "
        f"→ {ns_green}s green | "
        f"E-W: {ew_count:.0f} vehicles ({ew_ratio*100:.0f}%) "
        f"→ {ew_green}s green"
    )
    return ns_green, ew_green, reason


# ── Core analysis function ──────────────────────────────────────
def analyse_intersection(cursor, intersection_id: str):
    """
    Runs the full analysis pipeline for one intersection:
    1. Fetch last 2 min of readings
    2. Compute congestion level
    3. Detect anomaly
    4. Write to analysis_results
    5. Generate and write signal recommendation
    6. Create alert if congestion is high
    """

    # Step 1 — fetch last 2 minutes of readings
    cursor.execute("""
        SELECT vehicle_count, avg_speed_kmh, direction
        FROM readings
        WHERE intersection_id = %s
          AND timestamp >= NOW() - INTERVAL '2 minutes'
        ORDER BY timestamp DESC
    """, (intersection_id,))
    rows = cursor.fetchall()

    if not rows:
        log.info(f"  {intersection_id}: no recent readings, skipping")
        return

    # Step 2 — compute averages
    counts  = [r[0] for r in rows]
    speeds  = [r[1] for r in rows]
    avg_count = sum(counts) / len(counts)
    avg_speed = sum(speeds) / len(speeds)

    # Step 3 — congestion level
    congestion = compute_congestion_level(avg_count, avg_speed)

    # Step 4 — rolling average for anomaly (last 10 min)
    cursor.execute("""
        SELECT AVG(vehicle_count)
        FROM readings
        WHERE intersection_id = %s
          AND timestamp >= NOW() - INTERVAL '10 minutes'
    """, (intersection_id,))
    rolling_row = cursor.fetchone()
    rolling_avg = float(rolling_row[0]) if rolling_row[0] else 0.0

    latest_count = counts[0]
    is_anomaly, anomaly_reason = detect_anomaly(latest_count, rolling_avg)

    # Step 5 — write analysis result
    cursor.execute("""
        INSERT INTO analysis_results
            (intersection_id, congestion_level, avg_speed_1min,
             vehicle_count_1min, is_anomaly, anomaly_reason)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        intersection_id,
        congestion,
        round(avg_speed, 2),
        int(avg_count),
        is_anomaly,
        anomaly_reason
    ))

    # Step 6 — signal timing (split N-S vs E-W readings)
    ns_rows = [r for r in rows if r[2] == "N-S"]
    ew_rows = [r for r in rows if r[2] == "E-W"]
    ns_count = sum(r[0] for r in ns_rows) / max(len(ns_rows), 1)
    ew_count = sum(r[0] for r in ew_rows) / max(len(ew_rows), 1)

    ns_green, ew_green, rec_reason = compute_signal_timing(ns_count, ew_count)

    cursor.execute("""
        INSERT INTO recommendations
            (intersection_id, ns_green_secs, ew_green_secs, reason)
        VALUES (%s, %s, %s, %s)
    """, (intersection_id, ns_green, ew_green, rec_reason))

    # Step 7 — create alert if high congestion or anomaly
    if congestion == "high" or is_anomaly:
        severity = "critical" if (congestion == "high" and is_anomaly) else "warning"
        message = (
            f"Congestion: {congestion.upper()}, "
            f"Speed: {avg_speed:.1f} km/h, "
            f"Count: {avg_count:.0f} vehicles"
        )
        if is_anomaly:
            message += f" | ANOMALY: {anomaly_reason}"

        cursor.execute("""
            INSERT INTO alerts
                (intersection_id, severity, message)
            VALUES (%s, %s, %s)
        """, (intersection_id, severity, message))

    log.info(
        f"  {intersection_id}: {congestion.upper():6s} | "
        f"speed={avg_speed:.1f} km/h | "
        f"count={avg_count:.0f} | "
        f"anomaly={'YES' if is_anomaly else 'no'}"
    )


# ── Main loop ───────────────────────────────────────────────────
def run_analysis_loop(interval_seconds: int = 10):
    """
    Runs the analysis engine continuously.
    Every `interval_seconds`, analyses all 8 intersections.
    """
    log.info("Analysis engine started. Running every %ds.", interval_seconds)

    while True:
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Fetch all intersection IDs
            cursor.execute("SELECT id FROM intersections ORDER BY id;")
            intersection_ids = [row[0] for row in cursor.fetchall()]

            log.info("── Analysis cycle: %s ──", datetime.now().strftime("%H:%M:%S"))

            for iid in intersection_ids:
                analyse_intersection(cursor, iid)

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            log.error("Analysis cycle failed: %s", e)

        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_analysis_loop(interval_seconds=10)