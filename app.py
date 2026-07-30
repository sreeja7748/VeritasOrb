"""
Geodesic Auth — a map-click authentication backend.

Core idea: instead of typing a password, a user clicks an ORDERED sequence
of points on a map. We never store raw coordinates. Each point is first
snapped to a coarse grid cell (this IS the tolerance window — it's what
lets a human re-click "close enough" and still authenticate), then the
whole ordered sequence is salted and run through PBKDF2, exactly the way
you'd hash a typed password. The hash is one-way, so even a full database
leak does not hand an attacker usable coordinates.

Run:
    pip install -r requirements.txt
    python app.py
Then open http://localhost:5000
"""

import hashlib
import hmac
import math
import os
import sqlite3
import time
from contextlib import contextmanager

from flask import Flask, g, jsonify, request, send_from_directory

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

DB_PATH = os.path.join(os.path.dirname(__file__), "geodesic_auth.db")

# Tolerance grid cell size in degrees of latitude/longitude.
# 0.0005 deg of latitude is ~55m — roughly "which building", not
# "which exact paving stone". This is the single most important tuning
# knob in the whole system: too coarse and the keyspace collapses
# (see /api/entropy), too fine and legitimate users can't reproduce
# their own clicks.
GRID_SIZE_DEG = 1.0    

MIN_POINTS = 3
MAX_POINTS = 6

PBKDF2_ITERATIONS = 310_000  # OWASP 2023 recommendation for PBKDF2-HMAC-SHA256

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 60

app = Flask(__name__, static_folder="static", template_folder="templates")

# username -> {"count": int, "locked_until": float}
_rate_limit_state = {}


# --------------------------------------------------------------------------
# DB helpers
# --------------------------------------------------------------------------

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                salt TEXT NOT NULL,
                point_hash TEXT NOT NULL,
                num_points INTEGER NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.commit()


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Core crypto / geospatial logic
# --------------------------------------------------------------------------

def snap_to_grid(lat: float, lng: float) -> tuple:
    """Round a coordinate down to its tolerance cell. This is what makes
    re-clicking near-but-not-exactly the original point succeed: two
    clicks that fall in the same grid cell snap to the identical value
    and therefore hash identically."""
    return (
        round(lat / GRID_SIZE_DEG) * GRID_SIZE_DEG,
        round(lng / GRID_SIZE_DEG) * GRID_SIZE_DEG,
    )


def serialize_points(points: list) -> str:
    """Order matters — this is a *sequence* password, not a set."""
    snapped = [snap_to_grid(p["lat"], p["lng"]) for p in points]
    return "|".join(f"{lat:.6f},{lng:.6f}" for lat, lng in snapped)


def hash_points(points: list, salt: bytes) -> str:
    serialized = serialize_points(points).encode("utf-8")
    digest = hashlib.pbkdf2_hmac("sha256", serialized, salt, PBKDF2_ITERATIONS)
    return digest.hex()


def haversine_meters(lat1, lng1, lat2, lng2) -> float:
    """Used only for the entropy calculator's human-readable output —
    not part of the auth check itself, since matching happens in
    hash-space, not distance-space."""
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# --------------------------------------------------------------------------
# Rate limiting (brute-force / shoulder-surf retry protection)
# --------------------------------------------------------------------------

def check_locked(username: str):
    state = _rate_limit_state.get(username)
    if not state:
        return False, 0
    if state["count"] < MAX_FAILED_ATTEMPTS:
        return False, 0
    remaining = state["locked_until"] - time.time()
    if remaining <= 0:
        _rate_limit_state.pop(username, None)
        return False, 0
    return True, round(remaining)


def register_failure(username: str):
    state = _rate_limit_state.setdefault(username, {"count": 0, "locked_until": 0})
    state["count"] += 1
    if state["count"] >= MAX_FAILED_ATTEMPTS:
        state["locked_until"] = time.time() + LOCKOUT_SECONDS


