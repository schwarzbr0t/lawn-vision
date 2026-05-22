/**
 * Lawn Vision custom Lovelace card.
 *
 * Single-file vanilla web component (no build step, no dependencies).
 * Renders the Lawn Vision dashboard from the integration's sensors.
 */

const CARD_VERSION = "2.0.0";

const DEFAULT_CONFIG = {
  title: "Lawn Vision",
  entity_phase: "sensor.lawn_vision_phase",
  entity_growth: "sensor.lawn_vision_growth_score",
  entity_soil_temperature: "sensor.lawn_vision_soil_temperature",
  entity_mean_daily_temperature: "sensor.lawn_vision_mean_daily_temperature",
  entity_grassland_temperature_sum: "sensor.lawn_vision_grassland_temperature_sum",
  entity_growing_degree_days: "sensor.lawn_vision_growing_degree_days",
  entity_moisture_10cm: "sensor.lawn_vision_moisture_10cm",
  entity_moisture_20cm: "sensor.lawn_vision_moisture_20cm",
  entity_moisture_30cm: "sensor.lawn_vision_moisture_30cm",
  entity_mowing: "sensor.lawn_vision_mowing_condition",
  entity_water: "sensor.lawn_vision_water_need",
  entity_stress: "sensor.lawn_vision_stress_level",
  entity_recommendation: "sensor.lawn_vision_recommendation",
  entity_forecast_slot_24h: "sensor.lawn_vision_forecast_slot_24h",
  entity_forecast_slot_48h: "sensor.lawn_vision_forecast_slot_48h",
  entity_forecast_slot_3d: "sensor.lawn_vision_forecast_slot_3d",
  entity_forecast_rain_risk: "sensor.lawn_vision_forecast_rain_risk",
  entity_forecast_water_need: "sensor.lawn_vision_forecast_water_need",
  history_days: 14,
};

const PHASE_LABELS = {
  dormant: "Ruhephase",
  stress: "Stress",
  dry: "Trocken",
  active_growth: "Aktives Wachstum",
  waking_up: "Wachstumsstart",
  slow_growth: "Langsames Wachstum",
};

const PHASE_HEADLINES = {
  dormant: { h: "Rasen ruht", s: "Pflege niedrig halten, Boden nicht belasten." },
  stress: { h: "Rasen schonen", s: "Stress hoch — Bewässerung priorisieren, Pflege verschieben." },
  dry: { h: "Wasser einplanen", s: "Bodenfeuchte niedrig — bald tief wässern." },
  active_growth: { h: "Voll im Wachstum", s: "Regelmäßig mähen, Nährstoffe im Blick behalten." },
  waking_up: { h: "Aufwachen", s: "Wachstum startet — leichte Pflege ist ok." },
  slow_growth: { h: "Langsam aufbauen", s: "Wachstum zieht an, Pflegefenster planen." },
};

const FORECAST_GROWTH_LABELS = {
  rising: "steigend",
  slight: "leicht",
  stable: "stabil",
  falling: "fallend",
  unknown: "unbekannt",
};

const FORECAST_STRESS_LABELS = {
  low: "niedrig",
  mid: "mittel",
  high: "hoch",
};

const FORECAST_ACTION_LABELS = {
  mow_possible: "Mähen möglich",
  observe: "Beobachten",
  wait: "Warten",
  wait_rain: "Regen abwarten",
  stress_recovery: "Erst erholen lassen",
};

const REASON_LABELS = {
  growth_moderate: "Wachstum noch moderat",
  growth_active: "Wachstum aktiv",
  rain_rising: "Regenwahrscheinlichkeit steigt",
  water_needed: "Bewässerung sinnvoll",
  dry_ahead: "Nächste Tage trocken",
  stress_low: "Stress niedrig",
  stress_mid: "Stress moderat",
  stress_high: "Stress hoch",
  moisture_ok: "Bodenfeuchte ausreichend",
  moisture_low: "Bodenfeuchte niedrig",
  moisture_unknown: "Bodenfeuchte unbekannt",
};

const SLOT_TITLES = { 24: "+24h", 48: "+48h", 72: "+3T" };

const ALLOWED_ACTION_CODES = new Set(Object.keys(FORECAST_ACTION_LABELS));
const ALLOWED_GROWTH_CODES = new Set(Object.keys(FORECAST_GROWTH_LABELS));
const ALLOWED_STRESS_CODES = new Set(Object.keys(FORECAST_STRESS_LABELS));

