// ---------------------------------------------------------------------
// Geodesic Auth — frontend
// ---------------------------------------------------------------------

const MIN_POINTS = 3;
const MAX_POINTS = 6;

const state = {
  mode: "register",       // "register" | "login"
  points: [],              // [{lat, lng}]
  markers: [],              // real markers on the map
  decoyMarkers: [],
};

const map = L.map("map", { zoomControl: true }).setView([20, 0], 2.2);

L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
  attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
  maxZoom: 19,
}).addTo(map);

function realPointIcon(index) {
  return L.divIcon({
    className: "",
    html: `<div style="
      width:22px;height:22px;border-radius:50%;
      background:#C08A3E;border:2px solid #16232E;
      display:flex;align-items:center;justify-content:center;
      font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:600;
      color:#16232E;box-shadow:0 0 0 2px rgba(192,138,62,0.35);
    ">${index}</div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}

function decoyIcon() {
  return L.divIcon({
    className: "",
    html: `<div style="
      width:16px;height:16px;border-radius:50%;
      background:rgba(237,227,207,0.15);border:2px dashed rgba(237,227,207,0.4);
    "></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
}

// ---------------------------------------------------------------------
// Crosshair coordinate readout
// ---------------------------------------------------------------------

const crosshairEl = document.getElementById("crosshair-readout");
map.on("mousemove", (e) => {
  crosshairEl.querySelector(".crosshair-readout__lat").textContent =
    `LAT ${e.latlng.lat.toFixed(5)}`;
  crosshairEl.querySelector(".crosshair-readout__lng").textContent =
    `LNG ${e.latlng.lng.toFixed(5)}`;
});

// ---------------------------------------------------------------------
// Point list rendering
// ---------------------------------------------------------------------

const pointListEl = document.getElementById("point-list");
const undoBtn = document.getElementById("undo-btn");
const submitBtn = document.getElementById("submit-btn");

function renderPointList() {
  if (state.points.length === 0) {
    pointListEl.innerHTML = `<li class="readout__empty">No points selected yet</li>`;
  } else {
    pointListEl.innerHTML = state.points
      .map(
        (p, i) =>
          `<li><span class="pt-index">PT.${String(i + 1).padStart(2, "0")}</span> ${p.lat.toFixed(5)}, ${p.lng.toFixed(5)}</li>`
      )
      .join("");
  }
  undoBtn.disabled = state.points.length === 0;
  submitBtn.disabled = state.points.length < MIN_POINTS;
}

function addPoint(lat, lng) {
  if (state.points.length >= MAX_POINTS) {
    setStatus(`Maximum ${MAX_POINTS} points — undo one to add another.`, "error");
    return;
  }
  state.points.push({ lat, lng });

  const marker = L.marker([lat, lng], { icon: realPointIcon(state.points.length) }).addTo(map);
  state.markers.push(marker);

  renderPointList();
  refreshEntropy();
  setStatus("", "");
}

function undoLastPoint() {
  if (state.points.length === 0) return;
  state.points.pop();
  const marker = state.markers.pop();
  if (marker) map.removeLayer(marker);
  renderPointList();
  refreshEntropy();
}

function clearAllPoints() {
  state.points = [];
  state.markers.forEach((m) => map.removeLayer(m));
  state.markers = [];
  clearDecoys();
  renderPointList();
}

function clearDecoys() {
  state.decoyMarkers.forEach((m) => map.removeLayer(m));
  state.decoyMarkers = [];
  document.getElementById("decoy-note").classList.remove("is-visible");
}

function scatterDecoys() {
  clearDecoys();
  const bounds = map.getBounds();
  const count = 6 + Math.floor(Math.random() * 5);
  for (let i = 0; i < count; i++) {
    const lat = bounds.getSouth() + Math.random() * (bounds.getNorth() - bounds.getSouth());
    const lng = bounds.getWest() + Math.random() * (bounds.getEast() - bounds.getWest());
    const marker = L.marker([lat, lng], { icon: decoyIcon(), interactive: false }).addTo(map);
    state.decoyMarkers.push(marker);
  }
  document.getElementById("decoy-note").classList.add("is-visible");
}

map.on("click", (e) => addPoint(e.latlng.lat, e.latlng.lng));
undoBtn.addEventListener("click", undoLastPoint);

// ---------------------------------------------------------------------
// Mode switch
// ---------------------------------------------------------------------

document.querySelectorAll(".mode-switch__btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-switch__btn").forEach((b) => b.classList.remove("is-active"));
    btn.classList.add("is-active");
    state.mode = btn.dataset.mode;
    clearAllPoints();
    setStatus("", "");
    submitBtn.textContent = state.mode === "register" ? "Register sequence" : "Authenticate";

    if (state.mode === "login") {
      // Randomize center slightly + scatter decoys: shoulder-surfing mitigation.
      const c = map.getCenter();
      map.panTo([c.lat + (Math.random() - 0.5) * 0.02, c.lng + (Math.random() - 0.5) * 0.02], { animate: false });
      scatterDecoys();
      map.once("moveend", scatterDecoys);
    } else {
      clearDecoys();
    }
  });
});