def clear_failures(username: str):
    _rate_limit_state.pop(username, None)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def validate_points_payload(data):
    if not isinstance(data, dict):
        return "Malformed request body."
    username = data.get("username", "").strip()
    points = data.get("points")
    if not username or len(username) > 64:
        return "Username must be 1-64 characters."
    if not isinstance(points, list) or not (MIN_POINTS <= len(points) <= MAX_POINTS):
        return f"Must submit between {MIN_POINTS} and {MAX_POINTS} points."
    for p in points:
        if not isinstance(p, dict) or "lat" not in p or "lng" not in p:
            return "Each point needs lat and lng."
        try:
            lat, lng = float(p["lat"]), float(p["lng"])
        except (TypeError, ValueError):
            return "lat/lng must be numeric."
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return "lat/lng out of range."
    return None


# --------------------------------------------------------------------------
# Routes — static frontend
# --------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(app.template_folder, "index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(app.static_folder, filename)


# --------------------------------------------------------------------------
# Routes — API
# --------------------------------------------------------------------------

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}
    err = validate_points_payload(data)
    if err:
        return jsonify({"ok": False, "error": err}), 400

    username = data["username"].strip()
    points = data["points"]

    with get_db() as conn:
        existing = conn.execute(
            "SELECT 1 FROM users WHERE username = ?", (username,)
        ).fetchone()
        if existing:
            return jsonify({"ok": False, "error": "Username already registered."}), 409

        salt = os.urandom(16)
        point_hash = hash_points(points, salt)
        conn.execute(
            "INSERT INTO users (username, salt, point_hash, num_points, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, salt.hex(), point_hash, len(points), time.time()),
        )
        conn.commit()

    return jsonify({"ok": True, "message": "Registered. Remember your click order — it IS your password."})


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    err = validate_points_payload(data)
    if err:
        return jsonify({"ok": False, "error": err}), 400

    username = data["username"].strip()
    points = data["points"]

    locked, remaining = check_locked(username)
    if locked:
        return jsonify({
            "ok": False,
            "error": f"Too many failed attempts. Try again in {remaining}s."
        }), 429

    with get_db() as conn:
        row = conn.execute(
            "SELECT salt, point_hash, num_points FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    # Deliberately identical error for "no such user" and "wrong points":
    # distinguishing them would let an attacker enumerate valid usernames.
    generic_error = "Authentication failed."

    if not row:
        register_failure(username)
        return jsonify({"ok": False, "error": generic_error}), 401

    if row["num_points"] != len(points):
        register_failure(username)
        return jsonify({"ok": False, "error": generic_error}), 401

    salt = bytes.fromhex(row["salt"])
    candidate_hash = hash_points(points, salt)

    if hmac.compare_digest(candidate_hash, row["point_hash"]):
        clear_failures(username)
        return jsonify({"ok": True, "message": "Authenticated."})
    else:
        register_failure(username)
        return jsonify({"ok": False, "error": generic_error}), 401


@app.route("/api/entropy", methods=["GET"])
def api_entropy():
    """Teaching endpoint: shows the effective keyspace of the scheme given
    the current map viewport area and number of points, and compares it
    to a typed password. This is meant to be shown to students, not used
    for anything security-critical."""
    try:
        south = float(request.args.get("south"))
        north = float(request.args.get("north"))
        west = float(request.args.get("west"))
        east = float(request.args.get("east"))
        num_points = int(request.args.get("points", MIN_POINTS))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "south/north/west/east/points required."}), 400

    lat_span_m = haversine_meters(south, west, north, west)
    lng_span_m = haversine_meters(south, west, south, east)
    cell_m = haversine_meters(0, 0, GRID_SIZE_DEG, 0)  # approx cell edge length

    cols = max(1, lng_span_m / cell_m)
    rows = max(1, lat_span_m / cell_m)
    cells = cols * rows

    # Ordered sequence of `num_points` distinct cells: permutation, not combination.
    keyspace = 1
    for i in range(num_points):
        keyspace *= max(1, cells - i)

    bits = math.log2(keyspace) if keyspace > 0 else 0
    alnum_password_bits_per_char = math.log2(62)  # a-zA-Z0-9
    equivalent_password_len = bits / alnum_password_bits_per_char if bits else 0

    return jsonify({
        "ok": True,
        "grid_cells_in_view": round(cells),
        "keyspace": keyspace,
        "entropy_bits": round(bits, 1),
        "equivalent_alnum_password_length": round(equivalent_password_len, 1),
    })


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)