const ICONS = {
  grass: '<path d="M12 21V8"/><path d="M5 21h14"/><path d="M12 14c-4.5 0-7-2.8-7-7 4.5 0 7 2.8 7 7Z"/><path d="M12 11c4.5 0 7-2.8 7-7-4.5 0-7 2.8-7 7Z"/>',
  mow: '<path d="M3 20c9-1 15-7 18-17C11 5 4 10 3 20Z"/><path d="M3 20c5-6 10-9 16-12"/>',
  water: '<path d="M12 3s7 8 7 13a7 7 0 0 1-14 0c0-5 7-13 7-13Z"/>',
  stress: '<path d="M12 3 20 6v6c0 5-3.4 8.2-8 9-4.6-.8-8-4-8-9V6l8-3Z"/>',
  soil: '<path d="M14 14.76V5a4 4 0 0 0-8 0v9.76a6 6 0 1 0 8 0Z"/><path d="M10 5v11"/><path d="M18 7h2M18 11h3M18 15h2"/>',
  mean: '<path d="M14 14.76V5a4 4 0 0 0-8 0v9.76a6 6 0 1 0 8 0Z"/><path d="M10 5v11"/>',
  sigma: '<path d="M18 4H8l6 8-6 8h10"/>',
  gdd: '<path d="M4 20V5"/><path d="M4 20h17"/><path d="M7 17c3-8 7-10 12-10"/><path d="M16 7h3v3"/>',
  sun: '<path d="M12 3v2M5.6 5.6 7 7M3 12h2M18.4 5.6 17 7"/><path d="M17.5 19H8a5 5 0 1 1 .5-9.97A6 6 0 0 1 20 11a4 4 0 0 1-2.5 8Z"/>',
  rain: '<path d="M17.5 15H8a5 5 0 1 1 .5-9.97A6 6 0 0 1 20 7.5 4 4 0 0 1 17.5 15Z"/><path d="M8 19v1M12 19v1M16 19v1"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16 9"/>',
  clipboard: '<path d="M8 4h8l1 3H7l1-3Z"/><path d="M7 6H5v15h14V6h-2"/><path d="M8 12h8M8 16h5"/>',
};