// ---------------------------------------------------------------------
// Status + submit
// ---------------------------------------------------------------------

const statusEl = document.getElementById("status");
function setStatus(msg, kind) {
  statusEl.textContent = msg;
  statusEl.className = "status" + (kind ? ` is-${kind}` : "");
}

submitBtn.addEventListener("click", async () => {
  const username = document.getElementById("username").value.trim();
  if (!username) {
    setStatus("Enter a username first.", "error");
    return;
  }
  if (state.points.length < MIN_POINTS) {
    setStatus(`Select at least ${MIN_POINTS} points.`, "error");
    return;
  }

  submitBtn.disabled = true;
  setStatus("Working…", "");

  const endpoint = state.mode === "register" ? "/api/register" : "/api/login";
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, points: state.points }),
    });
    const data = await res.json();
    if (data.ok) {
      setStatus(data.message, "success");
      if (state.mode === "register") {
        setTimeout(() => document.querySelector('[data-mode="login"]').click(), 900);
      }
    } else {
      setStatus(data.error || "Something went wrong.", "error");
    }
  } catch (err) {
    setStatus("Network error — is the server running?", "error");
  } finally {
    submitBtn.disabled = state.points.length < MIN_POINTS;
  }
});

// ---------------------------------------------------------------------
// Entropy gauge
// ---------------------------------------------------------------------

const gaugeFill = document.getElementById("gauge-fill");
const gaugeNeedle = document.getElementById("gauge-needle");
const entropyBitsEl = document.getElementById("entropy-bits");
const equivLenEl = document.getElementById("equiv-len");

const GAUGE_ARC_LENGTH = 157;   // matches stroke-dasharray in CSS
const MAX_EXPECTED_BITS = 90;   // scale for the gauge sweep

async function refreshEntropy() {
  const bounds = map.getBounds();
  const params = new URLSearchParams({
    south: bounds.getSouth(),
    north: bounds.getNorth(),
    west: bounds.getWest(),
    east: bounds.getEast(),
    points: Math.max(state.points.length, MIN_POINTS),
  });
  try {
    const res = await fetch(`/api/entropy?${params}`);
    const data = await res.json();
    if (!data.ok) return;

    entropyBitsEl.textContent = data.entropy_bits;
    equivLenEl.textContent = data.equivalent_alnum_password_length;

    const frac = Math.min(1, data.entropy_bits / MAX_EXPECTED_BITS);
    gaugeFill.style.strokeDashoffset = GAUGE_ARC_LENGTH * (1 - frac);
    const angle = -90 + frac * 180;
    gaugeNeedle.style.transform = `rotate(${angle}deg)`;
  } catch (e) {
    // silent — teaching widget only
  }
}

map.on("moveend zoomend", refreshEntropy);
renderPointList();
refreshEntropy();