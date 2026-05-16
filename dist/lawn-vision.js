class LawnVisionCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity_growth) {
      throw new Error("entity_growth is required");
    }

    this.config = {
      title: "Lawn Vision",
      background_image: undefined,
      background_position: "center",
      background_size: "cover",
      layout: "auto",
      size: "normal",
      visual: {},
      show_agro: true,
      show_forecast: true,
      show_timeline: true,
      show_recommendation: true,
      show_care_guide: true,
      entity_phase: undefined,
      entity_soil_temperature: undefined,
      entity_mean_daily_temperature: undefined,
      entity_grassland_temperature_sum: undefined,
      entity_growing_degree_days: undefined,
      entity_moisture_10cm: undefined,
      entity_moisture_20cm: undefined,
      entity_moisture_30cm: undefined,
      entity_mowing: undefined,
      entity_water: undefined,
      entity_stress: undefined,
      entity_recommendation: undefined,
      entity_forecast_rain_risk: undefined,
      entity_forecast_water_need: undefined,
      entity_forecast_growth_trend: undefined,
      entity_forecast_best_window: undefined,
      entity_forecast_care_hint: undefined,
      entity_action_mow: undefined,
      entity_action_water: undefined,
      entity_action_fertilize: undefined,
      entity_action_scarify: undefined,
      entity_action_aerate: undefined,
      entity_action_overseed: undefined,
      entity_next_action: undefined,
      entity_care_plan_7d: undefined,
      show_care_plan_7d: true,
      ...config,
    };

    if (!this.card) {
      this.card = document.createElement("ha-card");
      this.card.className = "lawn-vision";
      this.root = document.createElement("div");
      this.root.className = "lawn-vision__root";
      this.styleEl = document.createElement("style");
      this.card.append(this.styleEl, this.root);
      this.appendChild(this.card);
      this.styleEl.textContent = this.styles();
      if ("ResizeObserver" in window) {
        this.resizeObserver = new ResizeObserver(() => this.updateSizeClass());
        this.resizeObserver.observe(this.card);
      }
    }
    this.updateSizeClass();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.config || !this.root) {
      return;
    }
    this.render();
  }

  getCardSize() {
    if (this.config?.size === "compact") {
      return 3;
    }
    if (this.config?.size === "large") {
      return 5;
    }
    return 4;
  }

  disconnectedCallback() {
    this.resizeObserver?.disconnect();
  }

  static getStubConfig() {
    return {
      type: "custom:lawn-vision-card",
      title: "Lawn Vision",
      background_image: "/local/community/lawn-vision/rasen.png",
      layout: "auto",
      size: "normal",
      show_care_guide: true,
      show_recommendation: false,
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
      entity_forecast_rain_risk: "sensor.lawn_vision_forecast_rain_risk",
      entity_forecast_water_need: "sensor.lawn_vision_forecast_water_need",
      entity_forecast_growth_trend: "sensor.lawn_vision_forecast_growth_trend",
      entity_forecast_best_window: "sensor.lawn_vision_forecast_best_window",
      entity_forecast_care_hint: "sensor.lawn_vision_forecast_care_hint",
      entity_action_mow: "sensor.lawn_vision_action_mow",
      entity_action_water: "sensor.lawn_vision_action_water",
      entity_action_fertilize: "sensor.lawn_vision_action_fertilize",
      entity_action_scarify: "sensor.lawn_vision_action_scarify",
      entity_action_aerate: "sensor.lawn_vision_action_aerate",
      entity_action_overseed: "sensor.lawn_vision_action_overseed",
      entity_next_action: "sensor.lawn_vision_next_action",
      entity_care_plan_7d: "sensor.lawn_vision_care_plan_7d",
    };
  }

  static getConfigElement() {
    return document.createElement("lawn-vision-card-editor");
  }

  render() {
    const growth = this.numberState(this.config.entity_growth);
    const mowing = this.numberState(this.config.entity_mowing);
    const water = this.numberState(this.config.entity_water);
    const stress = this.numberState(this.config.entity_stress);
    const soilTemperature = this.numberStateOrNull(this.config.entity_soil_temperature);
    const meanDailyTemperature = this.numberStateOrNull(
      this.config.entity_mean_daily_temperature
    );
    const grasslandTemperatureSum = this.numberStateOrNull(
      this.config.entity_grassland_temperature_sum
    );
    const growingDegreeDays = this.numberStateOrNull(
      this.config.entity_growing_degree_days
    );
    const moistureDepths = [
      { depth: "10 cm", value: this.numberStateOrNull(this.config.entity_moisture_10cm) },
      { depth: "20 cm", value: this.numberStateOrNull(this.config.entity_moisture_20cm) },
      { depth: "30 cm", value: this.numberStateOrNull(this.config.entity_moisture_30cm) },
    ];
    const phase = this.textState(this.config.entity_phase, "unknown");
    const forecastRainRisk = this.numberStateOrNull(this.config.entity_forecast_rain_risk);
    const forecastWaterNeed = this.numberStateOrNull(this.config.entity_forecast_water_need);
    const forecastGrowthTrend = this.textState(this.config.entity_forecast_growth_trend, "unknown");
    const forecastBestWindow = this.textState(this.config.entity_forecast_best_window, "--");
    const forecastCareHint = this.textState(this.config.entity_forecast_care_hint, "");
    const recommendation = this.textState(
      this.config.entity_recommendation,
      "Keine Empfehlung verfuegbar."
    );
    const tone = this.tone(growth, stress, phase);
    const plan = this.carePlan(mowing, water, stress);
    const timeline = this.timeline(mowing, water, stress);
    const showAgro = this.config.show_agro !== false;
    const showForecast = this.config.show_forecast !== false;
    const showTimeline = this.config.show_timeline !== false;
    const showRecommendation = this.config.show_recommendation !== false;
    const showCareGuide = this.config.show_care_guide !== false;
    const careGuide = this.careGuideData();
    const showCarePlan7d = this.config.show_care_plan_7d !== false;
    const carePlan7d = this.carePlan7dData();

    this.applyBackground();
    this.applyVisuals(tone);

    this.root.innerHTML = `
      <section class="scene scene--${tone}">
        <header class="topline">
          <div class="title">
            <span class="kicker">Rasenstatus</span>
            <h2>${this.escape(this.config.title)}</h2>
          </div>
          <div class="phase-pill">
            <ha-icon icon="${this.phaseIcon(phase)}"></ha-icon>
            <span>${this.escape(this.phaseLabel(phase))}</span>
          </div>
        </header>

        <section class="hero-grid">
          <div class="score-ring" style="--score:${growth}; --tone:${this.toneColor(tone)}">
            <span>${this.format(growth, "0")}</span>
            <small>%</small>
          </div>
          <div class="hero-copy">
            <strong>${this.escape(this.scoreHeadline(growth, stress, phase))}</strong>
            <span>${this.escape(this.scoreText(growth, stress))}</span>
          </div>
        </section>

        <section class="plan" aria-label="Pflegewerte">
          ${plan
            .map(
              (item) => `
                <article class="plan-item plan-item--${item.tone}">
                  <div class="plan-item__head">
                    <ha-icon icon="mdi:${item.icon}"></ha-icon>
                    <span>${this.escape(item.label)}</span>
                  </div>
                  <strong>${this.escape(item.value)}</strong>
                  <p>${this.escape(item.description)}</p>
                </article>
              `
            )
            .join("")}
        </section>

        ${showCarePlan7d && carePlan7d.days.length ? `
        <section class="care-plan-7d" aria-label="Pflegeplan 7 Tage">
          <header class="care-plan-7d__head">
            <span class="kicker">Pflegeplan</span>
            <strong>${carePlan7d.actionable} von ${carePlan7d.days.length} Tagen aktiv</strong>
          </header>
          <ol class="care-plan-7d__grid">
            ${carePlan7d.days.map((day) => `
              <li class="care-plan-day care-plan-day--${day.tone}">
                <span class="care-plan-day__label">${this.escape(day.day)}</span>
                <ha-icon icon="${day.icon}"></ha-icon>
                <strong>${this.escape(this.formatTempRange(day.temp_max, day.temp_min))}</strong>
                <em>${this.escape(day.hint)}</em>
                ${day.rain_probability ? `<small>${this.escape(`${day.rain_probability}%`)}</small>` : ""}
              </li>
            `).join("")}
          </ol>
        </section>` : ""}

        ${showCareGuide && (careGuide.headline || careGuide.items.length) ? `
        <section class="care-guide" aria-label="Pflegeguide">
          ${careGuide.headline ? `
            <div class="care-headline care-headline--${careGuide.headline.tone}">
              <ha-icon icon="${careGuide.headline.icon}"></ha-icon>
              <div>
                <span class="care-headline__kicker">Heute steht an</span>
                <strong>${this.escape(careGuide.headline.label)}</strong>
                ${careGuide.headline.window ? `<em>${this.escape(careGuide.headline.window)}</em>` : ""}
                ${careGuide.headline.reason ? `<p>${this.escape(careGuide.headline.reason)}</p>` : ""}
              </div>
            </div>
          ` : ""}
          ${careGuide.items.length ? `
            <ul class="care-list">
              ${careGuide.items.map((item) => `
                <li class="care-row care-row--${item.tone}">
                  <span class="care-row__icon"><ha-icon icon="${item.icon}"></ha-icon></span>
                  <div class="care-row__body">
                    <div class="care-row__head">
                      <strong>${this.escape(item.label)}</strong>
                      <span class="care-badge care-badge--${item.tone}">${this.escape(item.badge)}</span>
                    </div>
                    ${item.window ? `<em>${this.escape(item.window)}</em>` : ""}
                    ${item.reason ? `<p>${this.escape(item.reason)}</p>` : ""}
                  </div>
                </li>
              `).join("")}
            </ul>
          ` : ""}
        </section>` : ""}

        ${showAgro ? `<section class="agro-panel" aria-label="Agronomie">
          <div class="agro-grid">
            ${this.agroMetric("thermometer-lines", "Boden", soilTemperature, "C", 1)}
            ${this.agroMetric("thermometer-auto", "Tagesmittel", meanDailyTemperature, "C", 1)}
            ${this.agroMetric("sigma", "GTS", grasslandTemperatureSum, "K", 1)}
            ${this.agroMetric("chart-bell-curve-cumulative", "GDD", growingDegreeDays, "", 1)}
          </div>
          <div class="moisture-profile">
            <div class="moisture-profile__head">
              <span>Bodenfeuchte</span>
              <em>Volumen m3/m3</em>
            </div>
            ${moistureDepths.map((item) => this.moistureDepth(item)).join("")}
          </div>
        </section>` : ""}

        ${showForecast ? `<section class="forecast-panel" aria-label="Prognose">
          ${this.forecastMetric("calendar-clock", "Pflegefenster", forecastBestWindow)}
          ${this.forecastMetric("weather-pouring", "Regen", `${this.formatOptional(forecastRainRisk, 0)} %`)}
          ${this.forecastMetric("watering-can-outline", "Wasser 48h", `${this.formatOptional(forecastWaterNeed, 1)} mm`)}
          ${this.forecastMetric("trending-up", "Trend", this.trendLabel(forecastGrowthTrend))}
          ${forecastCareHint ? `<p>${this.escape(forecastCareHint)}</p>` : ""}
        </section>` : ""}

        ${showTimeline ? `<section class="horizon" aria-label="Pflegefenster">
          ${timeline
            .map(
              (item) => `
                <div class="horizon-step horizon-step--${item.tone}">
                  <span><ha-icon icon="mdi:check"></ha-icon></span>
                  <strong>${this.escape(item.day)}</strong>
                  <em>${this.escape(item.label)}</em>
                </div>
              `
            )
            .join("")}
        </section>` : ""}

        ${showRecommendation ? `<section class="recommendation">
          <ha-icon icon="mdi:clipboard-text-outline"></ha-icon>
          <div>
            <strong>Empfehlung</strong>
            <p>${this.escape(recommendation)}</p>
          </div>
        </section>` : ""}
      </section>
    `;
  }

  updateSizeClass() {
    if (!this.root || !this.card) {
      return;
    }

    const forcedLayout = this.config?.layout;
    const forcedSize = this.config?.size;
    const width = this.card.getBoundingClientRect().width || 0;
    let size = "wide";

    if (forcedLayout && forcedLayout !== "auto") {
      size = forcedLayout;
    } else if (forcedSize === "compact" || width < 420) {
      size = "compact";
    } else if (width < 680) {
      size = "medium";
    }

    this.root.dataset.size = size;
  }

  applyBackground() {
    const image = this.config.background_image;
    if (image) {
      const safeUrl = String(image).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
      this.root.style.setProperty("--lawn-bg", `url("${safeUrl}")`);
    } else {
      this.root.style.removeProperty("--lawn-bg");
    }

    this.root.style.setProperty(
      "--lawn-bg-position",
      this.config.background_position || "center"
    );
    this.root.style.setProperty(
      "--lawn-bg-size",
      this.config.background_size || "cover"
    );
  }

  applyVisuals(tone) {
    const visual = {
      accent_color: undefined,
      water_color: "#46a2ff",
      warning_color: "#f4b72f",
      card_radius: 16,
      section_radius: 12,
      overlay_opacity: 0.78,
      vignette_opacity: 0.16,
      panel_opacity: 0.76,
      blur: 16,
      text_scale: 1,
      min_height: "0",
      density: "normal",
      css_variables: {},
      ...this.config.visual,
    };

    const accent = visual.accent_color || this.toneColor(tone);
    this.root.dataset.density = visual.density || "normal";
    this.root.style.setProperty("--lv-accent", accent);
    this.root.style.setProperty("--lv-water", visual.water_color);
    this.root.style.setProperty("--lv-warning", visual.warning_color);
    this.root.style.setProperty("--lv-card-radius", `${Number(visual.card_radius) || 16}px`);
    this.root.style.setProperty("--lv-section-radius", `${Number(visual.section_radius) || 12}px`);
    this.root.style.setProperty("--lv-overlay-left", this.opacity(visual.overlay_opacity, 0.78));
    this.root.style.setProperty("--lv-overlay-mid", this.opacity(Number(visual.overlay_opacity) * 0.72, 0.56));
    this.root.style.setProperty("--lv-overlay-right", this.opacity(Number(visual.overlay_opacity) * 0.54, 0.42));
    this.root.style.setProperty("--lv-vignette-opacity", this.opacity(visual.vignette_opacity, 0.16));
    this.root.style.setProperty("--lv-panel-opacity", this.opacity(visual.panel_opacity, 0.76));
    this.root.style.setProperty("--lv-bg-blur", `${Number(visual.blur) || 0}px`);
    this.root.style.setProperty("--lv-text-scale", this.clampNumber(visual.text_scale, 0.75, 1.25, 1));
    this.root.style.setProperty("--lv-card-min-height", this.cssLength(visual.min_height, "0"));

    Object.entries(visual.css_variables || {}).forEach(([key, value]) => {
      const name = key.startsWith("--") ? key : `--${key}`;
      this.root.style.setProperty(name, String(value));
    });
  }

  carePlan(mowing, water, stress) {
    return [
      {
        icon: "leaf",
        label: "Maehen",
        value: this.actionText(mowing, "mowing"),
        description:
          mowing >= 72
            ? "Ideal fuer den naechsten Schnitt."
            : mowing >= 45
              ? "Bald gutes Fenster."
              : "Heute besser warten.",
        tone: this.metricTone(mowing, true),
      },
      {
        icon: "water-outline",
        label: "Wasser",
        value: `${this.format(water, "1")} mm`,
        description:
          water <= 3
            ? "Optimal bewaessert."
            : water <= 8
              ? "Leicht beobachten."
              : "Bewaesserung sinnvoll.",
        tone: this.metricTone(water, false),
      },
      {
        icon: "shield-outline",
        label: "Stress",
        value: `${this.format(stress, "0")} %`,
        description:
          stress <= 30
            ? "Niedrige Belastung."
            : stress <= 65
              ? "Mittlere Belastung."
              : "Rasen schonen.",
        tone: this.metricTone(100 - stress, true),
      },
    ];
  }

  agroMetric(icon, label, value, unit, digits) {
    return `
      <article class="agro-metric">
        <ha-icon icon="mdi:${icon}"></ha-icon>
        <div>
          <span>${this.escape(label)}</span>
          <strong>${this.formatOptional(value, digits)}${unit ? `<small>${this.escape(unit)}</small>` : ""}</strong>
        </div>
      </article>
    `;
  }

  moistureDepth(item) {
    const width = item.value === null ? 0 : Math.max(0, Math.min(item.value * 100, 100));
    return `
      <div class="moisture-depth">
        <span>${this.escape(item.depth)}</span>
        <div class="moisture-bar"><i style="width:${width}%"></i></div>
        <strong>${this.formatOptional(item.value, 3)}</strong>
      </div>
    `;
  }

  forecastMetric(icon, label, value) {
    return `
      <article class="forecast-metric">
        <ha-icon icon="mdi:${icon}"></ha-icon>
        <div>
          <span>${this.escape(label)}</span>
          <strong>${this.escape(value)}</strong>
        </div>
      </article>
    `;
  }

  timeline(mowing, water, stress) {
    if (stress >= 65) {
      return [
        { day: "Jetzt", label: "Erholen", tone: "warn" },
        { day: "+24h", label: "Pruefen", tone: "neutral" },
        { day: "+48h", label: "Schonend", tone: "neutral" },
        { day: "+3T", label: "Pflege", tone: "good" },
      ];
    }

    if (water >= 8) {
      return [
        { day: "Jetzt", label: "Waessern", tone: "warn" },
        { day: "+24h", label: "Ruhe", tone: "neutral" },
        { day: "+48h", label: "Maehen", tone: mowing >= 55 ? "good" : "neutral" },
        { day: "+3T", label: "Check", tone: "good" },
      ];
    }

    return [
      { day: "Jetzt", label: mowing >= 70 ? "Maehen" : "Check", tone: mowing >= 70 ? "good" : "neutral" },
      { day: "+24h", label: "Wuchs", tone: "good" },
      { day: "+48h", label: water > 4 ? "Wasser" : "Stabil", tone: water > 4 ? "neutral" : "good" },
      { day: "+3T", label: "Pflege", tone: "good" },
    ];
  }

  actionText(value, kind) {
    if (kind === "mowing") {
      if (value >= 72) return "Sehr gut";
      if (value >= 45) return "Bald";
      return "Warten";
    }
    return `${this.format(value, "0")} %`;
  }

  actionInfo(entityId) {
    if (!entityId || !this._hass || !this._hass.states || !this._hass.states[entityId]) {
      return null;
    }
    const entity = this._hass.states[entityId];
    const attrs = entity.attributes || {};
    return {
      state: entity.state,
      next_window: attrs.next_window ?? "",
      reason: attrs.reason ?? "",
      days_since: attrs.days_since ?? null,
      cooldown_days: attrs.cooldown_days ?? null,
    };
  }

  actionLabel(actionId) {
    return (
      {
        mow: "Maehen",
        water: "Bewaessern",
        fertilize: "Duengen",
        scarify: "Vertikutieren",
        aerate: "Aerifizieren",
        overseed: "Nachsaat",
      }[actionId] || "Pflege"
    );
  }

  actionIcon(actionId) {
    return (
      {
        mow: "mdi:robot-mower",
        water: "mdi:watering-can-outline",
        fertilize: "mdi:bottle-tonic-outline",
        scarify: "mdi:rake",
        aerate: "mdi:dots-grid",
        overseed: "mdi:seed-outline",
      }[actionId] || "mdi:leaf"
    );
  }

  actionStateLabel(state) {
    return (
      {
        do_now: "Jetzt",
        soon: "Bald",
        wait: "Warten",
        skip: "Nicht empfohlen",
        off_season: "Ausserhalb Saison",
      }[state] || "—"
    );
  }

  actionStateTone(state) {
    return (
      {
        do_now: "good",
        soon: "neutral",
        wait: "neutral",
        skip: "warn",
        off_season: "muted",
      }[state] || "muted"
    );
  }

  careGuideData() {
    const entities = {
      mow: this.config.entity_action_mow,
      water: this.config.entity_action_water,
      fertilize: this.config.entity_action_fertilize,
      scarify: this.config.entity_action_scarify,
      aerate: this.config.entity_action_aerate,
      overseed: this.config.entity_action_overseed,
    };
    const order = ["water", "mow", "fertilize", "overseed", "scarify", "aerate"];
    const items = order
      .map((id) => {
        const info = this.actionInfo(entities[id]);
        if (!info) return null;
        return {
          id,
          state: info.state,
          label: this.actionLabel(id),
          icon: this.actionIcon(id),
          badge: this.actionStateLabel(info.state),
          tone: this.actionStateTone(info.state),
          window: info.next_window,
          reason: info.reason,
        };
      })
      .filter(Boolean);

    let headline = null;
    const nextEntity = this.config.entity_next_action
      && this._hass?.states?.[this.config.entity_next_action];
    if (nextEntity) {
      const id = nextEntity.state;
      const attrs = nextEntity.attributes || {};
      headline = {
        id,
        label: id === "none" ? "Beobachten" : this.actionLabel(id),
        reason: attrs.reason ?? "",
        window: attrs.next_window ?? "",
        icon: id === "none" ? "mdi:eye-outline" : this.actionIcon(id),
        tone: id === "none" ? "muted" : "good",
      };
    }

    return { headline, items };
  }

  carePlan7dData() {
    const entity = this.config.entity_care_plan_7d
      && this._hass?.states?.[this.config.entity_care_plan_7d];
    if (!entity) {
      return { days: [], actionable: 0 };
    }
    const attrs = entity.attributes || {};
    const days = Array.isArray(attrs.days) ? attrs.days : [];
    return {
      days,
      actionable: Number.isFinite(attrs.actionable) ? attrs.actionable : 0,
    };
  }

  formatTempRange(high, low) {
    const hiOk = Number.isFinite(high);
    const loOk = Number.isFinite(low);
    if (hiOk && loOk) return `${Math.round(high)}° / ${Math.round(low)}°`;
    if (hiOk) return `${Math.round(high)}°`;
    if (loOk) return `${Math.round(low)}°`;
    return "--";
  }

  numberState(entityId) {
    if (!entityId || !this._hass.states[entityId]) {
      return 0;
    }
    const value = Number.parseFloat(this._hass.states[entityId].state);
    return Number.isFinite(value) ? value : 0;
  }

  numberStateOrNull(entityId) {
    if (!entityId || !this._hass.states[entityId]) {
      return null;
    }
    const value = Number.parseFloat(this._hass.states[entityId].state);
    return Number.isFinite(value) ? value : null;
  }

  textState(entityId, fallback) {
    if (!entityId || !this._hass.states[entityId]) {
      return fallback;
    }
    const state = this._hass.states[entityId].state;
    return state && state !== "unknown" && state !== "unavailable" ? state : fallback;
  }

  format(value, digits) {
    if (!Number.isFinite(value)) {
      return "--";
    }
    return Number(value).toFixed(Number(digits));
  }

  formatOptional(value, digits) {
    if (!Number.isFinite(value)) {
      return "--";
    }
    return this.format(value, digits);
  }

  phaseLabel(phase) {
    return (
      {
        active_growth: "Aktives Wachstum",
        dormant: "Ruhephase",
        dry: "Trockenstress",
        slow_growth: "Langsames Wachstum",
        stress: "Stressphase",
        waking_up: "Startwachstum",
      }[phase] || "Rasenzustand"
    );
  }

  phaseIcon(phase) {
    return (
      {
        active_growth: "mdi:leaf",
        dormant: "mdi:snowflake",
        dry: "mdi:weather-sunny-alert",
        slow_growth: "mdi:grass",
        stress: "mdi:alert-decagram-outline",
        waking_up: "mdi:seed-outline",
      }[phase] || "mdi:grass"
    );
  }

  trendLabel(trend) {
    return (
      {
        rising: "steigend",
        stable: "stabil",
        falling: "fallend",
        unknown: "--",
      }[trend] || trend
    );
  }

  scoreHeadline(growth, stress, phase) {
    if (phase === "dormant") return "Rasen ruht";
    if (stress > 65) return "Erholung priorisieren";
    if (growth > 78) return "Perfektes Pflegefenster";
    if (growth > 50) return "Solide Wachstumsphase";
    return "Langsam aufbauen";
  }

  scoreText(growth, stress) {
    if (stress > 65) {
      return "Heute keine intensiven Massnahmen planen.";
    }
    if (growth > 75) {
      return "Wachstum, Schnitt und Farbe wirken im gruenen Bereich.";
    }
    if (growth > 45) {
      return "Gute Basis, Wetter und Feuchte weiter beobachten.";
    }
    return "Wachstum aktuell verhalten, Pflegefenster abwarten.";
  }

  tone(growth, stress, phase) {
    if (phase === "dormant") {
      return "calm";
    }
    if (stress > 65 || phase === "dry" || phase === "stress") {
      return "warn";
    }
    if (growth > 68) {
      return "good";
    }
    return "neutral";
  }

  toneColor(tone) {
    return (
      {
        calm: "#78a7c3",
        good: "#42d65d",
        neutral: "#a7c957",
        warn: "#f4b72f",
      }[tone] || "#42d65d"
    );
  }

  metricTone(value, highIsGood) {
    if (highIsGood) {
      if (value >= 70) return "good";
      if (value >= 40) return "neutral";
      return "warn";
    }
    if (value <= 3) return "good";
    if (value <= 8) return "neutral";
    return "warn";
  }

  opacity(value, fallback) {
    return String(this.clampNumber(value, 0, 1, fallback));
  }

  clampNumber(value, min, max, fallback) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return fallback;
    }
    return Math.min(Math.max(numeric, min), max);
  }

  cssLength(value, fallback) {
    if (value === undefined || value === null || value === "") {
      return fallback;
    }
    if (typeof value === "number") {
      return `${value}px`;
    }
    return String(value);
  }

  escape(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  styles() {
    return `
      .lawn-vision {
        overflow: hidden;
        border-radius: var(--ha-card-border-radius, var(--lv-card-radius, 16px));
        background: #07111a;
        box-shadow: none;
      }

      .lawn-vision__root {
        color: #f8fafc;
        --lawn-bg: linear-gradient(140deg, #14311d, #07111a);
        --lawn-bg-position: center;
        --lawn-bg-size: cover;
        --lv-accent: #42d65d;
        --lv-water: #46a2ff;
        --lv-warning: #f4b72f;
        --lv-card-radius: 16px;
        --lv-section-radius: 12px;
        --lv-overlay-left: .78;
        --lv-overlay-mid: .56;
        --lv-overlay-right: .42;
        --lv-vignette-opacity: .16;
        --lv-panel-opacity: .76;
        --lv-bg-blur: 16px;
        --lv-text-scale: 1;
        --lv-card-min-height: 0;
        --lv-pad: 18px;
        --lv-gap: 14px;
        --lv-title: 28px;
        --lv-kicker: 12px;
        --lv-phase: 12px;
        --lv-ring: 104px;
        --lv-score: 46px;
        --lv-hero-title: 23px;
        --lv-hero-copy: 14px;
        --lv-plan-gap: 10px;
        --lv-plan-pad: 14px;
        --lv-plan-value: 19px;
        --lv-text: 13px;
        --lv-icon: 20px;
        --lv-check: 30px;
      }

      .lawn-vision__root[data-density="dense"] {
        --lv-pad: calc(var(--lv-pad) * .82);
        --lv-gap: calc(var(--lv-gap) * .78);
        --lv-plan-pad: calc(var(--lv-plan-pad) * .78);
        --lv-plan-gap: calc(var(--lv-plan-gap) * .78);
      }

      .lawn-vision__root[data-density="spacious"] {
        --lv-pad: calc(var(--lv-pad) * 1.18);
        --lv-gap: calc(var(--lv-gap) * 1.18);
        --lv-plan-pad: calc(var(--lv-plan-pad) * 1.16);
        --lv-plan-gap: calc(var(--lv-plan-gap) * 1.14);
      }

      .lawn-vision__root[data-size="compact"] {
        --lv-pad: 14px;
        --lv-gap: 10px;
        --lv-title: 23px;
        --lv-kicker: 10px;
        --lv-phase: 11px;
        --lv-ring: 82px;
        --lv-score: 36px;
        --lv-hero-title: 19px;
        --lv-hero-copy: 12px;
        --lv-plan-gap: 7px;
        --lv-plan-pad: 10px;
        --lv-plan-value: 16px;
        --lv-text: 12px;
        --lv-icon: 17px;
        --lv-check: 24px;
      }

      .lawn-vision__root[data-size="wide"] {
        --lv-pad: 26px;
        --lv-gap: 18px;
        --lv-title: 36px;
        --lv-kicker: 13px;
        --lv-phase: 14px;
        --lv-ring: 128px;
        --lv-score: 60px;
        --lv-hero-title: 28px;
        --lv-hero-copy: 16px;
        --lv-plan-gap: 14px;
        --lv-plan-pad: 18px;
        --lv-plan-value: 23px;
        --lv-text: 14px;
        --lv-icon: 22px;
        --lv-check: 34px;
      }

      .scene {
        position: relative;
        display: grid;
        gap: var(--lv-gap);
        min-height: var(--lv-card-min-height);
        overflow: hidden;
        border: 1px solid rgba(207, 231, 255, .16);
        border-radius: var(--lv-card-radius);
        padding: var(--lv-pad);
        isolation: isolate;
        background:
          radial-gradient(circle at 88% 28%, color-mix(in srgb, var(--lv-accent) 22%, transparent), transparent 18%),
          linear-gradient(90deg, rgba(3, 13, 22, var(--lv-overlay-left)), rgba(5, 18, 25, var(--lv-overlay-mid)) 46%, rgba(5, 18, 24, var(--lv-overlay-right))),
          linear-gradient(180deg, rgba(6, 15, 23, .30), rgba(6, 15, 23, .88)),
          var(--lawn-bg);
        background-size: auto, auto, auto, var(--lawn-bg-size);
        background-position: center, center, center, var(--lawn-bg-position);
        box-shadow:
          inset 0 1px 0 rgba(255,255,255,.08),
          inset 0 0 0 1px rgba(255,255,255,.03);
      }

      .scene::before {
        content: "";
        position: absolute;
        inset: 0;
        z-index: -1;
        background:
          linear-gradient(180deg, rgba(255,255,255,.06), transparent 18%),
          radial-gradient(circle at 24% 40%, var(--tone-glow), transparent 34%);
        pointer-events: none;
      }

      .scene::after {
        content: "";
        position: absolute;
        inset: 0;
        z-index: -1;
        background: rgba(5, 15, 22, var(--lv-vignette-opacity));
        backdrop-filter: blur(var(--lv-bg-blur)) saturate(1.05);
      }

      .scene--good { --tone: var(--lv-accent); --tone-soft: color-mix(in srgb, var(--lv-accent) 24%, transparent); --tone-glow: color-mix(in srgb, var(--lv-accent) 18%, transparent); --tone-dark: color-mix(in srgb, var(--lv-accent) 58%, #06141d); }
      .scene--neutral { --tone: var(--lv-accent); --tone-soft: color-mix(in srgb, var(--lv-accent) 20%, transparent); --tone-glow: color-mix(in srgb, var(--lv-accent) 16%, transparent); --tone-dark: color-mix(in srgb, var(--lv-accent) 52%, #06141d); }
      .scene--warn { --tone: var(--lv-warning); --tone-soft: color-mix(in srgb, var(--lv-warning) 20%, transparent); --tone-glow: color-mix(in srgb, var(--lv-warning) 16%, transparent); --tone-dark: color-mix(in srgb, var(--lv-warning) 55%, #06141d); }
      .scene--calm { --tone: #78a7c3; --tone-soft: rgba(120,167,195,.20); --tone-glow: rgba(120,167,195,.16); --tone-dark: #456f88; }

      .topline {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 18px;
      }

      .title {
        min-width: 0;
      }

      .kicker {
        display: block;
        color: rgba(226, 232, 240, .72);
        font-size: calc(var(--lv-kicker) * var(--lv-text-scale));
        font-weight: 780;
        letter-spacing: 0;
        line-height: 1;
        text-transform: uppercase;
        text-shadow: 0 2px 14px rgba(0,0,0,.45);
      }

      h2 {
        margin: 7px 0 0;
        color: #f8fafc;
        font-size: calc(var(--lv-title) * var(--lv-text-scale));
        line-height: 1;
        font-weight: 820;
        letter-spacing: 0;
        text-shadow: 0 3px 24px rgba(0,0,0,.48);
      }

      .phase-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 0;
        max-width: 42%;
        gap: 8px;
        border: 1px solid rgba(255,255,255,.14);
        border-radius: 999px;
        padding: 9px 13px;
        color: rgba(228, 246, 218, .96);
        background: rgba(255,255,255,.13);
        box-shadow:
          inset 0 1px 0 rgba(255,255,255,.16),
          0 16px 36px rgba(0,0,0,.18);
        backdrop-filter: blur(16px) saturate(1.2);
        font-size: calc(var(--lv-phase) * var(--lv-text-scale));
        font-weight: 760;
        line-height: 1.05;
      }

      .phase-pill ha-icon {
        --mdc-icon-size: var(--lv-icon);
        flex: 0 0 auto;
        color: var(--tone);
        filter: drop-shadow(0 0 10px var(--tone-soft));
      }

      .phase-pill span {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .hero-grid {
        display: grid;
        grid-template-columns: var(--lv-ring) minmax(0, 1fr);
        align-items: center;
        gap: var(--lv-gap);
        min-height: 0;
      }

      .score-ring {
        --size: var(--lv-ring);
        position: relative;
        display: grid;
        place-items: center;
        width: var(--size);
        height: var(--size);
        border-radius: 999px;
        background:
          radial-gradient(circle at center, rgba(8, 20, 29, .92) 0 56%, transparent 57%),
          conic-gradient(var(--tone) calc(var(--score) * 1%), rgba(255,255,255,.18) 0);
        box-shadow:
          inset 0 0 0 1px rgba(255,255,255,.08),
          0 24px 48px rgba(0,0,0,.32),
          0 0 36px var(--tone-soft);
      }

      .score-ring span {
        position: absolute;
        top: 47%;
        left: 50%;
        transform: translate(-50%, -50%);
        color: #f8fafc;
        font-size: calc(var(--lv-score) * var(--lv-text-scale));
        font-weight: 820;
        line-height: 1;
        text-shadow: 0 5px 26px rgba(0,0,0,.52);
      }

      .score-ring small {
        position: absolute;
        top: 68%;
        left: 50%;
        transform: translateX(-50%);
        margin-top: 0;
        color: rgba(226, 232, 240, .80);
        font-size: calc(var(--lv-score) * .28 * var(--lv-text-scale));
        font-weight: 720;
        line-height: 1;
      }

      .hero-copy {
        display: grid;
        gap: 8px;
        min-width: 0;
        max-width: 520px;
      }

      .hero-copy strong {
        color: #f8fafc;
        font-size: calc(var(--lv-hero-title) * var(--lv-text-scale));
        line-height: 1.12;
        font-weight: 820;
        text-shadow: 0 4px 26px rgba(0,0,0,.50);
      }

      .hero-copy span {
        max-width: 36ch;
        color: rgba(226, 232, 240, .82);
        font-size: calc(var(--lv-hero-copy) * var(--lv-text-scale));
        line-height: 1.35;
        font-weight: 560;
        text-shadow: 0 3px 20px rgba(0,0,0,.48);
      }

      .plan {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: var(--lv-plan-gap);
      }

      .plan-item {
        display: grid;
        min-width: 0;
        gap: 9px;
        border: 1px solid rgba(201, 226, 255, .17);
        border-radius: var(--lv-section-radius);
        padding: var(--lv-plan-pad);
        background: rgba(15, 28, 38, var(--lv-panel-opacity));
        box-shadow:
          inset 0 1px 0 rgba(255,255,255,.08),
          0 18px 46px rgba(0,0,0,.20);
        backdrop-filter: blur(16px) saturate(1.15);
      }

      .plan-item--good { --item-color: var(--lv-accent); }
      .plan-item--neutral { --item-color: var(--lv-water); }
      .plan-item--warn { --item-color: var(--lv-warning); }

      .plan-item__head {
        display: flex;
        align-items: center;
        gap: 8px;
        min-width: 0;
      }

      .plan-item__head ha-icon {
        --mdc-icon-size: var(--lv-icon);
        flex: 0 0 auto;
        color: var(--item-color);
      }

      .plan-item__head span {
        overflow: hidden;
        color: rgba(226, 232, 240, .76);
        font-size: calc(11px * var(--lv-text-scale));
        font-weight: 780;
        letter-spacing: 0;
        text-overflow: ellipsis;
        text-transform: uppercase;
        white-space: nowrap;
      }

      .plan-item strong {
        overflow: hidden;
        color: #f8fafc;
        font-size: calc(var(--lv-plan-value) * var(--lv-text-scale));
        line-height: 1.05;
        font-weight: 820;
        text-overflow: ellipsis;
        white-space: nowrap;
        text-shadow: 0 3px 22px rgba(0,0,0,.44);
      }

      .plan-item p {
        margin: -6px 0 0;
        color: rgba(226, 232, 240, .73);
        font-size: calc(var(--lv-text) * var(--lv-text-scale));
        line-height: 1.32;
      }

      .agro-panel {
        display: grid;
        grid-template-columns: minmax(0, 1.12fr) minmax(260px, .88fr);
        gap: var(--lv-plan-gap);
      }

      .agro-grid,
      .moisture-profile {
        border: 1px solid rgba(201, 226, 255, .15);
        border-radius: var(--lv-section-radius);
        background: rgba(11, 24, 33, calc(var(--lv-panel-opacity) * .92));
        box-shadow:
          inset 0 1px 0 rgba(255,255,255,.08),
          0 18px 46px rgba(0,0,0,.18);
        backdrop-filter: blur(16px) saturate(1.12);
      }

      .agro-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0;
        overflow: hidden;
      }

      .agro-metric {
        display: grid;
        grid-template-columns: var(--lv-icon) minmax(0, 1fr);
        align-items: center;
        gap: 8px;
        min-width: 0;
        padding: 12px;
        border-right: 1px solid rgba(201, 226, 255, .12);
      }

      .agro-metric:last-child {
        border-right: 0;
      }

      .agro-metric ha-icon {
        --mdc-icon-size: var(--lv-icon);
        color: var(--tone);
      }

      .agro-metric span,
      .moisture-profile__head span,
      .moisture-profile__head em,
      .moisture-depth span {
        color: rgba(226, 232, 240, .72);
        font-size: calc(11px * var(--lv-text-scale));
        font-weight: 760;
        line-height: 1.1;
      }

      .agro-metric strong {
        display: block;
        margin-top: 4px;
        overflow: hidden;
        color: #f8fafc;
        font-size: calc(var(--lv-plan-value) * var(--lv-text-scale));
        font-weight: 820;
        line-height: 1.05;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .agro-metric small {
        margin-left: 3px;
        color: rgba(226, 232, 240, .64);
        font-size: 12px;
        font-weight: 760;
      }

      .moisture-profile {
        display: grid;
        gap: 8px;
        padding: 12px;
      }

      .moisture-profile__head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }

      .moisture-profile__head em {
        font-style: normal;
        opacity: .68;
      }

      .moisture-depth {
        display: grid;
        grid-template-columns: 46px minmax(0, 1fr) 54px;
        align-items: center;
        gap: 10px;
      }

      .moisture-depth strong {
        color: #f8fafc;
        font-size: 13px;
        font-weight: 780;
        text-align: right;
      }

      .moisture-bar {
        height: 8px;
        overflow: hidden;
        border-radius: 999px;
        background: rgba(226, 232, 240, .16);
      }

      .moisture-bar i {
        display: block;
        height: 100%;
        border-radius: inherit;
        background: linear-gradient(90deg, var(--lv-water), var(--lv-accent));
        box-shadow: 0 0 18px rgba(70, 162, 255, .18);
      }

      .forecast-panel {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: var(--lv-plan-gap);
        border: 1px solid rgba(201, 226, 255, .15);
        border-radius: var(--lv-section-radius);
        padding: var(--lv-plan-pad);
        background: rgba(11, 24, 33, calc(var(--lv-panel-opacity) * .92));
        box-shadow:
          inset 0 1px 0 rgba(255,255,255,.08),
          0 18px 46px rgba(0,0,0,.18);
        backdrop-filter: blur(var(--lv-bg-blur)) saturate(1.12);
      }

      .forecast-metric {
        display: grid;
        grid-template-columns: var(--lv-icon) minmax(0, 1fr);
        align-items: center;
        gap: 8px;
        min-width: 0;
      }

      .forecast-metric ha-icon {
        --mdc-icon-size: var(--lv-icon);
        color: var(--lv-accent);
      }

      .forecast-metric span {
        display: block;
        overflow: hidden;
        color: rgba(226, 232, 240, .70);
        font-size: calc(11px * var(--lv-text-scale));
        font-weight: 760;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .forecast-metric strong {
        display: block;
        margin-top: 3px;
        overflow: hidden;
        color: #f8fafc;
        font-size: calc(var(--lv-text) * var(--lv-text-scale));
        font-weight: 820;
        line-height: 1.1;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .forecast-panel p {
        grid-column: 1 / -1;
        margin: 2px 0 0;
        color: rgba(226, 232, 240, .76);
        font-size: calc(var(--lv-text) * var(--lv-text-scale));
        line-height: 1.34;
      }

      .horizon {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0;
        padding: 10px 18px 2px;
      }

      .horizon-step {
        position: relative;
        display: grid;
        justify-items: center;
        gap: 10px;
        min-width: 0;
        color: rgba(226, 232, 240, .70);
        text-align: center;
      }

      .horizon-step::before {
        content: "";
        position: absolute;
        top: calc(var(--lv-check) / 2);
        left: 0;
        width: 100%;
        height: 3px;
        background: rgba(226, 232, 240, .28);
      }

      .horizon-step:first-child::before {
        left: 50%;
        width: 50%;
      }

      .horizon-step:last-child::before {
        width: 50%;
      }

      .horizon-step--good { --dot-color: var(--lv-accent); --dot-shadow: color-mix(in srgb, var(--lv-accent) 34%, transparent); }
      .horizon-step--neutral { --dot-color: #a7c957; --dot-shadow: rgba(167,201,87,.28); }
      .horizon-step--warn { --dot-color: var(--lv-warning); --dot-shadow: color-mix(in srgb, var(--lv-warning) 28%, transparent); }

      .horizon-step > span {
        position: relative;
        z-index: 1;
        display: grid;
        place-items: center;
        width: var(--lv-check);
        height: var(--lv-check);
        border: 2px solid rgba(255,255,255,.16);
        border-radius: 999px;
        background: linear-gradient(145deg, var(--dot-color), var(--tone-dark));
        box-shadow:
          inset 0 1px 0 rgba(255,255,255,.22),
          0 10px 24px var(--dot-shadow);
      }

      .horizon-step ha-icon {
        --mdc-icon-size: calc(var(--lv-check) * .56);
        color: #f8fafc;
        filter: drop-shadow(0 2px 5px rgba(0,0,0,.30));
      }

      .horizon-step strong {
        color: #f8fafc;
        font-size: calc((var(--lv-text) + 3px) * var(--lv-text-scale));
        line-height: 1;
        font-weight: 820;
        text-shadow: 0 3px 18px rgba(0,0,0,.44);
      }

      .horizon-step em {
        max-width: 100%;
        overflow: hidden;
        color: rgba(226, 232, 240, .70);
        font-size: calc(var(--lv-text) * var(--lv-text-scale));
        font-style: normal;
        line-height: 1.1;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .recommendation {
        display: grid;
        grid-template-columns: calc(var(--lv-icon) + 8px) minmax(0, 1fr);
        align-items: start;
        gap: 12px;
        border: 1px solid rgba(154, 211, 118, .18);
        border-radius: var(--lv-section-radius);
        padding: var(--lv-plan-pad);
        background: color-mix(in srgb, var(--lv-accent) 18%, rgba(15, 28, 38, var(--lv-panel-opacity)));
        box-shadow:
          inset 0 1px 0 rgba(255,255,255,.08),
          0 18px 44px rgba(0,0,0,.18);
        backdrop-filter: blur(16px) saturate(1.08);
      }

      .recommendation ha-icon {
        --mdc-icon-size: calc(var(--lv-icon) + 8px);
        color: var(--lv-accent);
        filter: drop-shadow(0 0 12px rgba(120,211,63,.18));
      }

      .recommendation strong {
        display: block;
        margin: 0 0 4px;
        color: #f8fafc;
        font-size: calc((var(--lv-text) + 3px) * var(--lv-text-scale));
        font-weight: 820;
        line-height: 1.1;
      }

      .recommendation p {
        margin: 0;
        max-width: 45ch;
        color: rgba(226, 232, 240, .82);
        font-size: calc(var(--lv-text) * var(--lv-text-scale));
        line-height: 1.36;
      }

      .lawn-vision__root[data-size="compact"] .scene {
        border-radius: 12px;
      }

      .lawn-vision__root[data-size="compact"] .topline {
        display: grid;
        gap: 10px;
      }

      .lawn-vision__root[data-size="compact"] .phase-pill {
        justify-self: start;
        max-width: 100%;
      }

      .lawn-vision__root[data-size="compact"] .hero-grid {
        grid-template-columns: var(--lv-ring) minmax(0, 1fr);
        align-items: center;
      }

      .lawn-vision__root[data-size="compact"] .plan {
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }

      .lawn-vision__root[data-size="compact"] .plan-item {
        gap: 7px;
      }

      .lawn-vision__root[data-size="compact"] .plan-item__head {
        gap: 5px;
      }

      .lawn-vision__root[data-size="compact"] .plan-item p {
        display: none;
      }

      .lawn-vision__root[data-size="compact"] .agro-panel {
        grid-template-columns: 1fr;
      }

      .lawn-vision__root[data-size="compact"] .forecast-panel {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .lawn-vision__root[data-size="compact"] .agro-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr));
      }

      .lawn-vision__root[data-size="compact"] .agro-metric {
        display: grid;
        grid-template-columns: 1fr;
        justify-items: center;
        gap: 5px;
        padding: 9px 5px;
        text-align: center;
      }

      .lawn-vision__root[data-size="compact"] .agro-metric span {
        display: none;
      }

      .lawn-vision__root[data-size="compact"] .agro-metric strong {
        font-size: 13px;
      }

      .lawn-vision__root[data-size="compact"] .horizon {
        padding-inline: 4px;
      }

      .lawn-vision__root[data-size="medium"] .agro-panel {
        grid-template-columns: 1fr;
      }

      .lawn-vision__root[data-size="medium"] .forecast-panel {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      @media (max-width: 760px) {
        .scene {
          min-height: 0;
          gap: 18px;
          padding: 22px;
        }

        .topline {
          display: grid;
        }

        .phase-pill {
          justify-self: start;
          min-width: 0;
          max-width: 100%;
          padding: 11px 14px;
        }

        .hero-grid {
          grid-template-columns: 112px minmax(0, 1fr);
          gap: 18px;
          min-height: 142px;
        }

        .score-ring {
          --size: 112px;
        }

        .score-ring span {
          font-size: 48px;
        }

        .plan {
          grid-template-columns: 1fr;
          gap: 10px;
        }

        .plan-item {
          padding: 16px;
          gap: 10px;
        }

        .agro-panel {
          grid-template-columns: 1fr;
        }

        .forecast-panel {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .agro-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .agro-metric {
          border-right: 0;
          border-bottom: 1px solid rgba(201, 226, 255, .12);
          padding: 14px;
        }

        .agro-metric:nth-last-child(-n + 2) {
          border-bottom: 0;
        }

        .horizon {
          padding: 12px 6px 0;
        }

        .horizon-step > span {
          width: 31px;
          height: 31px;
        }

        .recommendation {
          grid-template-columns: 30px minmax(0, 1fr);
          gap: 14px;
          padding: 16px;
        }

        .recommendation ha-icon {
          --mdc-icon-size: 28px;
        }
      }

      @media (max-width: 420px) {
        .hero-grid {
          grid-template-columns: 1fr;
        }
      }

      .care-guide {
        display: grid;
        gap: var(--lv-plan-gap);
        padding: var(--lv-plan-pad);
        border-radius: var(--lv-section-radius, 12px);
        background: rgba(7, 17, 26, calc(var(--lv-panel-opacity) * .9));
        backdrop-filter: blur(calc(var(--lv-bg-blur) * .6));
        border: 1px solid rgba(255, 255, 255, .06);
      }

      .care-headline {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 12px;
        align-items: start;
        padding: 12px 14px;
        border-radius: 10px;
        background: linear-gradient(120deg, rgba(66, 214, 93, .18), rgba(66, 214, 93, .06));
        border: 1px solid rgba(66, 214, 93, .32);
      }

      .care-headline--muted {
        background: rgba(255, 255, 255, .06);
        border-color: rgba(255, 255, 255, .12);
      }

      .care-headline ha-icon {
        --mdc-icon-size: calc(var(--lv-icon) * 1.5);
        color: var(--lv-accent);
        margin-top: 2px;
      }

      .care-headline__kicker {
        display: block;
        font-size: var(--lv-kicker);
        letter-spacing: .08em;
        text-transform: uppercase;
        color: rgba(255, 255, 255, .7);
      }

      .care-headline strong {
        display: block;
        font-size: calc(var(--lv-hero-title) * .85);
        margin-top: 2px;
      }

      .care-headline em {
        font-style: normal;
        color: var(--lv-accent);
        font-size: var(--lv-text);
        margin-top: 2px;
        display: inline-block;
      }

      .care-headline p {
        margin: 6px 0 0;
        font-size: var(--lv-text);
        color: rgba(255, 255, 255, .82);
        line-height: 1.35;
      }

      .care-list {
        list-style: none;
        padding: 0;
        margin: 0;
        display: grid;
        gap: 8px;
      }

      .care-row {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 10px;
        align-items: start;
        padding: 10px 12px;
        border-radius: 10px;
        background: rgba(255, 255, 255, .045);
        border: 1px solid rgba(255, 255, 255, .08);
      }

      .care-row--good {
        border-color: rgba(66, 214, 93, .35);
        background: rgba(66, 214, 93, .08);
      }

      .care-row--warn {
        border-color: rgba(244, 183, 47, .35);
        background: rgba(244, 183, 47, .08);
      }

      .care-row--muted { opacity: .72; }

      .care-row__icon {
        display: inline-flex;
        width: calc(var(--lv-icon) * 1.8);
        height: calc(var(--lv-icon) * 1.8);
        border-radius: 50%;
        align-items: center;
        justify-content: center;
        background: rgba(255, 255, 255, .08);
      }

      .care-row__icon ha-icon {
        --mdc-icon-size: var(--lv-icon);
        color: rgba(255, 255, 255, .92);
      }

      .care-row__body { display: grid; gap: 4px; min-width: 0; }

      .care-row__head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        flex-wrap: wrap;
      }

      .care-row__head strong { font-size: var(--lv-plan-value); }

      .care-badge {
        font-size: calc(var(--lv-kicker) * 1.05);
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 999px;
        background: rgba(255, 255, 255, .12);
        color: rgba(255, 255, 255, .85);
        white-space: nowrap;
      }

      .care-badge--good { background: rgba(66, 214, 93, .22); color: #c6f7d3; }
      .care-badge--warn { background: rgba(244, 183, 47, .22); color: #ffe6a9; }
      .care-badge--muted { background: rgba(255, 255, 255, .1); color: rgba(255, 255, 255, .66); }

      .care-row em {
        font-style: normal;
        color: var(--lv-accent);
        font-size: calc(var(--lv-text) * .95);
      }

      .care-row p {
        margin: 0;
        font-size: calc(var(--lv-text) * .95);
        color: rgba(255, 255, 255, .78);
        line-height: 1.3;
      }

      .care-plan-7d {
        display: grid;
        gap: 10px;
        padding: var(--lv-plan-pad);
        border-radius: var(--lv-section-radius, 12px);
        background: rgba(7, 17, 26, calc(var(--lv-panel-opacity) * .9));
        border: 1px solid rgba(255, 255, 255, .06);
      }

      .care-plan-7d__head {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 12px;
        color: rgba(255, 255, 255, .9);
      }

      .care-plan-7d__head .kicker {
        font-size: var(--lv-kicker);
        letter-spacing: .08em;
        text-transform: uppercase;
        color: rgba(255, 255, 255, .68);
      }

      .care-plan-7d__head strong {
        font-size: var(--lv-text);
        color: var(--lv-accent);
      }

      .care-plan-7d__grid {
        list-style: none;
        padding: 0;
        margin: 0;
        display: grid;
        grid-template-columns: repeat(7, minmax(0, 1fr));
        gap: 6px;
      }

      .care-plan-day {
        display: grid;
        gap: 4px;
        padding: 8px 4px;
        border-radius: 8px;
        background: rgba(255, 255, 255, .05);
        border: 1px solid rgba(255, 255, 255, .08);
        text-align: center;
        align-content: start;
      }

      .care-plan-day--good {
        background: rgba(66, 214, 93, .14);
        border-color: rgba(66, 214, 93, .35);
      }

      .care-plan-day--warn {
        background: rgba(244, 183, 47, .14);
        border-color: rgba(244, 183, 47, .35);
      }

      .care-plan-day--muted { opacity: .72; }

      .care-plan-day__label {
        font-weight: 700;
        font-size: calc(var(--lv-kicker) * 1.1);
        color: rgba(255, 255, 255, .85);
      }

      .care-plan-day ha-icon {
        --mdc-icon-size: calc(var(--lv-icon) * 1.05);
        color: rgba(255, 255, 255, .9);
        margin: 2px auto;
      }

      .care-plan-day strong {
        font-size: calc(var(--lv-text) * .95);
      }

      .care-plan-day em {
        font-style: normal;
        font-size: calc(var(--lv-kicker) * 1.05);
        color: rgba(255, 255, 255, .7);
        line-height: 1.2;
      }

      .care-plan-day small {
        font-size: calc(var(--lv-kicker) * 1.05);
        color: var(--lv-water);
      }

      .lawn-vision__root[data-size="compact"] .care-plan-7d__grid,
      .lawn-vision__root[data-size="medium"] .care-plan-7d__grid {
        grid-template-columns: repeat(4, minmax(0, 1fr));
        grid-auto-flow: row;
      }
    `;
  }
}

