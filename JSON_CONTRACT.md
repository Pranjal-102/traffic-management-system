# JSON Data Contract
> Source of truth for all data formats. Nobody changes a field name without 
> updating this file and telling the team.

---

## 1. Simulator → MQTT (Gulshan writes this)

Topic: `traffic/readings/{intersection_id}`

```json
{
  "intersection_id": "IN_001",
  "timestamp": "2026-08-01T10:32:00Z",
  "vehicle_count": 34,
  "avg_speed_kmh": 28.5,
  "direction": "N-S"
}
```

Rules:
- `intersection_id` must be exactly: IN_001 to IN_008
- `direction` must be exactly `"N-S"` or `"E-W"` — nothing else
- `vehicle_count` is a whole number, never negative
- `avg_speed_kmh` is decimal, range 0–120

---

## 2. API Responses (Pranjal serves → Vaibhav consumes)

Base URL: `http://127.0.0.1:8000`
Full docs: `http://127.0.0.1:8000/docs`

### GET /api/intersections
```json
{
  "intersections": [
    {
      "id": "IN_001",
      "name": "MG Road & Ring Road",
      "latitude": 23.2599,
      "longitude": 77.4126,
      "congestion_level": "high",
      "avg_speed": 12.5,
      "vehicle_count": 47,
      "is_anomaly": false,
      "computed_at": "2026-08-01T10:32:00"
    }
  ]
}
```

### GET /api/summary
```json
{
  "total_intersections": 8,
  "congestion": { "low": 3, "medium": 3, "high": 2 },
  "active_alerts": 2,
  "avg_system_speed_kmh": 31.4
}
```

### GET /api/alerts
```json
{
  "alerts": [
    {
      "id": 1,
      "intersection_id": "IN_003",
      "intersection_name": "Arera Colony Crossing",
      "severity": "critical",
      "message": "Congestion: HIGH | ANOMALY: Spike detected",
      "triggered_at": "2026-08-01T10:30:00",
      "resolved": false
    }
  ]
}
```

### GET /api/recommendations
```json
{
  "recommendations": [
    {
      "intersection_id": "IN_001",
      "intersection_name": "MG Road & Ring Road",
      "ns_green_secs": 62,
      "ew_green_secs": 28,
      "reason": "N-S: 41 vehicles (69%) → 62s green",
      "generated_at": "2026-08-01T10:32:00"
    }
  ]
}
```

### GET /api/history?id=IN_001&mins=60
```json
{
  "intersection_id": "IN_001",
  "minutes": 60,
  "readings": [
    {
      "timestamp": "2026-08-01T09:32:00",
      "vehicle_count": 28,
      "avg_speed_kmh": 34.2,
      "direction": "N-S"
    }
  ]
}
```

### WebSocket /ws/live
Pushes every 5 seconds:
```json
{
  "type": "live_update",
  "data": [ ...same shape as /api/intersections array... ]
}
```

---

## 3. Intersection IDs (all eight)

| ID     | Name                    |
|--------|-------------------------|
| IN_001 | MG Road & Ring Road     |
| IN_002 | DB Mall Junction        |
| IN_003 | Arera Colony Crossing   |
| IN_004 | Hoshangabad Road Cross  |
| IN_005 | AIIMS Square            |
| IN_006 | Karond Junction         |
| IN_007 | Bhopal Talkies Cross    |
| IN_008 | Piplani Sector 9        |