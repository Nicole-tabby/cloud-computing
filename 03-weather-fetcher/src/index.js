/**
 * Weather Data Fetcher - Cloudflare Worker (Serverless / FaaS)
 * ================================================================
 * scheduled()  -> runs automatically once a day (see [triggers] in
 *                 wrangler.toml) for the DEFAULT location, stores a row in D1.
 * fetch()      -> serves a small web UI where a user can search ANY city:
 *                   GET /                      -> the search page (HTML)
 *                   GET /api/weather?city=...   -> geocodes the city, fetches
 *                                                  weather, stores it in D1,
 *                                                  returns JSON
 *                   GET /api/history            -> last 20 stored readings (JSON)
 *                   GET /run                    -> manually triggers the default
 *                                                  scheduled fetch (for testing)
 */

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(fetchAndStoreWeather(env, env.LOCATION_NAME, env.LOCATION_LAT, env.LOCATION_LON));
  },

  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/api/weather") {
      return handleCitySearch(url, env);
    }

    if (url.pathname === "/api/history") {
      const { results } = await env.DB.prepare(
        "SELECT * FROM weather_readings ORDER BY fetched_at DESC LIMIT 20"
      ).all();
      return jsonResponse(results);
    }

    if (url.pathname === "/run") {
      const result = await fetchAndStoreWeather(env, env.LOCATION_NAME, env.LOCATION_LAT, env.LOCATION_LON);
      return jsonResponse({ status: "ok", stored: result });
    }

    // Default: serve the search UI
    return new Response(HTML_PAGE, { headers: { "content-type": "text/html;charset=UTF-8" } });
  },
};

function jsonResponse(obj) {
  return new Response(JSON.stringify(obj, null, 2), {
    headers: { "content-type": "application/json" },
  });
}

/** Geocodes a city name, fetches its weather, stores it, returns the result. */
async function handleCitySearch(url, env) {
  const city = url.searchParams.get("city");
  if (!city) {
    return jsonResponse({ error: "Missing ?city= parameter" });
  }

  const geoRes = await fetch(
    `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1`
  );
  const geoData = await geoRes.json();

  if (!geoData.results || geoData.results.length === 0) {
    return jsonResponse({ error: `No location found for "${city}"` });
  }

  const place = geoData.results[0];
  const displayName = [place.name, place.admin1, place.country].filter(Boolean).join(", ");

  const stored = await fetchAndStoreWeather(env, displayName, place.latitude, place.longitude);
  return jsonResponse(stored);
}