if (!customElements.get("lawn-vision-card")) {
  customElements.define("lawn-vision-card", LawnVisionCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "lawn-vision-card",
  name: "Lawn Vision Card",
  description: "Visual lawn growth, mowing, water and stress card.",
});

class LawnVisionCardEditor extends HTMLElement {
  setConfig(config) {
    this.config = {
      title: "Lawn Vision",
      background_image: "",
      background_position: "center",
      background_size: "cover",
      layout: "auto",
      size: "normal",
      show_agro: true,
      show_forecast: true,
      show_timeline: true,
      show_recommendation: true,
      show_care_guide: true,
      show_care_plan_7d: true,
      visual: {},
      ...config,
    };
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
  }

  render() {
    if (!this.config) {
      return;
    }

    const visual = {
      density: "normal",
      accent_color: "#42d65d",
      water_color: "#46a2ff",
      warning_color: "#f4b72f",
      card_radius: 16,
      section_radius: 12,
      overlay_opacity: 0.78,
      vignette_opacity: 0.16,
      panel_opacity: 0.76,
      blur: 16,
      text_scale: 1,
      min_height: 0,
      ...this.config.visual,
    };

    this.innerHTML = `
      <style>
        .editor {
          display: grid;
          gap: 16px;
          padding: 4px 0;
        }

        fieldset {
          display: grid;
          gap: 12px;
          margin: 0;
          padding: 14px;
          border: 1px solid var(--divider-color, rgba(127,127,127,.25));
          border-radius: 8px;
        }

        legend {
          padding: 0 6px;
          color: var(--primary-text-color);
          font-weight: 700;
        }

        label {
          display: grid;
          gap: 6px;
          color: var(--secondary-text-color);
          font-size: 12px;
          font-weight: 650;
        }

        input,
        select {
          box-sizing: border-box;
          width: 100%;
          min-height: 38px;
          border: 1px solid var(--divider-color, rgba(127,127,127,.35));
          border-radius: 6px;
          padding: 8px 10px;
          color: var(--primary-text-color);
          background: var(--card-background-color, #fff);
          font: inherit;
        }

        input[type="color"] {
          padding: 4px;
        }

        input[type="range"] {
          padding: 0;
        }

        .grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
        }

        .toggles {
          display: grid;
          gap: 8px;
        }

        .toggle {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          min-height: 34px;
        }

        .toggle input {
          width: auto;
          min-height: auto;
        }

        .range-row {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 46px;
          align-items: center;
          gap: 10px;
        }

        .range-row output {
          color: var(--primary-text-color);
          font-size: 12px;
          text-align: right;
        }

        details {
          display: grid;
          gap: 10px;
          padding: 4px 0;
        }

        details summary {
          cursor: pointer;
          font-weight: 650;
          color: var(--primary-text-color);
          padding: 4px 0;
        }

        details[open] summary {
          margin-bottom: 4px;
        }

        @media (max-width: 600px) {
          .grid {
            grid-template-columns: 1fr;
          }
        }
      </style>

      <div class="editor">
        <fieldset>
          <legend>Inhalt</legend>
          <label>
            Titel
            <input data-path="title" value="${this.escape(this.config.title || "")}" />
          </label>
          <label>
            Hintergrundbild
            <input data-path="background_image" value="${this.escape(this.config.background_image || "")}" placeholder="/local/community/lawn-vision/rasen.png" />
          </label>
          <div class="grid">
            ${this.select("background_position", "Bildposition", this.config.background_position, [
              ["center", "Mitte"],
              ["top", "Oben"],
              ["bottom", "Unten"],
              ["left", "Links"],
              ["right", "Rechts"],
            ])}
            ${this.select("background_size", "Bildgroesse", this.config.background_size, [
              ["cover", "Cover"],
              ["contain", "Contain"],
              ["auto", "Original"],
            ])}
          </div>
        </fieldset>

        <fieldset>
          <legend>Layout</legend>
          <div class="grid">
            ${this.select("layout", "Layout", this.config.layout, [
              ["auto", "Automatisch"],
              ["compact", "Kompakt"],
              ["medium", "Mittel"],
              ["wide", "Breit"],
            ])}
            ${this.select("size", "Kartenhoehe", this.config.size, [
              ["compact", "Kompakt"],
              ["normal", "Normal"],
              ["large", "Gross"],
            ])}
          </div>
          <div class="toggles">
            ${this.toggle("show_care_guide", "Pflegeguide anzeigen", this.config.show_care_guide !== false)}
            ${this.toggle("show_care_plan_7d", "7-Tage-Plan anzeigen", this.config.show_care_plan_7d !== false)}
            ${this.toggle("show_agro", "Agronomie anzeigen", this.config.show_agro !== false)}
            ${this.toggle("show_forecast", "Prognose anzeigen", this.config.show_forecast !== false)}
            ${this.toggle("show_timeline", "Timeline anzeigen", this.config.show_timeline !== false)}
            ${this.toggle("show_recommendation", "Empfehlung anzeigen", this.config.show_recommendation !== false)}
          </div>
        </fieldset>

        <fieldset>
          <legend>Entitaeten</legend>
          <details>
            <summary>Kernsensoren</summary>
            ${this.entityField("entity_phase", "Phase", "sensor.lawn_vision_phase")}
            ${this.entityField("entity_growth", "Wachstum (Pflicht)", "sensor.lawn_vision_growth_score")}
            ${this.entityField("entity_mowing", "Maehfenster", "sensor.lawn_vision_mowing_condition")}
            ${this.entityField("entity_water", "Wasserbedarf", "sensor.lawn_vision_water_need")}
            ${this.entityField("entity_stress", "Stress", "sensor.lawn_vision_stress_level")}
            ${this.entityField("entity_recommendation", "Empfehlung", "sensor.lawn_vision_recommendation")}
          </details>
          <details>
            <summary>Agronomie</summary>
            ${this.entityField("entity_soil_temperature", "Bodentemperatur", "sensor.lawn_vision_soil_temperature")}
            ${this.entityField("entity_mean_daily_temperature", "Tagesmittel", "sensor.lawn_vision_mean_daily_temperature")}
            ${this.entityField("entity_grassland_temperature_sum", "GTS", "sensor.lawn_vision_grassland_temperature_sum")}
            ${this.entityField("entity_growing_degree_days", "GDD", "sensor.lawn_vision_growing_degree_days")}
            ${this.entityField("entity_moisture_10cm", "Bodenfeuchte 10 cm", "sensor.lawn_vision_moisture_10cm")}
            ${this.entityField("entity_moisture_20cm", "Bodenfeuchte 20 cm", "sensor.lawn_vision_moisture_20cm")}
            ${this.entityField("entity_moisture_30cm", "Bodenfeuchte 30 cm", "sensor.lawn_vision_moisture_30cm")}
          </details>
          <details>
            <summary>Prognose</summary>
            ${this.entityField("entity_forecast_rain_risk", "Regenrisiko", "sensor.lawn_vision_forecast_rain_risk")}
            ${this.entityField("entity_forecast_water_need", "Wasserbedarf 48h", "sensor.lawn_vision_forecast_water_need")}
            ${this.entityField("entity_forecast_growth_trend", "Wachstumstrend", "sensor.lawn_vision_forecast_growth_trend")}
            ${this.entityField("entity_forecast_best_window", "Pflegefenster", "sensor.lawn_vision_forecast_best_window")}
            ${this.entityField("entity_forecast_care_hint", "Pflegehinweis", "sensor.lawn_vision_forecast_care_hint")}
          </details>
          <details open>
            <summary>Pflegeguide</summary>
            ${this.entityField("entity_next_action", "Naechste Aktion", "sensor.lawn_vision_next_action")}
            ${this.entityField("entity_care_plan_7d", "Pflegeplan 7 Tage", "sensor.lawn_vision_care_plan_7d")}
            ${this.entityField("entity_action_mow", "Aktion Maehen", "sensor.lawn_vision_action_mow")}
            ${this.entityField("entity_action_water", "Aktion Bewaessern", "sensor.lawn_vision_action_water")}
            ${this.entityField("entity_action_fertilize", "Aktion Duengen", "sensor.lawn_vision_action_fertilize")}
            ${this.entityField("entity_action_scarify", "Aktion Vertikutieren", "sensor.lawn_vision_action_scarify")}
            ${this.entityField("entity_action_aerate", "Aktion Aerifizieren", "sensor.lawn_vision_action_aerate")}
            ${this.entityField("entity_action_overseed", "Aktion Nachsaat", "sensor.lawn_vision_action_overseed")}
          </details>
        </fieldset>

        <fieldset>
          <legend>Design</legend>
          ${this.select("visual.density", "Dichte", visual.density, [
            ["dense", "Dicht"],
            ["normal", "Normal"],
            ["spacious", "Luftig"],
          ])}
          <div class="grid">
            ${this.color("visual.accent_color", "Akzent", visual.accent_color)}
            ${this.color("visual.water_color", "Wasser", visual.water_color)}
            ${this.color("visual.warning_color", "Warnung", visual.warning_color)}
          </div>
          ${this.range("visual.text_scale", "Textskalierung", visual.text_scale, 0.75, 1.25, 0.01)}
          ${this.range("visual.overlay_opacity", "Overlay", visual.overlay_opacity, 0, 1, 0.01)}
          ${this.range("visual.panel_opacity", "Panel-Deckkraft", visual.panel_opacity, 0, 1, 0.01)}
          ${this.range("visual.vignette_opacity", "Vignette", visual.vignette_opacity, 0, 0.6, 0.01)}
          ${this.range("visual.blur", "Glas-Blur", visual.blur, 0, 30, 1)}
          <div class="grid">
            ${this.number("visual.card_radius", "Kartenradius", visual.card_radius, 0, 32)}
            ${this.number("visual.section_radius", "Sektionenradius", visual.section_radius, 0, 24)}
            ${this.number("visual.min_height", "Mindesthoehe px", visual.min_height, 0, 900)}
          </div>
        </fieldset>
      </div>
    `;

    this.querySelectorAll("input, select").forEach((element) => {
      element.addEventListener("input", (event) => this.handleChange(event));
      element.addEventListener("change", (event) => this.handleChange(event));
    });
  }