const CARD_CSS = `
  :host{display:block;}
  *{box-sizing:border-box;}
  .dashboard{
    color:#f4f7f2;
    font-family: var(--primary-font-family, "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
    border-radius: var(--ha-card-border-radius, 24px);
    padding: 28px;
    background:
      radial-gradient(circle at 76% 5%, rgba(142, 175, 64, 0.22), transparent 38%),
      radial-gradient(circle at 16% 18%, rgba(47, 91, 63, 0.25), transparent 36%),
      linear-gradient(160deg, rgba(20, 47, 39, 0.92), rgba(2, 17, 22, 0.96) 54%, rgba(3, 16, 20, 0.98));
    border: 1px solid rgba(147, 180, 160, 0.22);
    box-shadow: 0 32px 90px rgba(0,0,0,0.42);
    position: relative;
    overflow: hidden;
  }
  .header{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;margin-bottom:32px;flex-wrap:wrap;}
  .eyebrow{color:#aeb9bc;font-weight:800;letter-spacing:0.02em;font-size:16px;margin-bottom:8px;}
  h1{margin:0;font-size:34px;line-height:1;letter-spacing:-0.04em;}
  .status-pill{display:inline-flex;align-items:center;gap:12px;padding:14px 22px;border-radius:999px;background:rgba(110,132,91,0.42);border:2px solid rgba(221,239,202,0.18);color:#e7ecd9;font-weight:800;font-size:16px;box-shadow:inset 0 1px 18px rgba(255,255,255,0.04);}
  .status-pill svg{color:#a7d84f;}
  .hero{display:grid;grid-template-columns:170px 1fr;gap:36px;align-items:center;margin-bottom:24px;}
  .gauge{width:170px;height:170px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(#a7d84f var(--ring-deg,68deg), rgba(136,159,137,0.32) var(--ring-deg,68deg) 360deg);position:relative;box-shadow:0 18px 40px rgba(0,0,0,0.34), inset 0 0 0 1px rgba(255,255,255,0.04);}
  .gauge::before{content:"";width:132px;height:132px;border-radius:50%;background:#07161c;box-shadow:inset 0 18px 34px rgba(0,0,0,0.38);position:absolute;}
  .gauge-value{position:relative;text-align:center;font-weight:900;}
  .gauge-value strong{display:block;font-size:54px;line-height:0.92;letter-spacing:-0.06em;}
  .gauge-value span{display:block;margin-top:6px;font-size:18px;color:#aeb9bc;font-weight:800;}
  .hero h2{margin:0 0 10px;font-size:30px;line-height:1.1;letter-spacing:-0.03em;}
  .hero p{margin:0;color:#c4cbcc;font-size:18px;line-height:1.4;font-weight:600;}
  .cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:14px;}
  .panel{background:linear-gradient(160deg, rgba(8,34,39,0.88), rgba(8,23,27,0.88));border:1px solid rgba(151,184,180,0.18);border-radius:18px;box-shadow:inset 0 1px 0 rgba(255,255,255,0.025), 0 18px 30px rgba(0,0,0,0.14);}
  .card{padding:20px 20px;min-height:150px;}
  .card-head{display:flex;align-items:center;gap:10px;color:#aeb9bc;font-size:13px;font-weight:900;margin-bottom:16px;text-transform:uppercase;letter-spacing:0.04em;}
  .card-head svg{width:24px;height:24px;}
  .card-value{font-size:24px;font-weight:900;letter-spacing:-0.03em;margin-bottom:6px;}
  .card-copy{color:#c0c8ca;font-size:14px;line-height:1.3;}
  .metrics{display:grid;grid-template-columns:repeat(4,1fr);overflow:hidden;margin-bottom:14px;border-radius:16px;}
  .metric{display:flex;align-items:center;gap:12px;padding:18px 18px;min-height:80px;border-right:1px solid rgba(170,201,197,0.16);}
  .metric:last-child{border-right:0;}
  .metric svg{color:#a7d84f;flex:0 0 auto;width:26px;height:26px;}
  .metric-label{color:#aeb9bc;font-size:13px;font-weight:800;margin-bottom:2px;}
  .metric-value{font-size:20px;font-weight:900;letter-spacing:-0.02em;}
  .section-title{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:6px 2px 14px;}
  .section-title h3{margin:0;font-size:20px;letter-spacing:-0.03em;}
  .tabs{display:inline-grid;grid-template-columns:repeat(3,1fr);width:200px;border-radius:10px;border:1px solid rgba(180,201,195,0.14);overflow:hidden;background:rgba(255,255,255,0.025);}
  .tab{padding:7px 0;text-align:center;color:#aeb9bc;font-weight:900;font-size:13px;cursor:pointer;}
  .tab.active{background:rgba(139,169,87,0.62);color:#f7f9ef;box-shadow:inset 0 0 20px rgba(255,255,255,0.06);}
  .history{padding:18px 18px 12px;margin-bottom:14px;}
  .chart-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:0;border:1px solid rgba(172,196,191,0.13);border-radius:14px;overflow:hidden;background:rgba(4,21,24,0.42);}
  .chart-card{padding:16px 14px 12px;border-right:1px solid rgba(172,196,191,0.13);min-height:170px;}
  .chart-card:last-child{border-right:0;}
  .chart-label{display:flex;gap:10px;align-items:center;margin-bottom:8px;}
  .chart-label svg{width:24px;height:24px;}
  .chart-label strong{font-size:15px;color:#a7d84f;}
  .chart-label .blue{color:#58b7f5;}
  .chart-label .yellow{color:#f2d33c;}
  .chart-label span{display:block;color:#aeb9bc;font-size:12px;margin-top:2px;}
  .mini-chart{width:100%;height:96px;overflow:visible;}
  .axis-label{font-size:10px;fill:#aeb9bc;}
  .grid-line{stroke:rgba(174,185,188,0.12);stroke-width:1;}
  .moisture{padding:18px 20px 18px;margin-bottom:14px;}
  .moisture .section-title{margin-bottom:8px;}
  .unit{color:#778489;font-size:13px;font-weight:900;}
  .moisture-row{display:grid;grid-template-columns:64px 1fr 50px;gap:16px;align-items:center;min-height:34px;color:#dbe3e3;font-weight:800;font-size:14px;}
  .bar{height:12px;border-radius:999px;background:rgba(172,190,188,0.18);overflow:hidden;}
  .bar span{display:block;height:100%;background:linear-gradient(90deg,#a7d84f, rgba(159,204,86,0.78));border-radius:inherit;box-shadow:0 0 24px rgba(160,214,79,0.2);}
  .forecast{padding:20px;margin-bottom:14px;}
  .forecast h3{margin:0 0 4px;font-size:20px;letter-spacing:-0.03em;}
  .forecast-subline{margin:0 0 18px;color:#aeb9bc;font-size:14px;font-weight:700;}
  .outlook-timeline{position:relative;display:grid;grid-template-columns:repeat(3,1fr);gap:14px;padding-top:28px;}
  .outlook-timeline::before{content:"";position:absolute;top:38px;left:16%;right:16%;height:3px;border-radius:999px;background:linear-gradient(90deg, rgba(167,216,79,0.42), rgba(88,183,245,0.48), rgba(167,216,79,0.82));box-shadow:0 0 24px rgba(167,216,79,0.14);}
  .outlook-step{position:relative;min-height:220px;padding:28px 14px 14px;border-radius:14px;background:linear-gradient(160deg, rgba(11,39,43,0.78), rgba(7,24,29,0.78));border:1px solid rgba(174,196,190,0.16);box-shadow:inset 0 1px 0 rgba(255,255,255,0.025);}
  .outlook-step.active{border-color:rgba(167,216,79,0.42);background:linear-gradient(160deg, rgba(31,62,43,0.86), rgba(8,31,35,0.86));}
  .outlook-step.rain .outlook-node{border-color:rgba(88,183,245,0.86);box-shadow:0 0 0 6px rgba(88,183,245,0.1), 0 0 22px rgba(88,183,245,0.2);}
  .outlook-step.wait .outlook-node{border-color:rgba(242,211,60,0.86);box-shadow:0 0 0 6px rgba(242,211,60,0.1), 0 0 22px rgba(242,211,60,0.2);}
  .outlook-node{position:absolute;top:-3px;left:50%;transform:translateX(-50%);width:28px;height:28px;border-radius:50%;background:#07161c;border:3px solid rgba(167,216,79,0.78);box-shadow:0 0 0 6px rgba(167,216,79,0.1), 0 0 22px rgba(167,216,79,0.22);z-index:2;}
  .outlook-time{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:12px;}
  .outlook-time strong{font-size:20px;letter-spacing:-0.03em;}
  .outlook-time svg{width:30px;height:30px;}
  .outlook-action{min-height:46px;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid rgba(180,199,195,0.09);}
  .outlook-action span{display:block;color:#aeb9bc;font-size:11px;font-weight:900;letter-spacing:0.05em;text-transform:uppercase;margin-bottom:4px;}
  .outlook-action b{display:block;color:#f4f7f2;font-size:17px;line-height:1.15;letter-spacing:-0.02em;}
  .signal-list{display:grid;gap:8px;}
  .signal{display:grid;grid-template-columns:18px 1fr auto;align-items:center;gap:8px;color:#cad4d4;font-size:13px;}
  .signal b{color:#f4f6ee;font-size:13px;white-space:nowrap;}
  .signal .green{color:#a7d84f;}
  .signal .blue{color:#58b7f5;}
  .signal .yellow{color:#f2d33c;}
  .outlook-score{margin-top:12px;padding-top:11px;border-top:1px solid rgba(180,199,195,0.09);}
  .score-label{display:flex;justify-content:space-between;color:#aeb9bc;font-size:11px;font-weight:900;margin-bottom:6px;}
  .score-track{height:6px;border-radius:999px;background:rgba(172,190,188,0.15);overflow:hidden;}
  .score-track span{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg, rgba(167,216,79,0.55), #a7d84f);}
  .recommendation{display:grid;grid-template-columns:78px 1fr;gap:20px;padding:24px 22px 20px;background:linear-gradient(160deg, rgba(45,79,43,0.92), rgba(20,54,35,0.88));border-color:rgba(169,214,139,0.28);}
  .recommendation-icon{width:72px;height:72px;border-radius:50%;display:grid;place-items:center;background:rgba(136,180,75,0.28);border:1px solid rgba(190,223,112,0.28);color:#a7d84f;box-shadow:inset 0 0 26px rgba(255,255,255,0.05), 0 12px 30px rgba(0,0,0,0.18);}
  .recommendation-icon svg{width:36px;height:36px;}
  .recommendation h3{margin:0 0 6px;font-size:22px;letter-spacing:-0.03em;}
  .recommendation p{margin:0;color:#e0e5df;font-size:17px;line-height:1.35;}
  .why{margin-top:16px;padding-top:16px;border-top:1px solid rgba(180,221,93,0.35);display:grid;grid-template-columns:84px 1fr 1fr;gap:10px 20px;align-items:start;}
  .why-title{color:#a7d84f;font-size:16px;font-weight:900;}
  .reason{display:flex;align-items:center;gap:10px;color:#e2e8df;font-size:14px;font-weight:700;margin-bottom:10px;}
  .reason svg{color:#a7d84f;flex:0 0 auto;width:18px;height:18px;}
  .reason.off{opacity:0.45;}
  svg{stroke-linecap:round;stroke-linejoin:round;}

  @media (max-width: 740px){
    .dashboard{padding:18px;}
    .hero{grid-template-columns:1fr;gap:18px;}
    .cards,.chart-grid,.metrics,.outlook-timeline{grid-template-columns:1fr;}
    .outlook-timeline::before{display:none;}
    .chart-card,.metric{border-right:0;border-bottom:1px solid rgba(172,196,191,0.13);}
    .chart-card:last-child,.metric:last-child{border-bottom:0;}
    .recommendation,.why{grid-template-columns:1fr;}
    .header{flex-direction:column;}
    .status-pill{width:100%;justify-content:center;}
  }
`;

class LawnVisionCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._config = null;
    this._historyDays = 14;
    this._history = { growth: [], water: [], stress: [] };
    this._historyTimer = null;
    this._lastHistoryFetch = 0;
  }

  static getStubConfig() {
    return { ...DEFAULT_CONFIG };
  }

  setConfig(config) {
    this._config = { ...DEFAULT_CONFIG, ...(config || {}) };
    this._historyDays = Number(this._config.history_days) || 14;
    this._render();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) {
      this._fetchHistory();
    } else if (Date.now() - this._lastHistoryFetch > 5 * 60 * 1000) {
      this._fetchHistory();
    }
    this._render();
  }

  getCardSize() {
    return 14;
  }

  /* ---------- data helpers ---------- */

  _state(entityId) {
    if (!entityId) return null;
    return this._hass?.states?.[entityId] ?? null;
  }

  _num(entityId, digits = 1) {
    const s = this._state(entityId);
    if (!s) return null;
    const n = Number(s.state);
    if (!isFinite(n)) return null;
    return digits === null ? n : Number(n.toFixed(digits));
  }

  _attr(entityId, key) {
    const s = this._state(entityId);
    return s?.attributes?.[key] ?? null;
  }

  _formatNum(value, digits = 1, fallback = "--") {
    if (value === null || value === undefined || !isFinite(value)) return fallback;
    return Number(value).toFixed(digits).replace(/\.0+$/, "");
  }

  /* ---------- history via websocket ---------- */

  async _fetchHistory() {
    if (!this._hass || !this._config) return;
    this._lastHistoryFetch = Date.now();
    const days = this._historyDays;
    const end = new Date();
    const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);
    const ids = [
      this._config.entity_growth,
      this._config.entity_water,
      this._config.entity_stress,
    ].filter(Boolean);
    if (ids.length === 0) return;
    try {
      const result = await this._hass.callWS({
        type: "history/history_during_period",
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        entity_ids: ids,
        minimal_response: true,
        no_attributes: true,
      });
      const series = (key, eid) => {
        const arr = (result && result[eid]) || [];
        return arr
          .map((p) => ({
            t: new Date(p.lu ? p.lu * 1000 : p.last_updated || p.last_changed).getTime(),
            v: Number(p.s !== undefined ? p.s : p.state),
          }))
          .filter((p) => isFinite(p.v));
      };
      this._history = {
        growth: series("growth", this._config.entity_growth),
        water: series("water", this._config.entity_water),
        stress: series("stress", this._config.entity_stress),
      };
      this._render();
    } catch (err) {
      console.warn("[lawn-vision-card] history fetch failed", err);
    }
  }

  /* ---------- render ---------- */

  _render() {
    if (!this.shadowRoot || !this._config) return;

    const phaseState = this._state(this._config.entity_phase);
    const phaseCode = phaseState ? phaseState.state : "slow_growth";
    const phaseLabel = PHASE_LABELS[phaseCode] || phaseCode || "—";
    const headline = PHASE_HEADLINES[phaseCode] || PHASE_HEADLINES.slow_growth;

    const growth = this._num(this._config.entity_growth, 0);
    const ringDeg = growth !== null ? Math.max(0, Math.min(360, (growth / 100) * 360)) : 0;

    const soilT = this._num(this._config.entity_soil_temperature, 1);
    const meanT = this._num(this._config.entity_mean_daily_temperature, 1);
    const gts = this._num(this._config.entity_grassland_temperature_sum, 0);
    const gdd = this._num(this._config.entity_growing_degree_days, 1);
    const m10 = this._num(this._config.entity_moisture_10cm, 2);
    const m20 = this._num(this._config.entity_moisture_20cm, 2);
    const m30 = this._num(this._config.entity_moisture_30cm, 2);
    const mowing = this._state(this._config.entity_mowing);
    const mowingV = mowing ? Number(mowing.state) : null;
    const water = this._num(this._config.entity_water, 1);
    const stress = this._num(this._config.entity_stress, 0);

    const recState = this._state(this._config.entity_recommendation);
    const recText = recState ? recState.state : "";
    const reasons = (recState && recState.attributes && Array.isArray(recState.attributes.reasons))
      ? recState.attributes.reasons : [];

    const html = `
      <style>${CARD_CSS}</style>
      <div class="dashboard">
        ${this._renderHeader(phaseLabel)}
        ${this._renderHero(growth, ringDeg, headline)}
        ${this._renderKpis(mowing, mowingV, water, stress)}
        ${this._renderMetrics(soilT, meanT, gts, gdd)}
        ${this._renderHistory()}
        ${this._renderMoisture(m10, m20, m30)}
        ${this._renderForecast()}
        ${this._renderRecommendation(recText, reasons)}
      </div>
    `;

    this.shadowRoot.innerHTML = html;
    this._bindTabs();
  }

  _renderHeader(phaseLabel) {
    return `
      <header class="header">
        <div>
          <div class="eyebrow">RASENSTATUS</div>
          <h1>${this._escape(this._config.title || "Lawn Vision")}</h1>
        </div>
        <div class="status-pill">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3">${ICONS.grass}</svg>
          ${this._escape(phaseLabel)}
        </div>
      </header>`;
  }

  _renderHero(growth, ringDeg, headline) {
    const growthDisplay = growth === null ? "--" : growth;
    return `
      <section class="hero">
        <div class="gauge" style="--ring-deg:${ringDeg}deg">
          <div class="gauge-value">
            <strong>${growthDisplay}</strong>
            <span>%</span>
          </div>
        </div>
        <div>
          <h2>${this._escape(headline.h)}</h2>
          <p>${this._escape(headline.s)}</p>
        </div>
      </section>`;
  }

  _renderKpis(mowing, mowingV, water, stress) {
    const mowText = this._mowingCopy(mowingV);
    return `
      <section class="cards">
        <article class="panel card">
          <div class="card-head"><svg viewBox="0 0 24 24" fill="none" stroke="#f2d33c" stroke-width="2.2">${ICONS.mow}</svg>MÄHEN</div>
          <div class="card-value">${this._escape(mowText.value)}</div>
          <div class="card-copy">${this._escape(mowText.copy)}</div>
        </article>
        <article class="panel card">
          <div class="card-head"><svg viewBox="0 0 24 24" fill="none" stroke="#a7d84f" stroke-width="2.2">${ICONS.water}</svg>WASSER</div>
          <div class="card-value">${this._formatNum(water, 1)} mm / 48h</div>
          <div class="card-copy">${water !== null && water > 3 ? "Bewässerung sinnvoll." : "Regen wahrscheinlich."}</div>
        </article>
        <article class="panel card">
          <div class="card-head"><svg viewBox="0 0 24 24" fill="none" stroke="#a7d84f" stroke-width="2.2">${ICONS.stress}</svg>STRESS</div>
          <div class="card-value">${stress === null ? "--" : stress} %</div>
          <div class="card-copy">${this._stressCopy(stress)}</div>
        </article>
      </section>`;
  }

  _mowingCopy(mowingV) {
    if (mowingV === null || !isFinite(mowingV)) return { value: "--", copy: "Keine Daten." };
    if (mowingV >= 70) return { value: "Jetzt", copy: "Gutes Mähfenster." };
    if (mowingV >= 45) return { value: "In 2 Tagen", copy: "Wachstum noch moderat." };
    if (mowingV >= 25) return { value: "Bald", copy: "Bedingungen brauchbar." };
    return { value: "Warten", copy: "Wachstum noch zu langsam." };
  }

  _stressCopy(stress) {
    if (stress === null) return "Keine Daten.";
    if (stress >= 65) return "Hohe Belastung.";
    if (stress >= 35) return "Moderate Belastung.";
    return "Niedrige Belastung.";
  }

  _renderMetrics(soilT, meanT, gts, gdd) {
    return `
      <section class="panel metrics">
        <div class="metric">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">${ICONS.soil}</svg>
          <div><div class="metric-label">Boden</div><div class="metric-value">${this._formatNum(soilT, 1)} °C</div></div>
        </div>
        <div class="metric">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">${ICONS.mean}</svg>
          <div><div class="metric-label">Tagesmittel</div><div class="metric-value">${this._formatNum(meanT, 1)} °C</div></div>
        </div>
        <div class="metric">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">${ICONS.sigma}</svg>
          <div><div class="metric-label">GTS</div><div class="metric-value">${this._formatNum(gts, 0)} K</div></div>
        </div>
        <div class="metric">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">${ICONS.gdd}</svg>
          <div><div class="metric-label">GDD</div><div class="metric-value">${this._formatNum(gdd, 1)}</div></div>
        </div>
      </section>`;
  }

  _renderHistory() {
    const days = this._historyDays;
    const periods = [
      { d: 7, label: "7T" },
      { d: 14, label: "14T" },
      { d: 30, label: "30T" },
    ];
    const tabs = periods
      .map((p) => `<span class="tab${p.d === days ? " active" : ""}" data-days="${p.d}">${p.label}</span>`)
      .join("");
    return `
      <section class="panel history">
        <div class="section-title">
          <h3>Verlauf ${days} Tage</h3>
          <div class="tabs">${tabs}</div>
        </div>
        <div class="chart-grid">
          ${this._renderMiniLine("Wachstum", this._history.growth, "#a7d84f", true)}
          ${this._renderMiniBars("Wasser", this._history.water, "#58b7f5")}
          ${this._renderMiniLine("Stress", this._history.stress, "#f2d33c", true, true)}
        </div>
      </section>`;
  }

  _renderMiniLine(title, points, color, withLevels, isStress) {
    const icon = isStress ? ICONS.stress : ICONS.mow;
    const colorClass = color === "#a7d84f" ? "" : (color === "#58b7f5" ? "blue" : "yellow");
    if (!points || points.length < 2) {
      return `
        <article class="chart-card">
          <div class="chart-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2.2">${icon}</svg>
            <div><strong${colorClass ? " class=\"" + colorClass + "\"" : ""}>${title}</strong><span>letzte ${this._historyDays} Tage</span></div>
          </div>
          <svg class="mini-chart" viewBox="0 0 250 120"><text class="axis-label" x="55" y="60">Daten werden geladen…</text></svg>
        </article>`;
    }
    const { path, area, dots, axis } = this._buildLineChart(points, withLevels);
    return `
      <article class="chart-card">
        <div class="chart-label">
          <svg viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2.2">${icon}</svg>
          <div><strong${colorClass ? " class=\"" + colorClass + "\"" : ""}>${title}</strong><span>letzte ${this._historyDays} Tage</span></div>
        </div>
        <svg class="mini-chart" viewBox="0 0 250 120">
          ${withLevels ? `
            <line class="grid-line" x1="45" y1="25" x2="240" y2="25"/>
            <line class="grid-line" x1="45" y1="58" x2="240" y2="58"/>
            <line class="grid-line" x1="45" y1="90" x2="240" y2="90"/>
            <text class="axis-label" x="0" y="30">hoch</text>
            <text class="axis-label" x="0" y="63">mittel</text>
            <text class="axis-label" x="0" y="95">niedrig</text>` : ""}
          <path d="${area}" fill="${this._withAlpha(color, 0.13)}"/>
          <path d="${path}" fill="none" stroke="${color}" stroke-width="3"/>
          <g fill="${color}">${dots}</g>
          ${axis}
        </svg>
      </article>`;
  }

  _renderMiniBars(title, points, color) {
    if (!points || points.length === 0) {
      return `
        <article class="chart-card">
          <div class="chart-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2.2">${ICONS.water}</svg>
            <div><strong class="blue">${title}</strong><span>letzte ${this._historyDays} Tage</span></div>
          </div>
          <svg class="mini-chart" viewBox="0 0 250 120"><text class="axis-label" x="55" y="60">Daten werden geladen…</text></svg>
        </article>`;
    }
    const bars = this._buildBars(points);
    return `
      <article class="chart-card">
        <div class="chart-label">
          <svg viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2.2">${ICONS.water}</svg>
          <div><strong class="blue">${title}</strong><span>letzte ${this._historyDays} Tage</span></div>
        </div>
        <svg class="mini-chart" viewBox="0 0 250 120">
          <line class="grid-line" x1="22" y1="25" x2="240" y2="25"/>
          <line class="grid-line" x1="22" y1="58" x2="240" y2="58"/>
          <line class="grid-line" x1="22" y1="90" x2="240" y2="90"/>
          <g fill="${color}">${bars}</g>
          <text class="axis-label" x="22" y="118">-${this._historyDays}T</text>
          <text class="axis-label" x="202" y="118">Heute</text>
        </svg>
      </article>`;
  }

  _buildLineChart(points, withLevels) {
    const downsampled = this._downsample(points, 14);
    const xs = downsampled.map((p, i) => 50 + (i * (185 / Math.max(1, downsampled.length - 1))));
    const vs = downsampled.map((p) => p.v);
    const min = Math.min(...vs);
    const max = Math.max(...vs);
    const range = max - min < 1 ? 1 : (max - min);
    const yFor = (v) => 95 - ((v - min) / range) * 70;

    const points2 = downsampled.map((p, i) => [xs[i], yFor(p.v)]);
    const path = points2.map((p, i) => (i === 0 ? `M${p[0]} ${p[1]}` : `L${p[0]} ${p[1]}`)).join(" ");
    const last = points2[points2.length - 1];
    const first = points2[0];
    const area = `${path} L${last[0]} 103 L${first[0]} 103 Z`;
    const dots = points2.map((p) => `<circle cx="${p[0]}" cy="${p[1]}" r="3.2"/>`).join("");
    const axis = `
      <text class="axis-label" x="${withLevels ? 45 : 22}" y="118">-${this._historyDays}T</text>
      <text class="axis-label" x="205" y="118">Heute</text>`;
    return { path, area, dots, axis };
  }

  _buildBars(points) {
    const downsampled = this._downsample(points, 11);
    const max = Math.max(...downsampled.map((p) => p.v), 1);
    const slotWidth = (240 - 28) / downsampled.length;
    return downsampled
      .map((p, i) => {
        const height = Math.max(2, (p.v / max) * 66);
        const x = 28 + i * slotWidth;
        const y = 100 - height;
        return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${(slotWidth - 4).toFixed(1)}" height="${height.toFixed(1)}" rx="3"/>`;
      })
      .join("");
  }

  _downsample(points, n) {
    if (!points || points.length === 0) return [];
    if (points.length <= n) return points;
    const out = [];
    const step = points.length / n;
    for (let i = 0; i < n; i++) {
      const startIdx = Math.floor(i * step);
      const endIdx = Math.min(points.length, Math.floor((i + 1) * step));
      const slice = points.slice(startIdx, endIdx);
      if (slice.length === 0) continue;
      const avg = slice.reduce((s, p) => s + p.v, 0) / slice.length;
      out.push({ t: slice[slice.length - 1].t, v: avg });
    }
    return out;
  }

  _renderMoisture(m10, m20, m30) {
    const row = (depth, value) => {
      const pct = value === null ? 0 : Math.max(0, Math.min(100, (value / 0.45) * 100));
      return `<div class="moisture-row">
        <span>${depth}</span>
        <div class="bar"><span style="width:${pct.toFixed(1)}%"></span></div>
        <span>${this._formatNum(value, 2)}</span>
      </div>`;
    };
    return `
      <section class="panel moisture">
        <div class="section-title">
          <h3>Bodenfeuchte</h3>
          <span class="unit">Volumen m³/m³</span>
        </div>
        ${row("10 cm", m10)}
        ${row("20 cm", m20)}
        ${row("30 cm", m30)}
      </section>`;
  }

  _renderForecast() {
    const slots = [
      { eid: this._config.entity_forecast_slot_24h, hours: 24 },
      { eid: this._config.entity_forecast_slot_48h, hours: 48 },
      { eid: this._config.entity_forecast_slot_3d, hours: 72 },
    ];
    const steps = slots.map((s, idx) => this._renderForecastStep(s, idx === slots.length - 1)).join("");
    return `
      <section class="panel forecast">
        <h3>Ausblick</h3>
        <p class="forecast-subline">Kombinierte Zeitachse aus Wetter, Wachstum und empfohlener Aktion.</p>
        <div class="outlook-timeline">${steps}</div>
      </section>`;
  }

  _renderForecastStep(slot, isLast) {
    const st = this._state(slot.eid);
    const attrs = (st && st.attributes) || {};
    const hours = this._clampInt(attrs.hours, 1, 240, slot.hours);
    const rawState = st ? Number(st.state) : NaN;
    const suitability = isFinite(rawState) ? this._clampInt(rawState, 0, 100, 0) : 0;
    const actionCode = ALLOWED_ACTION_CODES.has(attrs.action_code) ? attrs.action_code : "";
    const action = actionCode
      ? (attrs.action_label || FORECAST_ACTION_LABELS[actionCode] || "—")
      : "—";
    const growthCode = ALLOWED_GROWTH_CODES.has(attrs.growth_code) ? attrs.growth_code : "unknown";
    const growth = attrs.growth_label || FORECAST_GROWTH_LABELS[growthCode] || "—";
    const stressCode = ALLOWED_STRESS_CODES.has(attrs.stress_code) ? attrs.stress_code : "low";
    const stress = attrs.stress_label || FORECAST_STRESS_LABELS[stressCode] || "—";
    const rainPct = this._clampInt(attrs.rain_pct, 0, 100, 0);

    const stepClass = ["outlook-step"];
    if (isLast && suitability >= 60) stepClass.push("active");
    if (actionCode === "wait_rain") stepClass.push("rain");
    if (actionCode === "wait" || actionCode === "stress_recovery") stepClass.push("wait");

    const iconKey = actionCode === "wait_rain" ? "rain" : "sun";
    const slotTitle = SLOT_TITLES[hours] || `+${hours}h`;

    return `
      <article class="${stepClass.join(" ")}">
        <span class="outlook-node"></span>
        <div class="outlook-time">
          <strong>${this._escape(slotTitle)}</strong>
          <svg viewBox="0 0 24 24" fill="none" stroke="#d6e8f7" stroke-width="2">${ICONS[iconKey]}</svg>
        </div>
        <div class="outlook-action"><span>Aktion</span><b>${this._escape(action)}</b></div>
        <div class="signal-list">
          <div class="signal"><span class="green">▥</span><span>Wuchs</span><b>${this._escape(growth)}</b></div>
          <div class="signal"><span class="blue">♢</span><span>Regen</span><b>${rainPct} %</b></div>
          <div class="signal"><span class="yellow">♢</span><span>Stress</span><b>${this._escape(stress)}</b></div>
        </div>
        <div class="outlook-score">
          <div class="score-label"><span>Eignung</span><b>${suitability}</b></div>
          <div class="score-track"><span style="width:${suitability}%"></span></div>
        </div>
      </article>`;
  }

  _clampInt(value, min, max, fallback) {
    const n = Number(value);
    if (!isFinite(n)) return fallback;
    return Math.max(min, Math.min(max, Math.round(n)));
  }

  _renderRecommendation(recText, reasons) {
    const reasonsHtml = reasons.length
      ? reasons.map((r) => {
          const label = r.label || REASON_LABELS[r.code] || r.code;
          const off = r.ok === false ? " off" : "";
          return `<div class="reason${off}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">${ICONS.check}</svg>${this._escape(label)}</div>`;
        }).join("")
      : `<div class="reason"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">${ICONS.check}</svg>Wachstum noch moderat</div>`;
    // split reasons into two columns
    const half = Math.ceil(reasons.length / 2) || 2;
    const left = reasons.slice(0, half).map((r) => this._reasonHtml(r)).join("") || reasonsHtml;
    const right = reasons.slice(half).map((r) => this._reasonHtml(r)).join("");

    return `
      <section class="panel recommendation">
        <div class="recommendation-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">${ICONS.clipboard}</svg>
        </div>
        <div>
          <h3>Empfehlung</h3>
          <p>${this._escape(recText || "Aktuell keine Empfehlung verfügbar.")}</p>
          <div class="why">
            <div class="why-title">Warum?</div>
            <div>${left}</div>
            <div>${right}</div>
          </div>
        </div>
      </section>`;
  }

  _reasonHtml(r) {
    const label = r.label || REASON_LABELS[r.code] || r.code;
    const off = r.ok === false ? " off" : "";
    return `<div class="reason${off}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">${ICONS.check}</svg>${this._escape(label)}</div>`;
  }

  /* ---------- interactions ---------- */

  _bindTabs() {
    const tabs = this.shadowRoot.querySelectorAll(".tab[data-days]");
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const d = Number(tab.getAttribute("data-days"));
        if (!d || d === this._historyDays) return;
        this._historyDays = d;
        this._lastHistoryFetch = 0;
        this._fetchHistory();
      });
    });
  }

  /* ---------- utilities ---------- */

  _withAlpha(hex, alpha) {
    const m = /^#([0-9a-f]{6})$/i.exec(hex);
    if (!m) return hex;
    const n = parseInt(m[1], 16);
    const r = (n >> 16) & 255;
    const g = (n >> 8) & 255;
    const b = n & 255;
    return `rgba(${r},${g},${b},${alpha})`;
  }

  _escape(s) {
    if (s === null || s === undefined) return "";
    return String(s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );
  }
}

if (!customElements.get("lawn-vision-card")) {
  customElements.define("lawn-vision-card", LawnVisionCard);
  console.info(`%c LAWN-VISION-CARD %c v${CARD_VERSION} `,
    "color:#07161c;background:#a7d84f;padding:2px 6px;border-radius:3px 0 0 3px;font-weight:700;",
    "color:#a7d84f;background:#07161c;padding:2px 6px;border-radius:0 3px 3px 0;");
}

window.customCards = window.customCards || [];
if (!window.customCards.find((c) => c.type === "lawn-vision-card")) {
  window.customCards.push({
    type: "lawn-vision-card",
    name: "Lawn Vision",
    description: "Dashboard card for the Lawn Vision integration.",
    preview: false,
  });
}