/** Fetches current weather for given coordinates and inserts one row into D1. */
async function fetchAndStoreWeather(env, locationName, lat, lon) {
  const apiUrl =
    `https://api.open-meteo.com/v1/forecast` +
    `?latitude=${lat}&longitude=${lon}` +
    `&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code`;

  const res = await fetch(apiUrl);
  if (!res.ok) {
    throw new Error(`Weather API request failed: ${res.status}`);
  }
  const data = await res.json();
  const current = data.current;
  const fetchedAt = new Date().toISOString();

  await env.DB.prepare(
    `INSERT INTO weather_readings
       (location_name, latitude, longitude, temperature_c, humidity_pct, wind_speed_kmh, weather_code, fetched_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
  )
    .bind(
      locationName,
      Number(lat),
      Number(lon),
      current.temperature_2m,
      current.relative_humidity_2m,
      current.wind_speed_10m,
      current.weather_code,
      fetchedAt
    )
    .run();

  return {
    location: locationName,
    latitude: Number(lat),
    longitude: Number(lon),
    temperature_c: current.temperature_2m,
    humidity_pct: current.relative_humidity_2m,
    wind_speed_kmh: current.wind_speed_10m,
    weather_code: current.weather_code,
    fetched_at: fetchedAt,
  };
}

// Maps Open-Meteo's numeric weather_code to a short human description.
const WEATHER_CODE_MAP = {
  0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
  45: "Fog", 48: "Depositing rime fog",
  51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
  61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
  71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
  80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
  95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
};

const HTML_PAGE = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Weather Data Fetcher — 24UG00216</title>
<style>
  :root {
    --bg: #0f172a;
    --card: #1e293b;
    --accent: #38bdf8;
    --text: #f1f5f9;
    --muted: #94a3b8;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    min-height: 100vh;
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 48px 20px;
  }
  h1 { font-size: 1.5rem; margin: 0 0 4px; }
  .subtitle { color: var(--muted); margin: 0 0 32px; font-size: 0.9rem; }
  .search-box {
    display: flex;
    gap: 8px;
    width: 100%;
    max-width: 420px;
    margin-bottom: 28px;
  }
  input[type="text"] {
    flex: 1;
    padding: 12px 16px;
    border-radius: 10px;
    border: 1px solid #334155;
    background: var(--card);
    color: var(--text);
    font-size: 1rem;
  }
  input[type="text"]:focus { outline: 2px solid var(--accent); }
  button {
    padding: 12px 20px;
    border-radius: 10px;
    border: none;
    background: var(--accent);
    color: #0f172a;
    font-weight: 600;
    cursor: pointer;
    font-size: 1rem;
  }
  button:hover { opacity: 0.9; }
  button:disabled { opacity: 0.5; cursor: default; }
  .card {
    width: 100%;
    max-width: 420px;
    background: var(--card);
    border-radius: 16px;
    padding: 28px;
    display: none;
  }
  .card.visible { display: block; }
  .card .place { font-size: 1.2rem; font-weight: 600; }
  .card .temp { font-size: 3rem; font-weight: 700; margin: 8px 0; }
  .card .desc { color: var(--muted); margin-bottom: 16px; }
  .metrics { display: flex; gap: 24px; font-size: 0.9rem; color: var(--muted); }
  .metrics b { color: var(--text); }
  .error { color: #f87171; margin-top: 8px; }
  .history {
    width: 100%;
    max-width: 420px;
    margin-top: 32px;
  }
  .history h2 { font-size: 0.9rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .history-item {
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid #334155;
    font-size: 0.9rem;
  }
  .history-item .h-loc { color: var(--text); }
  .history-item .h-meta { color: var(--muted); }
</style>
</head>
<body>
  <h1>🌤️ Weather Data Fetcher</h1>
  <p class="subtitle">24UG00216 · Cloudflare Workers + D1</p>

  <div class="search-box">
    <input type="text" id="cityInput" placeholder="Enter any city, e.g. Tokyo" />
    <button id="searchBtn">Search</button>
  </div>

  <div class="card" id="resultCard">
    <div class="place" id="rPlace"></div>
    <div class="temp" id="rTemp"></div>
    <div class="desc" id="rDesc"></div>
    <div class="metrics">
      <div>💧 <b id="rHumidity"></b></div>
      <div>💨 <b id="rWind"></b></div>
    </div>
  </div>
  <div class="error" id="errorMsg"></div>

  <div class="history">
    <h2>Recently stored readings</h2>
    <div id="historyList"></div>
  </div>

<script>
  const WEATHER_DESC = ${JSON.stringify(WEATHER_CODE_MAP)};

  const input = document.getElementById("cityInput");
  const btn = document.getElementById("searchBtn");
  const card = document.getElementById("resultCard");
  const errorMsg = document.getElementById("errorMsg");

  async function search() {
    const city = input.value.trim();
    if (!city) return;
    errorMsg.textContent = "";
    btn.disabled = true;
    btn.textContent = "Searching...";
    try {
      const res = await fetch("/api/weather?city=" + encodeURIComponent(city));
      const data = await res.json();
      if (data.error) {
        errorMsg.textContent = data.error;
        card.classList.remove("visible");
      } else {
        document.getElementById("rPlace").textContent = data.location;
        document.getElementById("rTemp").textContent = data.temperature_c + "°C";
        document.getElementById("rDesc").textContent = WEATHER_DESC[data.weather_code] || "—";
        document.getElementById("rHumidity").textContent = data.humidity_pct + "%";
        document.getElementById("rWind").textContent = data.wind_speed_kmh + " km/h";
        card.classList.add("visible");
        loadHistory();
      }
    } catch (e) {
      errorMsg.textContent = "Something went wrong. Try again.";
    } finally {
      btn.disabled = false;
      btn.textContent = "Search";
    }
  }

  async function loadHistory() {
    const res = await fetch("/api/history");
    const rows = await res.json();
    const list = document.getElementById("historyList");
    list.innerHTML = rows.map(r =>
      '<div class="history-item"><span class="h-loc">' + r.location_name +
      '</span><span class="h-meta">' + r.temperature_c + '°C · ' +
      new Date(r.fetched_at).toLocaleString() + '</span></div>'
    ).join("");
  }

  btn.addEventListener("click", search);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") search(); });

  loadHistory();
</script>
</body>
</html>`;