  select(path, label, value, options) {
    return `
      <label>
        ${this.escape(label)}
        <select data-path="${this.escape(path)}">
          ${options
            .map(
              ([optionValue, optionLabel]) => `
                <option value="${this.escape(optionValue)}" ${value === optionValue ? "selected" : ""}>${this.escape(optionLabel)}</option>
              `
            )
            .join("")}
        </select>
      </label>
    `;
  }

  color(path, label, value) {
    return `
      <label>
        ${this.escape(label)}
        <input type="color" data-path="${this.escape(path)}" value="${this.escape(value || "#42d65d")}" />
      </label>
    `;
  }

  number(path, label, value, min, max) {
    return `
      <label>
        ${this.escape(label)}
        <input type="number" data-path="${this.escape(path)}" value="${this.escape(value ?? "")}" min="${min}" max="${max}" />
      </label>
    `;
  }

  range(path, label, value, min, max, step) {
    const id = `lv-${path.replace(/\./g, "-")}`;
    return `
      <label>
        ${this.escape(label)}
        <div class="range-row">
          <input id="${this.escape(id)}" type="range" data-path="${this.escape(path)}" value="${this.escape(value)}" min="${min}" max="${max}" step="${step}" />
          <output for="${this.escape(id)}">${this.escape(value)}</output>
        </div>
      </label>
    `;
  }

