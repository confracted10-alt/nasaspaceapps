import html
import io
import json
from pathlib import Path
from datetime import date, datetime, timezone

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
import numpy as np

try:
    from shapely.geometry import shape, Point
except Exception:
    shape = Point = None

# -------------------------------------------------------------------
# TerraPulse | 3D Earth Explorer
# NASA FIRMS active-fire observations + CesiumJS globe
# -------------------------------------------------------------------

st.set_page_config(
    page_title="TerraPulse | Earth Explorer",
    layout="wide",
    initial_sidebar_state="expanded",
)

FIRMS_AREA_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
WORLDVIEW_SNAPSHOT_URL = "https://wvs.earthdata.nasa.gov/api/v1/snapshot"
CESIUM_VERSION = "1.127"

SENSORS = {
    "MODIS Terra/Aqua (approx. 1 km)": "MODIS_NRT",
    "VIIRS NOAA-20 (375 m)": "VIIRS_NOAA20_NRT",
    "VIIRS NOAA-21 (375 m)": "VIIRS_NOAA21_NRT",
}

# ------------------------------ Styling ------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700;800&family=DM+Serif+Display&display=swap');

    :root {
      --tp-bg: #101d17;
      --tp-panel: #1a2b21;
      --tp-panel2: #22372a;
      --tp-border: rgba(203, 219, 192, .16);
      --tp-text: #edf0e4;
      --tp-muted: #b3c0aa;
      --tp-sage: #b8cda8;
      --tp-accent: #b8cda8;
      --tp-accent-dark: #263a2c;
    }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp {
      background:
        radial-gradient(ellipse at 75% 0%, rgba(83, 112, 72, .16), transparent 38%),
        linear-gradient(180deg, #101d17 0%, #14231b 100%);
      color: var(--tp-text);
    }
    [data-testid="stHeader"] { background: rgba(16,29,23,.88); }
    [data-testid="stSidebar"] {
      background: linear-gradient(180deg, #1a2b21 0%, #14231b 100%);
      border-right: 1px solid var(--tp-border);
    }
    [data-testid="stSidebar"] * { color: var(--tp-text); }
    h1, h2, h3 { color: var(--tp-text) !important; letter-spacing: -.025em; }
    h1 { font-family: 'DM Serif Display', serif !important; font-weight: 400 !important; }
    p, label, .stMarkdown { color: var(--tp-text); }
    .tp-eyebrow {
      color: var(--tp-sage); font: 500 .68rem 'DM Mono', monospace;
      letter-spacing: .16em; text-transform: uppercase; margin-bottom: .5rem;
    }
    .tp-hero {
      font: 400 clamp(2.1rem, 5vw, 4rem)/1.03 'DM Serif Display', serif;
      color: #f0f0e5; letter-spacing: -.025em; margin: .15rem 0 .6rem 0;
    }
    .tp-subtitle { color: var(--tp-muted); font-size: .94rem; line-height: 1.65; max-width: 850px; }
    .tp-rule { border-top: 1px solid var(--tp-border); margin: .9rem 0 1.2rem 0; }
    .tp-card {
      background: linear-gradient(145deg, rgba(34,55,42,.95), rgba(24,42,31,.95));
      border: 1px solid var(--tp-border); border-radius: 15px;
      padding: 16px 18px; min-height: 102px;
    }
    .tp-card-label {
      color: var(--tp-muted); font: 500 .65rem 'DM Mono', monospace;
      letter-spacing: .09em; text-transform: uppercase; margin-bottom: .55rem;
    }
    .tp-card-value { color: var(--tp-text); font-size: 1.65rem; font-weight: 800; line-height: 1.1; }
    .tp-card-note { color: var(--tp-muted); font-size: .72rem; margin-top: .45rem; line-height: 1.4; }
    .tp-muted { color: var(--tp-muted); font-size: .82rem; line-height: 1.55; }
    .tp-section { color: var(--tp-text); font-size: 1.04rem; font-weight: 750; margin: .2rem 0 .25rem 0; }
    .tp-tag {
      display:inline-block; border:1px solid rgba(184,205,168,.28);
      background:rgba(184,205,168,.08); color:#c8d8bd; border-radius:999px;
      padding:4px 9px; font:500 .65rem 'DM Mono',monospace; letter-spacing:.05em;
    }
    div[data-testid="stMetric"] {
      background: rgba(26,43,33,.8); border: 1px solid var(--tp-border);
      padding: 12px 15px; border-radius: 13px;
    }
    div[data-testid="stMetricLabel"] { color: var(--tp-muted); }
    div[data-testid="stMetricValue"] { color: var(--tp-text); }
    .stButton button, .stDownloadButton button {
      border-radius: 10px; border: 1px solid rgba(184,205,168,.35);
      background: rgba(184,205,168,.10); color: var(--tp-text); font-weight: 700;
    }
    .stButton button:hover, .stDownloadButton button:hover {
      border-color: var(--tp-sage); color: white;
    }
    [data-testid="stDataFrame"] { border: 1px solid var(--tp-border); border-radius: 12px; overflow: hidden; }
    /* Keep Streamlit's interactive controls in the same sage/forest palette. */
    [data-baseweb="tag"] { background: #b8cda8 !important; color: #203027 !important; }
    [data-baseweb="tag"] * { color: #203027 !important; }
    [data-testid="stMultiSelect"] [data-baseweb="tag"] svg { fill: #203027 !important; }
    [data-testid="stSlider"] [role="slider"] { background: #b8cda8 !important; border-color: #b8cda8 !important; }
    [data-testid="stSlider"] [data-baseweb="slider"] div[role="progressbar"] { background: #8fa77b !important; }
    [data-testid="stRadio"] [data-checked="true"] { color: #b8cda8 !important; }
    button[kind="primary"] { background: #b8cda8 !important; color: #203027 !important; border-color: #b8cda8 !important; }
    button[kind="secondary"]:hover { border-color: #b8cda8 !important; color: #edf0e4 !important; }
    [data-testid="stAlert"] { border-radius: 12px; }
    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------ Data helpers ------------------------------

def format_acq_time(value):
    try:
        digits = str(int(float(value))).zfill(4)
        return f"{digits[:2]}:{digits[2:]} UTC"
    except (ValueError, TypeError, OverflowError):
        return "—"


def normalize_columns(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Normalize FIRMS columns while retaining original confidence values."""
    df = df.copy()
    df["sensor_source"] = source

    for col in ("latitude", "longitude", "frp", "scan", "track"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "frp" not in df.columns:
        df["frp"] = pd.NA

    brightness_col = next(
        (c for c in ("brightness", "bright_ti4", "bright_ti5", "bright_t31") if c in df.columns),
        None,
    )
    if brightness_col:
        df["thermal_brightness_k"] = pd.to_numeric(df[brightness_col], errors="coerce")
        df["brightness_field"] = brightness_col
    else:
        if "thermal_brightness_k" not in df.columns:
            df["thermal_brightness_k"] = pd.NA
        if "brightness_field" not in df.columns:
            df["brightness_field"] = "Not supplied"

    raw_conf = df["confidence"] if "confidence" in df.columns else pd.Series(pd.NA, index=df.index)
    conf_num = pd.to_numeric(raw_conf, errors="coerce")
    conf_text = raw_conf.astype(str).str.strip().str.lower()
    category_score = conf_text.map({
        "l": 30, "low": 30, "n": 60, "nominal": 60, "h": 90, "high": 90
    })
    calculated_score = conf_num.fillna(category_score)
    if "confidence_score_display" in df.columns:
        existing_score = pd.to_numeric(df["confidence_score_display"], errors="coerce")
        calculated_score = existing_score.fillna(calculated_score)
    df["confidence_score_display"] = calculated_score
    if "confidence_original" not in df.columns:
        df["confidence_original"] = raw_conf.astype(str)

    if "acq_date" in df.columns:
        df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce")
    else:
        df["acq_date"] = pd.NaT

    if "acq_time_display" not in df.columns:
        df["acq_time_display"] = (
            df["acq_time"].apply(format_acq_time) if "acq_time" in df.columns else "—"
        )
    if "daynight" not in df.columns:
        df["daynight"] = "Unknown"
    else:
        df["daynight"] = df["daynight"].map({
            "D": "Day", "N": "Night", "Day": "Day", "Night": "Night"
        }).fillna("Unknown")

    if "satellite" not in df.columns:
        df["satellite"] = source.replace("_NRT", "")
    return df.dropna(subset=["latitude", "longitude"])


def infer_source(raw: pd.DataFrame) -> str:
    """Infer the FIRMS product family from the uploaded CSV metadata."""
    if "sensor_source" in raw.columns and len(raw):
        return str(raw["sensor_source"].iloc[0])
    if "FIRMS source" in raw.columns and len(raw):
        return str(raw["FIRMS source"].iloc[0])
    instrument = str(raw["instrument"].iloc[0]).upper() if "instrument" in raw.columns and len(raw) else ""
    satellite = str(raw["satellite"].iloc[0]).upper() if "satellite" in raw.columns and len(raw) else ""
    if "MODIS" in instrument or "MODIS" in satellite:
        return "MODIS_NRT"
    if "NOAA-20" in satellite or "NOAA20" in satellite or satellite.strip() in {"N20", "J1"}:
        return "VIIRS_NOAA20_NRT"
    if "NOAA-21" in satellite or "NOAA21" in satellite or satellite.strip() in {"N21", "J2"}:
        return "VIIRS_NOAA21_NRT"
    if "SUOMI" in satellite or "NPP" in satellite or "SNPP" in satellite:
        return "VIIRS_SNPP_NRT"
    if "VIIRS" in instrument:
        return "VIIRS_SNPP_NRT"
    return "Uploaded FIRMS CSV"


def normalize_uploaded_csv(uploaded_file) -> pd.DataFrame:
    raw = pd.read_csv(uploaded_file)
    if raw.empty:
        return raw
    # Accept both original NASA FIRMS CSVs and TerraPulse's own exported CSV format.
    aliases = {
        "Acquisition date": "acq_date",
        "Acquisition time": "acq_time_display",
        "FIRMS source": "sensor_source",
        "Satellite": "satellite",
        "Latitude": "latitude",
        "Longitude": "longitude",
        "Original confidence": "confidence",
        "Display score (approx.)": "confidence_score_display",
        "Thermal brightness (K)": "thermal_brightness_k",
        "Brightness source field": "brightness_field",
        "FRP (MW)": "frp",
        "Day/night": "daynight",
    }
    raw = raw.rename(columns={key: value for key, value in aliases.items() if key in raw.columns})
    source = infer_source(raw)
    return normalize_columns(raw, source)


@st.cache_data(ttl=900, show_spinner=False, max_entries=16)
def fetch_source(api_key: str, source: str, days: int) -> pd.DataFrame:
    """Fetch one global FIRMS source; FIRMS area API supports 1–5 days."""
    url = f"{FIRMS_AREA_URL}/{api_key}/{source}/world/{days}"
    response = requests.get(url, timeout=(10, 90))
    response.raise_for_status()
    body = response.text.strip()
    if not body or body.lower().startswith(("invalid", "error", "no data")):
        raise RuntimeError(body[:250] or "FIRMS returned an empty response.")
    raw = pd.read_csv(io.StringIO(body))
    return normalize_columns(raw, source) if not raw.empty else raw


def get_worldview_snapshot_url(lat: float, lon: float, obs_date: date) -> str:
    half_lat, half_lon = 2.0, 2.8
    west, east = max(-180, lon - half_lon), min(180, lon + half_lon)
    south, north = max(-90, lat - half_lat), min(90, lat + half_lat)
    params = {
        "REQUEST": "GetSnapshot", "TIME": obs_date.isoformat(),
        "BBOX": f"{west},{south},{east},{north}", "CRS": "EPSG:4326",
        "LAYERS": "MODIS_Terra_CorrectedReflectance_TrueColor",
        "FORMAT": "image/jpeg", "WIDTH": "900", "HEIGHT": "560",
    }
    return requests.Request("GET", WORLDVIEW_SNAPSHOT_URL, params=params).prepare().url


def safe_float(row, key):
    try:
        value = row.get(key)
        return float(value) if pd.notna(value) else None
    except (ValueError, TypeError):
        return None


def _family_label(value):
    text = str(value if pd.notna(value) else "").upper()
    if text.startswith("MODIS"):
        return "MODIS"
    if text.startswith("VIIRS"):
        return "VIIRS"
    return "OTHER"


def _acquisition_timestamp(df: pd.DataFrame) -> pd.Series:
    """Build UTC acquisition timestamps from FIRMS date + HHMM fields."""
    dates = pd.to_datetime(df.get("acq_date"), errors="coerce", utc=True)
    if "acq_time" in df.columns:
        raw_time = df["acq_time"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(4)
    elif "acq_time_display" in df.columns:
        raw_time = (
            df["acq_time_display"].astype(str)
            .str.extract(r"(\d{1,2}):(\d{2})", expand=True)
            .fillna("")
            .agg("".join, axis=1)
            .str.zfill(4)
        )
    else:
        raw_time = pd.Series("0000", index=df.index)

    hh = pd.to_numeric(raw_time.str[:2], errors="coerce")
    mm = pd.to_numeric(raw_time.str[2:4], errors="coerce")
    valid = hh.between(0, 23) & mm.between(0, 59)
    offset = pd.to_timedelta(hh.fillna(0), unit="h") + pd.to_timedelta(mm.fillna(0), unit="m")
    result = dates + offset
    return result.where(valid & dates.notna())


def match_modis_viirs(dataframe: pd.DataFrame, radius_km=5.0, time_window_minutes=60, max_per_sensor=3000):
    """For each VIIRS detection, find its nearest eligible MODIS observation.

    This is a many-to-one candidate correspondence search, not a fire-identity
    classifier. Multiple finer-resolution VIIRS pixels may correspond to one
    coarser MODIS pixel. Acquisition times are compared in UTC.
    """
    work = dataframe.copy().reset_index(drop=True)
    work["_family"] = work["sensor_source"].map(_family_label)
    work["_timestamp"] = _acquisition_timestamp(work)
    work = work[work["_family"].isin(["MODIS", "VIIRS"])].dropna(
        subset=["latitude", "longitude", "_timestamp"]
    ).copy()
    modis = work[work["_family"] == "MODIS"].copy()
    viirs = work[work["_family"] == "VIIRS"].copy()

    if modis.empty or viirs.empty:
        return pd.DataFrame(), len(modis), len(viirs), False

    sampled = len(modis) > max_per_sensor or len(viirs) > max_per_sensor
    if len(modis) > max_per_sensor:
        modis = modis.sample(max_per_sensor, random_state=42)
    if len(viirs) > max_per_sensor:
        viirs = viirs.sample(max_per_sensor, random_state=42)

    mlat = np.radians(modis["latitude"].astype(float).to_numpy())
    mlon = np.radians(modis["longitude"].astype(float).to_numpy())
    vlat = np.radians(viirs["latitude"].astype(float).to_numpy())
    vlon = np.radians(viirs["longitude"].astype(float).to_numpy())
    mt = modis["_timestamp"].astype("int64").to_numpy() / 1e9
    vt = viirs["_timestamp"].astype("int64").to_numpy() / 1e9

    radius_earth = 6371.0088
    radius_rad = radius_km / radius_earth
    time_limit = time_window_minutes * 60
    rows = []

    # Chunk by VIIRS to keep memory bounded while evaluating all candidate pairs.
    chunk_size = 250
    for start in range(0, len(viirs), chunk_size):
        stop = min(start + chunk_size, len(viirs))
        lat1 = vlat[start:stop, None]
        lon1 = vlon[start:stop, None]
        dlat = mlat[None, :] - lat1
        dlon = mlon[None, :] - lon1
        hav = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(mlat[None, :]) * np.sin(dlon / 2) ** 2
        distances = 2 * radius_earth * np.arcsin(np.sqrt(np.clip(hav, 0, 1)))
        time_diffs = np.abs(mt[None, :] - vt[start:stop, None])
        eligible = (distances <= radius_km) & (time_diffs <= time_limit)
        eligible &= np.isfinite(distances) & np.isfinite(time_diffs)

        for local_i in range(stop - start):
            candidates = np.flatnonzero(eligible[local_i])
            if not len(candidates):
                continue
            # Rank by normalized spatial + temporal separation; retain the nearest candidate.
            scores = distances[local_i, candidates] / max(radius_km, 1e-9) + time_diffs[local_i, candidates] / max(time_limit, 1)
            best = candidates[int(np.argmin(scores))]
            vi = viirs.iloc[start + local_i]
            mo = modis.iloc[best]
            rows.append({
                "VIIRS satellite": str(vi.get("satellite", vi.get("sensor_source", "VIIRS"))),
                "MODIS satellite": str(mo.get("satellite", mo.get("sensor_source", "MODIS"))),
                "VIIRS date (UTC)": vi["_timestamp"].strftime("%Y-%m-%d %H:%M"),
                "MODIS date (UTC)": mo["_timestamp"].strftime("%Y-%m-%d %H:%M"),
                "Distance (km)": round(float(distances[local_i, best]), 3),
                "Time difference (min)": round(float(time_diffs[local_i, best] / 60), 1),
                "VIIRS latitude": round(float(vi["latitude"]), 5),
                "VIIRS longitude": round(float(vi["longitude"]), 5),
                "MODIS latitude": round(float(mo["latitude"]), 5),
                "MODIS longitude": round(float(mo["longitude"]), 5),
                "VIIRS FRP (MW)": safe_float(vi, "frp"),
                "MODIS FRP (MW)": safe_float(mo, "frp"),
                "VIIRS confidence": str(vi.get("confidence_original", "Not supplied")),
                "MODIS confidence": str(mo.get("confidence_original", "Not supplied")),
            })

    result = pd.DataFrame(rows)
    return result, len(modis), len(viirs), sampled


def make_cesium_html(dataframe: pd.DataFrame, focus_lat=None, focus_lon=None) -> str:
    """Render a self-contained CesiumJS globe with FIRMS detection entities."""
    records = []
    map_df = dataframe
    max_points = 6000
    sampled = len(map_df) > max_points
    if sampled:
        map_df = map_df.sample(max_points, random_state=42)

    for _, row in map_df.iterrows():
        lat, lon = safe_float(row, "latitude"), safe_float(row, "longitude")
        if lat is None or lon is None:
            continue
        frp = safe_float(row, "frp")
        family = _family_label(row.get("sensor_source", ""))
        # Sensor colors make the MODIS/VIIRS comparison legible at a glance.
        color = "#f4a340" if family == "MODIS" else "#48c7d8" if family == "VIIRS" else "#c5d0c8"
        obs_date = row["acq_date"].strftime("%Y-%m-%d") if pd.notna(row.get("acq_date")) else "Not supplied"
        source = html.escape(str(row.get("sensor_source", "Unknown")))
        satellite = html.escape(str(row.get("satellite", "Not supplied")))
        confidence = html.escape(str(row.get("confidence_original", "Not supplied")))
        brightness = safe_float(row, "thermal_brightness_k")
        records.append({
            "lat": lat, "lon": lon, "color": color,
            "size": max(5, min(13, 5 + (frp or 0) ** 0.35)),
            "source": source, "satellite": satellite,
            "date": obs_date, "time": html.escape(str(row.get("acq_time_display", "—"))),
            "confidence": confidence,
            "frp": f"{frp:.2f} MW" if frp is not None else "Not supplied",
            "brightness": f"{brightness:.2f} K" if brightness is not None else "Not supplied",
            "latText": f"{lat:.5f}", "lonText": f"{lon:.5f}",
        })

    payload = json.dumps(records, ensure_ascii=True).replace("</", "<\\/")
    focus = {
        "lat": float(focus_lat) if focus_lat is not None else 18.0,
        "lon": float(focus_lon) if focus_lon is not None else 0.0,
    }
    focus_json = json.dumps(focus)
    sampled_note = (
        f"Showing a responsive sample of {max_points:,} of {len(dataframe):,} filtered detections on the globe. "
        "Counts and exports still use all records."
        if sampled else f"Showing all {len(records):,} filtered detections on the globe."
    )
    note_json = json.dumps(sampled_note)

    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cesium.com/downloads/cesiumjs/releases/{CESIUM_VERSION}/Build/Cesium/Cesium.js"></script>
  <link href="https://cesium.com/downloads/cesiumjs/releases/{CESIUM_VERSION}/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
  <style>
    html, body, #cesiumContainer {{ width:100%; height:100%; margin:0; padding:0; overflow:hidden; background:#101d17; }}
    .cesium-viewer {{ border-radius:16px; overflow:hidden; }}
    .cesium-viewer-toolbar {{ top:12px; right:12px; }}
    .tp-overlay {{
      position:absolute; z-index:10; top:14px; left:14px; width:min(270px, calc(100% - 90px));
      padding:13px 14px; border:1px solid rgba(203,219,192,.2); border-radius:13px;
      background:rgba(16,29,23,.88); color:#edf0e4; backdrop-filter:blur(12px);
      font:12px/1.45 'Arial',sans-serif; box-shadow:0 8px 28px rgba(0,0,0,.22);
    }}
    .tp-brand {{ color:#c6d8b9; font-size:10px; letter-spacing:2px; font-weight:bold; }}
    .tp-title {{ font-size:16px; font-weight:bold; margin:5px 0 3px; }}
    .tp-note {{ color:#b3c0aa; font-size:10px; }}
    .tp-search {{ display:flex; gap:5px; margin-top:10px; }}
    .tp-search input {{ min-width:0; width:100%; border:1px solid #536b59; border-radius:7px; padding:7px; background:#1c3024; color:#fff; }}
    .tp-search button {{ border:0; border-radius:7px; padding:7px 9px; background:#b8cda8; color:#17251d; font-weight:bold; cursor:pointer; }}
    .tp-legend {{ display:flex; gap:9px; flex-wrap:wrap; margin-top:10px; color:#cbd6c4; font-size:10px; }}
    .dot {{ display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:4px; }}
    .tp-toggle {{ margin-top:8px; display:flex; gap:7px; align-items:center; color:#d5dfd0; }}
    .tp-map-controls {{ position:absolute; z-index:11; top:14px; right:14px; display:flex; gap:5px; padding:5px; border:1px solid rgba(30,45,38,.14); border-radius:11px; background:rgba(248,250,247,.96); box-shadow:0 3px 14px rgba(0,0,0,.22); }}
    .tp-map-controls button {{ border:0; border-radius:7px; padding:8px 10px; background:transparent; color:#26352d; font:600 11px Arial,sans-serif; cursor:pointer; }}
    .tp-map-controls button.active, .tp-map-controls button:hover {{ background:#e2eadf; color:#17251d; }}
    .tp-zoom {{ position:absolute; z-index:11; right:14px; bottom:34px; display:flex; flex-direction:column; gap:4px; }}
    .tp-zoom button {{ width:36px; height:36px; border:1px solid rgba(30,45,38,.14); border-radius:8px; background:rgba(248,250,247,.97); color:#26352d; font-size:20px; cursor:pointer; box-shadow:0 2px 8px rgba(0,0,0,.15); }}
    .tp-map-legend {{ margin-top:10px; padding-top:9px; border-top:1px solid rgba(203,219,192,.18); display:grid; gap:5px; color:#dce5d8; font-size:10px; }}
    .tp-legend-row {{ display:flex; align-items:center; gap:7px; }}
    .tp-legend-swatch {{ width:9px; height:9px; border-radius:50%; display:inline-block; }}
    .cesium-infoBox {{ background:rgba(16,29,23,.96); color:#edf0e4; border:1px solid #536b59; border-radius:10px; }}
    .cesium-infoBox-title {{ background:#22372a; color:#edf0e4; }}
    .cesium-infoBox-description {{ background:#17271e; color:#edf0e4; }}
    .cesium-infoBox-description table {{ color:#edf0e4; font-size:12px; }}
    .cesium-infoBox-description td {{ padding:4px 7px; border-bottom:1px solid #344a39; }}
    .cesium-infoBox-camera {{ display:none; }}
    .cesium-viewer .cesium-widget-credits {{ font-size:9px; }}
  </style>
</head>
<body>
  <div id="cesiumContainer"></div>
  <div class="tp-overlay">
    <div class="tp-brand">TERRAPULSE / EARTH EXPLORER</div>
    <div class="tp-title">Explore the living planet.</div>
    <div class="tp-note" id="recordNote">{html.escape(sampled_note)}</div>
    <div class="tp-search">
      <input id="coords" placeholder="Fly to coordinates: lat, lon" aria-label="Latitude and longitude">
      <button id="go">GO</button>
    </div>
    <label class="tp-toggle"><input type="checkbox" id="fireToggle" checked> Show fire detections</label>
    <div class="tp-map-legend">
      <div class="tp-legend-row"><i class="tp-legend-swatch" style="background:#f4a340"></i> MODIS · nominal ~1 km</div>
      <div class="tp-legend-row"><i class="tp-legend-swatch" style="background:#48c7d8"></i> VIIRS · nominal 375 m</div>
      <div class="tp-legend-row" style="color:#aebcaf">Marker = detection location, not fire perimeter</div>
    </div>
  </div>
  <div class="tp-map-controls" aria-label="Map type">
    <button class="active" data-map="satellite">Satellite</button>
    <button data-map="streets">Map</button>
    <button data-map="terrain">Terrain</button>
  </div>
  <div class="tp-zoom"><button id="zoomIn" aria-label="Zoom in">+</button><button id="zoomOut" aria-label="Zoom out">−</button></div>
  <script>
    const fireRecords = {payload};
    const start = {focus_json};
    const viewer = new Cesium.Viewer('cesiumContainer', {{
      animation:false, timeline:false, baseLayerPicker:false,
      geocoder:false, homeButton:true, sceneModePicker:true,
      navigationHelpButton:false, fullscreenButton:false,
      infoBox:true, selectionIndicator:true,
      baseLayer:false, terrainProvider:new Cesium.EllipsoidTerrainProvider(),
      scene3DOnly:true, shouldAnimate:true
    }});

    viewer.scene.globe.enableLighting = true;
    viewer.scene.globe.showGroundAtmosphere = true;
    viewer.scene.skyAtmosphere.show = true;
    viewer.scene.fog.enabled = true;
    viewer.scene.screenSpaceCameraController.minimumZoomDistance = 120000;
    viewer.scene.screenSpaceCameraController.maximumZoomDistance = 30000000;

    async function addImagery(mapType = 'satellite') {{
      const layers = {{
        satellite: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer',
        streets: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer',
        terrain: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer'
      }};
      try {{
        const imagery = await Cesium.ArcGisMapServerImageryProvider.fromUrl(layers[mapType] || layers.satellite);
        viewer.imageryLayers.removeAll();
        viewer.imageryLayers.addImageryProvider(imagery);
        document.querySelectorAll('.tp-map-controls button').forEach(button => {{
          button.classList.toggle('active', button.dataset.map === mapType);
        }});
      }} catch (error) {{
        console.error('Basemap could not be loaded:', error);
      }}
    }}


    const fireEntities = [];
    function addFires() {{
      fireRecords.forEach((r, index) => {{
        const description = `
          <table>
            <tr><td>FIRMS source</td><td>${{r.source}}</td></tr>
            <tr><td>Satellite</td><td>${{r.satellite}}</td></tr>
            <tr><td>Acquisition</td><td>${{r.date}} · ${{r.time}}</td></tr>
            <tr><td>Coordinates</td><td>${{r.latText}}, ${{r.lonText}}</td></tr>
            <tr><td>Original confidence</td><td>${{r.confidence}}</td></tr>
            <tr><td>FRP</td><td>${{r.frp}}</td></tr>
            <tr><td>Thermal brightness</td><td>${{r.brightness}}</td></tr>
          </table>
          <p style="color:#b3c0aa;font-size:11px">A FIRMS detection is a satellite-observed thermal anomaly, not independent confirmation of a wildfire.</p>
        `;
        const entity = viewer.entities.add({{
          name: `${{r.source}} · ${{r.latText}}, ${{r.lonText}}`,
          description: description,
          position: Cesium.Cartesian3.fromDegrees(r.lon, r.lat, 250),
          point: {{
            pixelSize: r.size,
            color: Cesium.Color.fromCssColorString(r.color).withAlpha(0.94),
            outlineColor: Cesium.Color.fromCssColorString('#f4ead6').withAlpha(0.85),
            outlineWidth: 1,
            disableDepthTestDistance: 10000000
          }}
        }});
        fireEntities.push(entity);
      }});
    }}

    document.getElementById('fireToggle').addEventListener('change', (event) => {{
      fireEntities.forEach(entity => entity.show = event.target.checked);
    }});
    function flyToCoordinates() {{
      const raw = document.getElementById('coords').value.trim();
      const parts = raw.split(/[,\\s]+/).map(Number);
      if (parts.length < 2 || !Number.isFinite(parts[0]) || !Number.isFinite(parts[1]) ||
          Math.abs(parts[0]) > 90 || Math.abs(parts[1]) > 180) {{
        alert('Enter valid coordinates as latitude, longitude.');
        return;
      }}
      viewer.camera.flyTo({{
        destination: Cesium.Cartesian3.fromDegrees(parts[1], parts[0], 450000),
        duration: 2
      }});
    }}
    document.getElementById('go').addEventListener('click', flyToCoordinates);
    document.getElementById('coords').addEventListener('keydown', e => {{
      if (e.key === 'Enter') flyToCoordinates();
    }});
    document.querySelectorAll('.tp-map-controls button').forEach(button => {{
      button.addEventListener('click', () => addImagery(button.dataset.map));
    }});
    document.getElementById('zoomIn').addEventListener('click', () => viewer.camera.zoomIn(viewer.camera.positionCartographic.height * 0.35));
    document.getElementById('zoomOut').addEventListener('click', () => viewer.camera.zoomOut(viewer.camera.positionCartographic.height * 0.35));

    addImagery().then(() => {{
      addFires();
      viewer.camera.flyTo({{
        destination: Cesium.Cartesian3.fromDegrees(start.lon, start.lat, 23000000),
        duration: 1.5
      }});
    }});
  </script>
</body>
</html>
"""


# ------------------------------ Sidebar ------------------------------

with st.sidebar:
    st.markdown('<div class="tp-eyebrow">TerraPulse / Explorer controls</div>', unsafe_allow_html=True)
    st.markdown("## Observation layers")
    api_key = st.secrets.get("FIRMS_MAP_KEY", "")
    if not api_key or "ADD_YOUR_NASA_FIRMS_KEY_HERE" in api_key or "paste_your_private" in api_key:
        api_key = ""
    selected_labels = st.multiselect(
        "Satellite instruments", list(SENSORS.keys()), default=list(SENSORS.keys())
    )
    days = st.select_slider(
        "Near-real-time observation window",
        options=[1, 2, 3, 4, 5], value=1,
        format_func=lambda x: f"Past {x} day{'s' if x != 1 else ''}",
    )
    confidence_threshold = st.slider(
        "Minimum confidence display score", 0, 100, 0, 10,
        help="MODIS numeric confidence is retained. VIIRS low/nominal/high categories are mapped to 30/60/90 for this shared display filter only; this is not a NASA-defined cross-sensor score.",
    )
    daynight_choice = st.radio("Day/night", ["All", "Day", "Night"], horizontal=True)
    min_frp_filter = st.number_input("Minimum FRP (MW)", min_value=0.0, max_value=10000.0, value=0.0, step=1.0, help="FRP is the rate of radiant energy emitted by a detected pixel. Leave at zero to include all values.")
    refresh = st.button("Refresh NASA data", use_container_width=True)
    if refresh:
        st.cache_data.clear()
        st.rerun()

    st.markdown('<div class="tp-rule"></div>', unsafe_allow_html=True)
    st.markdown("### Offline / uploaded data")
    uploaded_csvs = st.file_uploader(
        "Load FIRMS CSV snapshot(s)",
        type=["csv"],
        accept_multiple_files=True,
        help="You can upload MODIS and VIIRS CSVs together. If a NASA FIRMS key is configured, TerraPulse can also fetch selected live sources that are not already represented in the uploaded files.",
    )
    historical_csv = st.file_uploader("Add historical FIRMS CSV archive (optional)", type=["csv"], key="historical_csv", help="Add an older FIRMS download to explore longer-term patterns. It is kept separate from live NRT data conceptually, but normalized for analysis.")
    habitat_geojson = st.file_uploader("Add habitat / protected-area GeoJSON (optional)", type=["geojson", "json"], key="habitat_geojson", help="A polygon boundary file. TerraPulse checks whether detections fall inside mapped areas; this is potential exposure, not proof of ecological damage.")
    vegetation_csv = st.file_uploader("Add vegetation-index CSV (optional)", type=["csv"], key="vegetation_csv", help="CSV should contain a date column and an NDVI column. Optional latitude/longitude columns allow site-specific filtering.")
    use_included_sample = st.checkbox(
        "Use included sample snapshot (10 Nov 2026)",
        value=False,
        help="This is a saved example, not live data.",
    )
    st.markdown('<div class="tp-rule"></div>', unsafe_allow_html=True)
    st.markdown("### Data notes")
    st.markdown(
        '<div class="tp-muted">FIRMS detections are thermal anomalies, not proof of a wildfire. '
        'Sensor confidence definitions differ. Cloud cover, observation timing, product latency, '
        'and spatial resolution affect what satellites observe.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="tp-muted">Basemaps: Esri World Imagery, Street Map and Topographic services. Fire observations: NASA FIRMS. '
        'The globe currently uses an ellipsoid, not high-resolution terrain.</div>',
        unsafe_allow_html=True,
    )


# ------------------------------ Header ------------------------------

st.markdown('<div class="tp-eyebrow">SATELLITE OBSERVATIONS / ENVIRONMENTAL INTELLIGENCE</div>', unsafe_allow_html=True)
st.markdown('<div class="tp-hero">Explore the living planet.</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="tp-subtitle">Explore Earth through NASA satellite observations. Compare MODIS and VIIRS evidence, investigate thermal anomalies across space and time, and connect observations to ecosystem context.</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="tp-rule"></div>', unsafe_allow_html=True)

# ------------------------------ Load data ------------------------------

frames = []
source_errors = []
source_status = []
data_mode_parts = []

# Load every supplied snapshot. Multiple files allow a MODIS archive and a
# VIIRS archive to be explored together without one replacing the other.
uploaded_sources = set()
if uploaded_csvs:
    for uploaded_file in uploaded_csvs:
        try:
            uploaded_file.seek(0)
            part = normalize_uploaded_csv(uploaded_file)
            if not part.empty:
                frames.append(part)
                uploaded_sources.update(part["sensor_source"].dropna().astype(str).unique())
                source_status.append(f"{uploaded_file.name}: loaded {len(part):,} rows")
            else:
                source_status.append(f"{uploaded_file.name}: file contained no observations")
        except Exception as exc:
            source_errors.append(f"{uploaded_file.name}: could not read CSV ({exc})")
    if frames:
        data_mode_parts.append("uploaded FIRMS snapshot(s)")

# The included sample is a MODIS-era example snapshot. It can coexist with
# live VIIRS feeds, but users are warned that the dates may not overlap.
if use_included_sample:
    sample_path = Path(__file__).resolve().parent / "sample_data" / "terrapulse_firms_20261110_1443UTC.csv"
    try:
        sample_raw = pd.read_csv(sample_path)
        sample_part = normalize_columns(sample_raw, infer_source(sample_raw))
        if not sample_part.empty:
            frames.append(sample_part)
            uploaded_sources.update(sample_part["sensor_source"].dropna().astype(str).unique())
            data_mode_parts.append("included sample snapshot")
            source_status.append(f"Included sample: loaded {len(sample_part):,} rows")
    except Exception as exc:
        source_errors.append(f"Included sample could not be loaded: {exc}")

# Fetch selected live sources that are not already present in uploaded data.
# This is the key fix: uploading a MODIS CSV no longer prevents VIIRS from
# being fetched from FIRMS in the same run.
selected_sources = [SENSORS[label] for label in selected_labels]
missing_live_sources = [source for source in selected_sources if source not in uploaded_sources]

if api_key and missing_live_sources:
    progress = st.progress(0, text="Connecting to NASA FIRMS…")
    for index, source in enumerate(missing_live_sources, start=1):
        try:
            part = fetch_source(api_key, source, days)
            if not part.empty:
                frames.append(part)
                source_status.append(f"{source}: loaded {len(part):,} live observations")
            else:
                source_status.append(f"{source}: NASA FIRMS returned zero observations for this window")
        except requests.RequestException as exc:
            source_errors.append(f"{source}: network/API request failed ({exc})")
        except Exception as exc:
            source_errors.append(f"{source}: {exc}")
        progress.progress(index / len(missing_live_sources), text=f"Loading {source}…")
    progress.empty()
    data_mode_parts.append("NASA FIRMS near-real-time")
elif not api_key and missing_live_sources:
    source_status.append(
        "Live sources not fetched: add a NASA FIRMS MAP_KEY or upload CSV files for the selected sensors."
    )

if not frames and historical_csv is None:
    st.info(
        "Add your NASA FIRMS key in `.streamlit/secrets.toml`, upload one or more FIRMS CSVs, "
        "or select the included sample snapshot in the sidebar to preview the globe."
    )
    st.markdown(
        "To configure live data, create `.streamlit/secrets.toml` and add "
        '`FIRMS_MAP_KEY = "your_private_key"`. '
        "The selected MODIS and VIIRS sources will then be requested separately."
    )
    st.stop()

data_mode = " + ".join(dict.fromkeys(data_mode_parts)) or "Historical FIRMS archive"

if source_status:
    with st.expander("Data-source loading report", expanded=bool(source_errors)):
        for status in source_status:
            st.write("• " + status)

# Add an optional historical FIRMS archive without replacing the live or snapshot data.
if historical_csv is not None:
    try:
        historical_csv.seek(0)
        historical_part = normalize_uploaded_csv(historical_csv)
        if not historical_part.empty:
            historical_part["dataset_period"] = "Uploaded historical archive"
            frames.append(historical_part)
            data_mode = (data_mode + " + historical archive").strip(" +")
    except Exception as exc:
        st.warning(f"Historical archive could not be added: {exc}")

if source_errors:
    with st.expander("Some NASA FIRMS sources could not be loaded"):
        for error in source_errors:
            st.warning(error)

if not frames or all(frame.empty for frame in frames):
    st.error(
        "No detections were loaded. Check the NASA FIRMS key and connection, or upload a saved FIRMS CSV snapshot."
    )
    st.stop()

fires = pd.concat(frames, ignore_index=True)
fires = fires.drop_duplicates(
    subset=["latitude", "longitude", "acq_date", "acq_time_display", "satellite", "sensor_source"],
    keep="first",
)

loaded_sources = sorted(fires["sensor_source"].dropna().astype(str).unique())
loaded_families = set()
for loaded_source in loaded_sources:
    if loaded_source.upper().startswith("MODIS"):
        loaded_families.add("MODIS")
    elif loaded_source.upper().startswith("VIIRS"):
        loaded_families.add("VIIRS")

if loaded_families == {"MODIS"}:
    st.warning(
        "Only MODIS observations are currently loaded. Keep NOAA-20 and NOAA-21 VIIRS selected, "
        "check the Data-source loading report, and confirm your NASA FIRMS MAP_KEY is configured."
    )
elif loaded_families == {"VIIRS"}:
    st.info("VIIRS observations are loaded, but no MODIS observations are present for cross-sensor comparison.")
elif loaded_families == {"MODIS", "VIIRS"}:
    st.success("Both MODIS and VIIRS observations are loaded. Cross-sensor analysis is available for overlapping acquisition times.")

filtered = fires.copy()
filtered = filtered[
    filtered["confidence_score_display"].isna()
    | (filtered["confidence_score_display"] >= confidence_threshold)
]
if daynight_choice != "All":
    filtered = filtered[filtered["daynight"] == daynight_choice]
if min_frp_filter > 0:
    filtered = filtered[pd.to_numeric(filtered["frp"], errors="coerce").fillna(-1) >= min_frp_filter]

# ------------------------------ Summary ------------------------------

total_loaded = len(fires)
total_filtered = len(filtered)
high_conf = int((filtered["confidence_score_display"] >= 80).sum())
sources_present = filtered["sensor_source"].nunique()
latest_obs = filtered["acq_date"].max()
latest_text = latest_obs.strftime("%d %b %Y") if pd.notna(latest_obs) else "Not available"

st.markdown(
    f'<span class="tp-tag">{html.escape(data_mode.upper())}</span> '
    f'<span class="tp-tag">{len(filtered):,} FILTERED OBSERVATIONS</span>',
    unsafe_allow_html=True,
)
m1, m2, m3, m4 = st.columns(4)
metrics = [
    (m1, "VISIBLE DETECTIONS", f"{total_filtered:,}", f"{total_loaded:,} loaded before filters"),
    (m2, "HIGH DISPLAY SCORE", f"{high_conf:,}", "Score ≥ 80; not a cross-sensor class"),
    (m3, "SOURCES PRESENT", str(sources_present), "In the loaded dataset"),
    (m4, "LATEST ACQUISITION", latest_text, f"Window: {days} day(s) for live data"),
]
for col, label, value, note in metrics:
    with col:
        st.markdown(
            f'<div class="tp-card"><div class="tp-card-label">{label}</div>'
            f'<div class="tp-card-value">{value}</div><div class="tp-card-note">{note}</div></div>',
            unsafe_allow_html=True,
        )

# ------------------------------ Main experience ------------------------------

explore_tab, analyze_tab, understand_tab, field_tab = st.tabs(
    ["EXPLORE", "ANALYZE", "ECOSYSTEMS", "FIELD GUIDE"]
)

with explore_tab:
    st.markdown('<div class="tp-section">Earth Explorer</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="tp-muted">Rotate the globe, zoom into landscapes, and select a marker to inspect its FIRMS record. '
        'Use the coordinate search in the globe to fly to a location.</div>',
        unsafe_allow_html=True,
    )
    if filtered.empty:
        st.info("No observations match the current filters.")
    else:
        globe_html = make_cesium_html(filtered)
        components.html(globe_html, height=690, scrolling=False)
        st.caption(
            "Orange markers represent MODIS observations; cyan markers represent VIIRS observations. "
            "Marker locations are detection coordinates, not fire perimeters. The globe may sample markers for browser performance; summary counts and CSV exports use the full filtered dataset."
        )

with analyze_tab:
    st.markdown('<div class="tp-section">Fire intelligence</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="tp-muted">Explore the measurements available in the currently loaded observation window. '
        'Near-real-time FIRMS data is not a long-term historical archive.</div>',
        unsafe_allow_html=True,
    )
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.markdown("**Detections by satellite source**")
        source_counts = filtered["sensor_source"].value_counts()
        st.bar_chart(source_counts)
    with chart_right:
        st.markdown("**Daily detection counts**")
        dated = filtered.dropna(subset=["acq_date"]).copy()
        if not dated.empty:
            daily_counts = dated.groupby(dated["acq_date"].dt.date).size()
            st.line_chart(daily_counts)
        else:
            st.info("Acquisition dates are unavailable in this dataset.")

    st.markdown('<div class="tp-rule"></div>', unsafe_allow_html=True)
    st.markdown("**Fire Radiative Power (FRP)**")
    frp_data = pd.to_numeric(filtered.get("frp"), errors="coerce").dropna()
    if not frp_data.empty:
        a, b, c = st.columns(3)
        a.metric("Records with FRP", f"{len(frp_data):,}")
        b.metric("Median FRP", f"{frp_data.median():.2f} MW")
        c.metric("Maximum FRP", f"{frp_data.max():.2f} MW")
        st.caption(
            "FRP is the rate of radiant energy emitted by the detected fire pixel, expressed in megawatts. "
            "It is not flame temperature, burned area, or a direct measure of ecological damage."
        )
    else:
        st.info("FRP values are not available in the currently loaded records.")

    st.markdown('<div class="tp-rule"></div>', unsafe_allow_html=True)
    st.markdown("**Cross-sensor detection matching**")
    st.caption("TerraPulse searches for VIIRS detections with a nearby MODIS observation inside the selected distance and acquisition-time windows. One MODIS observation may correspond to several finer-resolution VIIRS detections.")
    match_col1, match_col2 = st.columns(2)
    with match_col1:
        match_km = st.slider("Maximum spatial separation (km)", 0.5, 20.0, 5.0, 0.5, key="match_km")
    with match_col2:
        match_minutes = st.slider("Maximum acquisition-time difference (minutes)", 5, 180, 60, 5, key="match_minutes")

    matching_input = filtered.dropna(subset=["latitude", "longitude", "acq_date"]).copy()
    families_here = set(matching_input["sensor_source"].map(_family_label).unique())
    if not {"MODIS", "VIIRS"}.issubset(families_here):
        st.info("Load both MODIS and VIIRS observations with acquisition dates to run cross-sensor matching. Upload both FIRMS CSVs or enable live MODIS and NOAA-20/NOAA-21 VIIRS sources.")
    else:
        match_df, modis_n, viirs_n, was_sampled = match_modis_viirs(
            matching_input,
            radius_km=match_km,
            time_window_minutes=match_minutes,
            max_per_sensor=3000,
        )
        if was_sampled:
            st.warning("For performance, a reproducible sample of up to 3,000 observations per sensor family was compared. The correspondence rate below applies to this sample, not the complete dataset.")

        matched_viirs = len(match_df)
        correspondence_rate = (matched_viirs / viirs_n * 100) if viirs_n else 0.0
        metric_a, metric_b, metric_c, metric_d = st.columns(4)
        metric_a.metric("MODIS observations compared", f"{modis_n:,}")
        metric_b.metric("VIIRS observations compared", f"{viirs_n:,}")
        metric_c.metric("VIIRS with MODIS candidate", f"{matched_viirs:,}")
        metric_d.metric("VIIRS correspondence rate", f"{correspondence_rate:.1f}%")

        st.caption("This is a directional candidate-correspondence rate: the share of compared VIIRS observations with at least one MODIS observation inside the chosen thresholds. It is not sensor accuracy, fire-count agreement, or proof of a shared fire event.")

        if not match_df.empty:
            left, right = st.columns(2)
            with left:
                st.metric("Median spatial separation", f"{match_df['Distance (km)'].median():.2f} km")
            with right:
                st.metric("Median time difference", f"{match_df['Time difference (min)'].median():.1f} min")

            st.markdown("**Candidate correspondences**")
            st.dataframe(match_df.head(150), use_container_width=True, hide_index=True)
            st.download_button(
                "Download cross-sensor matching results",
                match_df.to_csv(index=False).encode("utf-8"),
                "terrapulse_cross_sensor_matches.csv",
                "text/csv",
                key="download_cross_sensor_matches",
            )
        else:
            st.info("No candidate correspondences met both thresholds. Try a wider spatial or temporal window. A non-match does not mean that a fire was absent.")

    st.markdown('<div class="tp-rule"></div>', unsafe_allow_html=True)
    st.markdown("**Try an investigation**")
    question = st.selectbox("What would you like to find out?", ["Which satellite source contributed the most observations?", "What does the FRP distribution look like?", "How did detections change over the selected dates?", "Which observations have the highest FRP?"])
    if question.startswith("Which satellite"):
        st.write("**What the data says:**")
        st.dataframe(filtered["sensor_source"].value_counts().rename("Observations").reset_index().rename(columns={"index":"Satellite source"}), hide_index=True, use_container_width=True)
        st.caption("A larger count can reflect instrument characteristics, coverage, overpass timing, and detection sensitivity — not necessarily more fires.")
    elif question.startswith("What does"):
        if not frp_data.empty:
            st.bar_chart(frp_data.clip(upper=frp_data.quantile(.98)).value_counts(bins=12).sort_index())
            st.caption("The chart groups FRP values into ranges. Very large outliers are clipped in this view for readability; the underlying records are unchanged.")
        else:
            st.info("FRP is not available in this dataset.")
    elif question.startswith("How did"):
        if not dated.empty:
            st.line_chart(dated.groupby(dated["acq_date"].dt.date).size())
            st.caption("These are detection records per acquisition date, not counts of unique fires.")
    else:
        top = filtered.assign(frp_num=pd.to_numeric(filtered["frp"], errors="coerce")).nlargest(10, "frp_num")
        st.dataframe(top[["acq_date", "sensor_source", "latitude", "longitude", "frp"]], hide_index=True, use_container_width=True)
        st.caption("High FRP indicates a higher measured rate of radiant energy from that detected pixel at observation time. It is not a direct measure of fire size or damage.")

with understand_tab:
    st.markdown('<div class="tp-section">Ecosystem context explorer</div>', unsafe_allow_html=True)
    st.markdown('<div class="tp-muted">Connect fire observations to mapped habitats and vegetation measurements. These layers add context; they do not prove ecological damage or recovery on their own.</div>', unsafe_allow_html=True)
    st.markdown("### Wildlife habitat / protected-area overlap")
    if habitat_geojson is not None:
        try:
            geo = json.load(habitat_geojson)
            features = geo.get("features", []) if geo.get("type") == "FeatureCollection" else [{"type":"Feature", "geometry":geo, "properties":{}}]
            if shape is None:
                st.warning("Install Shapely to calculate polygon overlap. The uploaded file was received, but no spatial result was calculated.")
            else:
                polygons = []
                for feature in features:
                    geom = feature.get("geometry")
                    if geom:
                        props = feature.get("properties") or {}
                        polygons.append((str(props.get("name") or props.get("NAME") or props.get("species") or "Mapped habitat"), shape(geom)))
                overlap_rows = []
                for _, obs in filtered.iterrows():
                    point = Point(float(obs["longitude"]), float(obs["latitude"]))
                    for name, polygon in polygons:
                        if polygon.is_valid and polygon.intersects(point):
                            overlap_rows.append({"Mapped area":name, "Date":str(obs["acq_date"].date()) if pd.notna(obs["acq_date"]) else "Unknown", "Satellite":obs["sensor_source"], "Latitude":obs["latitude"], "Longitude":obs["longitude"], "FRP (MW)":safe_float(obs,"frp")})
                overlap_df = pd.DataFrame(overlap_rows)
                st.metric("Observations inside mapped polygons", f"{len(overlap_df):,}")
                if not overlap_df.empty:
                    st.dataframe(overlap_df.head(200), use_container_width=True, hide_index=True)
                    st.download_button("Download habitat overlap results", overlap_df.to_csv(index=False).encode("utf-8"), "terrapulse_habitat_exposure_screen.csv", "text/csv")
                else:
                    st.info("No loaded observation points fell inside the uploaded polygons. This does not rule out exposure nearby or at another time.")
                st.caption(f"Checked {len(filtered):,} observations against {len(polygons):,} mapped polygons. Point-in-polygon is a screening test, not a wildlife-impact assessment.")
        except Exception as exc:
            st.error(f"Could not process this GeoJSON: {exc}")
    else:
        st.info("Add a habitat or protected-area GeoJSON file in the sidebar to activate the spatial overlap explorer.")

    st.markdown('<div class="tp-rule"></div>', unsafe_allow_html=True)
    st.markdown("### Vegetation change viewer")
    if vegetation_csv is not None:
        try:
            veg = pd.read_csv(vegetation_csv)
            lower = {c.lower():c for c in veg.columns}
            date_col = next((lower[c] for c in ["date", "acq_date", "time", "timestamp"] if c in lower), None)
            ndvi_col = next((lower[c] for c in ["ndvi", "mean_ndvi", "value"] if c in lower), None)
            if not date_col or not ndvi_col:
                st.warning("The vegetation CSV needs a date column and an NDVI column. Example headers: date, NDVI.")
            else:
                veg[date_col] = pd.to_datetime(veg[date_col], errors="coerce")
                veg[ndvi_col] = pd.to_numeric(veg[ndvi_col], errors="coerce")
                veg = veg.dropna(subset=[date_col, ndvi_col]).sort_values(date_col)
                if not veg.empty:
                    st.line_chart(veg.set_index(date_col)[ndvi_col])
                    before = st.date_input("Choose a baseline date", value=veg[date_col].min().date(), key="veg_before")
                    after = st.date_input("Choose a comparison date", value=veg[date_col].max().date(), key="veg_after")
                    bvals = veg.loc[veg[date_col].dt.date == before, ndvi_col]
                    avals = veg.loc[veg[date_col].dt.date == after, ndvi_col]
                    if not bvals.empty and not avals.empty:
                        delta = float(avals.mean() - bvals.mean())
                        st.metric("NDVI difference (comparison − baseline)", f"{delta:+.3f}")
                        st.caption("NDVI is a vegetation greenness index. A change can be influenced by season, rainfall, clouds, sensor/product differences, and land management; it is not proof of fire-caused damage or recovery.")
                    else:
                        st.info("Choose dates that exist in the uploaded dataset to calculate a comparison.")
        except Exception as exc:
            st.error(f"Could not read the vegetation CSV: {exc}")
    else:
        st.info("Add a vegetation-index CSV in the sidebar to activate the time-series and before/after comparison.")

    st.markdown('<div class="tp-rule"></div>', unsafe_allow_html=True)
    st.markdown("### Historical activity and recurrence")
    if historical_csv is not None and filtered["acq_date"].notna().any():
        hist = filtered.dropna(subset=["acq_date"]).copy()
        hist["Month"] = hist["acq_date"].dt.to_period("M").astype(str)
        st.bar_chart(hist.groupby("Month").size())
        st.caption("Monthly detection counts are a first-look pattern, not a count of unique fire events. A rigorous recurrence analysis needs a defined event-separation rule and ideally burned-area or perimeter data.")
    else:
        st.info("Upload a historical FIRMS archive to explore longer-term monthly activity. The live near-real-time feed alone is not a multi-year archive.")

with field_tab:
    st.markdown('<div class="tp-section">TerraPulse field guide</div>', unsafe_allow_html=True)
    st.write("No remote-sensing background required. Select a term to get a plain-language explanation and learn what it can — and cannot — tell you.")
    glossary = {
        "Active-fire detection": ("A satellite sensor noticed an unusually hot signal in a pixel at the time it passed overhead.", "It is evidence of a thermal anomaly, not automatic proof of a wildfire or its exact boundary."),
        "MODIS": ("An instrument carried on NASA's Terra and Aqua satellites. Its active-fire product has a nominal pixel size around 1 km.", "A pixel is an observation footprint, not a precise outline of flames."),
        "VIIRS": ("An instrument carried on Suomi-NPP, NOAA-20 and NOAA-21. Its active-fire product has a nominal 375 m pixel size.", "Smaller pixels can reveal more spatial detail, but do not guarantee that every fire is detected."),
        "FRP — Fire Radiative Power": ("An estimate of how quickly radiant energy is being released by the detected fire pixel, usually shown in megawatts (MW).", "It is not flame temperature, burned area, total energy, or a direct damage score."),
        "Confidence": ("A product-specific indicator about the confidence of a detection. Different sensors may use different scales or categories.", "Do not compare raw MODIS and VIIRS confidence values as if they were one universal score."),
        "NDVI": ("A satellite-derived index that uses red and near-infrared light to estimate vegetation greenness.", "It is affected by season, clouds, soil, water, and vegetation type; it does not identify the cause of change."),
        "NBR / dNBR": ("Indices using near- and shortwave-infrared reflectance, often used to study burned areas and change before versus after an event.", "The calculation, sign convention, product, and date selection must be stated."),
        "Habitat exposure": ("A map-based screen showing that an observation is near or inside a mapped habitat boundary.", "It does not establish that animals were present, injured, displaced, or killed."),
        "Recurrence": ("A way to study whether an area experiences separate fire events over time.", "Repeated satellite detections are not automatically separate fires; event rules and burned-area data matter."),
    }
    term = st.selectbox("Choose a concept", list(glossary.keys()))
    st.markdown(f"### {term}")
    st.success(glossary[term][0])
    st.warning("**Important limitation:** " + glossary[term][1])
    st.markdown('<div class="tp-rule"></div>', unsafe_allow_html=True)
    st.markdown("### Follow a simple investigation")
    stage = st.radio("What are you trying to understand?", ["I found a bright marker", "Two satellites show nearby detections", "I want to know whether vegetation changed", "I want to understand possible habitat exposure"], horizontal=False)
    explanations = {
        "I found a bright marker": "Open its details. Check the satellite, acquisition time, FRP, confidence field, and source. Then compare with imagery and other evidence. Brightness on the map is a display aid, not a fire-severity verdict.",
        "Two satellites show nearby detections": "Check the time difference and distance. Different instruments have different pixel sizes and overpass times. A spatial-temporal match is a lead for investigation, not independent ground confirmation.",
        "I want to know whether vegetation changed": "Compare the same location across appropriate pre- and post-event dates. Account for season, clouds, sensor/product differences, and use a documented index such as NDVI or NBR.",
        "I want to understand possible habitat exposure": "Overlay observations with a dated, authoritative habitat boundary. Distance or overlap can prioritize investigation, but ecological impact requires species and field evidence."
    }
    st.info(explanations[stage])
    st.markdown("### Where TerraPulse gets its information")
    st.markdown("""- **NASA FIRMS:** active-fire / thermal-anomaly observations.
- **NASA Worldview:** satellite imagery context.
- **Uploaded archives and context layers:** optional user-supplied historical observations, vegetation indices, and GeoJSON habitat boundaries.

TerraPulse is an exploration and learning tool, not an emergency warning or operational fire-response system.""")

# ------------------------------ Detection records ------------------------------

st.markdown('<div class="tp-rule"></div>', unsafe_allow_html=True)
with st.expander("Open detection explorer & observation records", expanded=False):
    if filtered.empty:
        st.info("No detection to inspect.")
    else:
        options_df = filtered.reset_index(drop=True).copy()
        options_df["choice"] = options_df.apply(
            lambda r: (
                f"{r['acq_date'].strftime('%Y-%m-%d') if pd.notna(r['acq_date']) else 'Date unknown'} · "
                f"{float(r['latitude']):.3f}, {float(r['longitude']):.3f} · {r['sensor_source']}"
            ), axis=1,
        )
        chosen_label = st.selectbox(
            "Choose a detection", options_df["choice"].tolist(), label_visibility="collapsed"
        )
        row = options_df.loc[options_df["choice"] == chosen_label].iloc[0]
        d1, d2, d3 = st.columns(3)
        d1.metric("Original confidence", str(row["confidence_original"]))
        frp_value = safe_float(row, "frp")
        d2.metric("FRP", f"{frp_value:.2f} MW" if frp_value is not None else "—")
        bright = safe_float(row, "thermal_brightness_k")
        d3.metric("Thermal brightness", f"{bright:.2f} K" if bright is not None else "—")
        st.write(
            f"**Coordinates:** {float(row['latitude']):.5f}, {float(row['longitude']):.5f}  \n"
            f"**Source:** {row['sensor_source']}  \n"
            f"**Acquisition:** {row['acq_date'].strftime('%Y-%m-%d') if pd.notna(row['acq_date']) else 'Not supplied'} · {row['acq_time_display']}"
        )
        if st.button("Load NASA Worldview satellite context"):
            if pd.isna(row["acq_date"]):
                st.warning("This record has no valid acquisition date.")
            else:
                with st.spinner("Requesting NASA Worldview imagery…"):
                    try:
                        image_url = get_worldview_snapshot_url(
                            float(row["latitude"]), float(row["longitude"]), row["acq_date"].date()
                        )
                        response = requests.get(image_url, timeout=35)
                        response.raise_for_status()
                        if "image" not in response.headers.get("content-type", ""):
                            raise RuntimeError("Worldview did not return an image.")
                        st.image(
                            response.content,
                            caption=(
                                f"NASA Worldview / MODIS Terra true-color context · "
                                f"{row['acq_date'].date()}. Regional imagery is not confirmation "
                                "that flames are visible at the detection point."
                            ),
                            use_container_width=True,
                        )
                    except Exception as exc:
                        st.warning(f"Worldview imagery could not be loaded: {exc}")
                        st.markdown("[Open NASA Worldview](https://worldview.earthdata.nasa.gov/)")

        st.markdown(
            f"[Open coordinates in OpenStreetMap](https://www.openstreetmap.org/?mlat={float(row['latitude'])}&mlon={float(row['longitude'])}#map=8/{float(row['latitude'])}/{float(row['longitude'])})"
        )

    st.markdown('<div class="tp-rule"></div>', unsafe_allow_html=True)
    st.markdown("**Observation records**")
    st.markdown(
        '<div class="tp-muted">The table uses all filtered records. The display score is an approximate shared filter '
        'for VIIRS categories and MODIS numeric confidence; original confidence values are preserved.</div>',
        unsafe_allow_html=True,
    )
    display_columns = [
        "acq_date", "acq_time_display", "sensor_source", "satellite",
        "latitude", "longitude", "confidence_original", "confidence_score_display",
        "thermal_brightness_k", "brightness_field", "frp", "daynight",
    ]
    available_columns = [c for c in display_columns if c in filtered.columns]
    table_df = filtered[available_columns].copy().rename(columns={
        "acq_date": "Acquisition date", "acq_time_display": "Acquisition time",
        "sensor_source": "FIRMS source", "satellite": "Satellite",
        "latitude": "Latitude", "longitude": "Longitude",
        "confidence_original": "Original confidence",
        "confidence_score_display": "Display score (approx.)",
        "thermal_brightness_k": "Thermal brightness (K)",
        "brightness_field": "Brightness source field", "frp": "FRP (MW)",
        "daynight": "Day/night",
    })
    st.dataframe(table_df.head(1000), use_container_width=True, height=350)
    if len(table_df) > 1000:
        st.caption(f"Showing first 1,000 of {len(table_df):,} records. CSV export includes all filtered records.")
    csv_bytes = table_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered observations (CSV)",
        data=csv_bytes,
        file_name=f"terrapulse_firms_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%MUTC')}.csv",
        mime="text/csv",
    )

st.markdown('<div class="tp-rule"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="tp-muted">Fire observations: NASA FIRMS Near Real-Time active-fire products. '
    'Globe imagery: Esri World Imagery. Satellite context: NASA Worldview / GIBS. '
    'FIRMS detections indicate satellite-observed thermal anomalies; they do not independently establish '
    'fire cause, severity, or ground conditions. The globe currently uses an ellipsoid without high-resolution terrain.</div>',
    unsafe_allow_html=True,
)
import streamlit as st
NASA_FIRMS_MAP_KEY = st.secrets["FIRMS_MAP_KEY"]