  toggle(path, label, checked) {
    return `
      <label class="toggle">
        <span>${this.escape(label)}</span>
        <input type="checkbox" data-path="${this.escape(path)}" ${checked ? "checked" : ""} />
      </label>
    `;
  }

  entityField(path, label, placeholder) {
    const value = this.config[path] ?? "";
    return `
      <label>
        ${this.escape(label)}
        <input type="text" data-path="${this.escape(path)}" value="${this.escape(value)}" placeholder="${this.escape(placeholder)}" />
      </label>
    `;
  }

  handleChange(event) {
    const element = event.currentTarget;
    const path = element.dataset.path;
    if (!path) {
      return;
    }

    const nextConfig = this.cloneConfig(this.config);
    let value = element.value;

    if (element.type === "checkbox") {
      value = element.checked;
    } else if (element.type === "number" || element.type === "range") {
      value = Number(element.value);
    }

    this.setPath(nextConfig, path, value);
    this.config = nextConfig;

    const output = element.parentElement?.querySelector("output");
    if (output) {
      output.textContent = String(value);
    }

    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: nextConfig },
        bubbles: true,
        composed: true,
      })
    );
  }

  setPath(target, path, value) {
    const parts = path.split(".");
    let cursor = target;
    parts.slice(0, -1).forEach((part) => {
      cursor[part] = cursor[part] || {};
      cursor = cursor[part];
    });
    cursor[parts[parts.length - 1]] = value;
  }

  cloneConfig(config) {
    return JSON.parse(JSON.stringify(config));
  }

  escape(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
}

if (!customElements.get("lawn-vision-card-editor")) {
  customElements.define("lawn-vision-card-editor", LawnVisionCardEditor);
}

const registeredLawnVisionCard = customElements.get("lawn-vision-card");
if (registeredLawnVisionCard && !registeredLawnVisionCard.getConfigElement) {
  registeredLawnVisionCard.getConfigElement = () =>
    document.createElement("lawn-vision-card-editor");
}
