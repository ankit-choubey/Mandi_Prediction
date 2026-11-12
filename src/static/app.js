/**
 * APMC Mandi Intelligence System - Research Instrument Frontend Application
 * Task: MP-UI-002 Agricultural Research Instrument Redesign
 * Pure Vanilla JavaScript (Zero External Packages, Zero CDN Dependencies).
 */

(function () {
  'use strict';

  // State Management
  const state = {
    health: null,
    catalog: null,
    allSeries: [],
    selectedDistrict: '',
    selectedMarket: '',
    selectedCommodity: '',
    selectedVariety: '',
    selectedGrade: '',
    latestObservation: null,
    benchmarkData: null,
    lastEconomicsResult: null,
    currentEvaluationRequestId: 0,
    sessionObservations: new Map(), // series_id -> Array<{date: string, modalPrice: number}>
  };

  // DOM Elements Cache
  const elements = {
    // Header & Masthead
    badgeHealth: document.getElementById('badge-health'),
    serviceAsOf: document.getElementById('service-as-of'),
    btnRefresh: document.getElementById('btn-refresh'),

    // Reproducibility Drawer
    drawerIndexSha: document.getElementById('drawer-index-sha'),
    drawerSourceSha: document.getElementById('drawer-source-sha'),

    // Navigation Tabs & Panels
    tabButtons: document.querySelectorAll('.tab-btn'),
    tabPanels: document.querySelectorAll('.tab-panel'),

    // Catalog Stats Grid
    statTotalSeries: document.getElementById('stat-total-series'),
    statAcceptedSeries: document.getElementById('stat-accepted-series'),
    statReviewSeries: document.getElementById('stat-review-series'),
    statUnavailableSeries: document.getElementById('stat-unavailable-series'),

    // 5-Part Cascading Selectors
    selDistrict: document.getElementById('sel-district'),
    selMarket: document.getElementById('sel-market'),
    selCommodity: document.getElementById('sel-commodity'),
    selVariety: document.getElementById('sel-variety'),
    selGrade: document.getElementById('sel-grade'),

    // Observation Cards & Price Movement
    obsEmptyState: document.getElementById('obs-empty-state'),
    obsVerifiedCard: document.getElementById('obs-verified-card'),
    obsReviewCard: document.getElementById('obs-review-card'),
    btnUseInCalc: document.getElementById('btn-use-in-calc'),

    // Price Movement Panel
    priceMovementPanel: document.getElementById('price-movement-panel'),
    priceMovementContent: document.getElementById('price-movement-content'),
    movementCapabilityBadge: document.getElementById('movement-capability-badge'),

    // Verified Card Fields
    obsSeriesTitle: document.getElementById('obs-series-title'),
    obsMarketSubtitle: document.getElementById('obs-market-subtitle'),
    obsModalPrice: document.getElementById('obs-modal-price'),
    obsMinPrice: document.getElementById('obs-min-price'),
    obsMaxPrice: document.getElementById('obs-max-price'),
    obsDate: document.getElementById('obs-date'),
    obsAge: document.getElementById('obs-age'),

    // Review Card Fields
    revDistrict: document.getElementById('rev-district'),
    revMarket: document.getElementById('rev-market'),
    revCommodity: document.getElementById('rev-commodity'),
    revVarietyGrade: document.getElementById('rev-variety-grade'),
    revDate: document.getElementById('rev-date'),

    // Benchmark Scorecard Elements
    benchmarkTbody: document.getElementById('benchmark-tbody'),
    bmWinnerModel: document.getElementById('bm-winner-model'),
    bmWinnerDesc: document.getElementById('bm-winner-desc'),
    bmRmseModel: document.getElementById('bm-rmse-model'),
    bmRmseDesc: document.getElementById('bm-rmse-desc'),
    bmRegimeTitle: document.getElementById('bm-regime-title'),
    bmRegimeDesc: document.getElementById('bm-regime-desc'),
    bmFoldGrid: document.getElementById('bm-fold-grid'),
    bmFoldNote: document.getElementById('bm-fold-note'),

    // Economics Form
    econForm: document.getElementById('economics-form'),
    btnPresetFixture: document.getElementById('btn-preset-fixture'),
    btnPresetClear: document.getElementById('btn-preset-clear'),
    btnCalcSubmit: document.getElementById('btn-calc-submit'),
    econCalcStatus: document.getElementById('econ-calc-status'),
    staleBanner: document.getElementById('stale-banner'),
    btnExportReceipt: document.getElementById('btn-export-receipt'),
    econInitialPrompt: document.getElementById('econ-initial-prompt'),
    econMetricsGrid: document.getElementById('econ-metrics-grid'),
    econDisclosuresBox: document.getElementById('econ-disclosures-box'),
    econDisclosuresList: document.getElementById('econ-disclosures-list'),

    // Economics Inputs
    econQuantity: document.getElementById('econ-quantity'),
    econCurrentPrice: document.getElementById('econ-current-price'),
    econFuturePoint: document.getElementById('econ-future-point'),
    econFutureLower: document.getElementById('econ-future-lower'),
    econFutureUpper: document.getElementById('econ-future-upper'),
    econHorizon: document.getElementById('econ-horizon'),
    econOriginDate: document.getElementById('econ-origin-date'),
    econOriginStatus: document.getElementById('econ-origin-status'),
    econStorageCost: document.getElementById('econ-storage-cost'),
    econHandlingCost: document.getElementById('econ-handling-cost'),
    econTransportCost: document.getElementById('econ-transport-cost'),
    econTransNow: document.getElementById('econ-trans-now'),
    econTransLater: document.getElementById('econ-trans-later'),
    econLossPct: document.getElementById('econ-loss-pct'),
    econMarkdownPct: document.getElementById('econ-markdown-pct'),
    econAnnualRate: document.getElementById('econ-annual-rate'),
    econCarryingType: document.getElementById('econ-carrying-type'),

    // Economics Results
    resGrossProceeds: document.getElementById('res-gross-proceeds'),
    resNetProceeds: document.getElementById('res-net-proceeds'),
    resHoldingProceeds: document.getElementById('res-holding-proceeds'),
    resDeltaR: document.getElementById('res-delta-r'),
    resBreakeven: document.getElementById('res-breakeven'),
    rangeResultsBox: document.getElementById('range-results-box'),
    rangeFutureBounds: document.getElementById('range-future-bounds'),
    rangeGainMin: document.getElementById('range-gain-min'),
    rangeGainMax: document.getElementById('range-gain-max'),
    rangeGainPoint: document.getElementById('range-gain-point'),

    // Waterfall Table
    waterfallCard: document.getElementById('waterfall-card'),
    waterfallTbody: document.getElementById('waterfall-tbody'),
  };

  // Utility: Currency Formatter
  function formatINR(val, decimals = 2) {
    if (val === null || val === undefined || isNaN(val)) return 'Unavailable';
    return '₹ ' + Number(val).toLocaleString('en-IN', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }

  // Utility: Server-Computed Age Formatter (India Calendar Date)
  function formatServerAge(ageDays, obsDate) {
    const dateStr = obsDate ? ` (${obsDate})` : '';
    if (ageDays === null || ageDays === undefined) {
      return obsDate ? `Observed: ${obsDate}` : 'Unknown date';
    }
    if (ageDays === 0) return `Observed today (India Calendar)${dateStr}`;
    if (ageDays === 1) return `1 day old (India Calendar)${dateStr}`;
    return `${ageDays} days old (India Calendar)${dateStr}`;
  }

  // Fetch wrapper with error normalization
  async function fetchAPI(endpoint, options = {}) {
    const res = await fetch(endpoint, options);
    const contentType = res.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      throw new Error(`Unexpected server response type: ${contentType}`);
    }
    const data = await res.json();
    if (!res.ok && data.status !== 'ERROR') {
      throw new Error(data.message || `HTTP ${res.status}`);
    }
    return data;
  }

  // Initialize System
  async function init() {
    setupTabNavigation();
    setupSelectorCascade();
    setupEconomicsEvents();

    try {
      await Promise.all([
        loadHealth(),
        loadCatalogAndPrices(),
        loadBenchmarks(),
      ]);
    } catch (err) {
      console.error('System initialization error:', err);
    }
  }

  // Tab Navigation with Keyboard Accessibility (ArrowLeft / ArrowRight / Home / End)
  function setupTabNavigation() {
    const tabs = Array.from(elements.tabButtons);

    tabs.forEach((btn, idx) => {
      btn.addEventListener('click', () => switchTab(btn));

      btn.addEventListener('keydown', (e) => {
        let targetIdx = null;
        if (e.key === 'ArrowRight') {
          targetIdx = (idx + 1) % tabs.length;
        } else if (e.key === 'ArrowLeft') {
          targetIdx = (idx - 1 + tabs.length) % tabs.length;
        } else if (e.key === 'Home') {
          targetIdx = 0;
        } else if (e.key === 'End') {
          targetIdx = tabs.length - 1;
        }

        if (targetIdx !== null) {
          e.preventDefault();
          tabs[targetIdx].focus();
          switchTab(tabs[targetIdx]);
        }
      });
    });
  }

  function switchTab(activeBtn) {
    elements.tabButtons.forEach((btn) => {
      btn.setAttribute('aria-selected', 'false');
      btn.setAttribute('tabindex', '-1');
    });
    activeBtn.setAttribute('aria-selected', 'true');
    activeBtn.setAttribute('tabindex', '0');

    const targetPanelId = activeBtn.getAttribute('aria-controls');
    elements.tabPanels.forEach((panel) => {
      if (panel.id === targetPanelId) {
        panel.classList.add('active');
        panel.removeAttribute('hidden');
      } else {
        panel.classList.remove('active');
        panel.setAttribute('hidden', 'true');
      }
    });
  }

  // Load Health Status from /api/v1/health
  async function loadHealth() {
    try {
      const resp = await fetchAPI('/api/v1/health');
      if (resp.status === 'SUCCESS' && resp.data) {
        state.health = resp.data;
        const status = resp.data.process_status;
        elements.badgeHealth.textContent = `Service: ${status}`;
        elements.badgeHealth.className = status === 'HEALTHY' ? 'badge badge-success' : 'badge badge-amber';

        if (resp.data.as_of_utc) {
          const dt = new Date(resp.data.as_of_utc);
          elements.serviceAsOf.textContent = `Snapshot UTC: ${dt.toISOString().replace('.000Z', 'Z')}`;
        }

        // Populate drawer source hash if exposed safely in prices capability
        const priceMeta = resp.data.capabilities?.prices?.metadata;
        if (priceMeta && priceMeta.source_sha256 && elements.drawerSourceSha) {
          elements.drawerSourceSha.textContent = priceMeta.source_sha256;
        }
      }
    } catch (err) {
      console.error('Failed to load health:', err);
      elements.badgeHealth.textContent = 'Service: Degraded';
      elements.badgeHealth.className = 'badge badge-danger';
    }
  }

  // Load Catalog and Price Series
  async function loadCatalogAndPrices() {
    try {
      const [catResp, pricesResp] = await Promise.all([
        fetchAPI('/api/v1/catalog'),
        fetchAPI('/api/v1/prices/latest'),
      ]);

      if (catResp.status === 'SUCCESS' && catResp.data) {
        state.catalog = catResp.data;
        elements.statTotalSeries.textContent = Number(catResp.data.total_series_count).toLocaleString();
        elements.statAcceptedSeries.textContent = Number(catResp.data.accepted_series_count).toLocaleString();
        elements.statReviewSeries.textContent = Number(catResp.data.review_series_count).toLocaleString();
        elements.statUnavailableSeries.textContent = '0';
      }

      if (pricesResp.status === 'SUCCESS' && pricesResp.data) {
        const rawSeries = pricesResp.data.series || [];
        state.allSeries = rawSeries.map(adaptPriceRecord);

        // Record observations in session cache for truth-preserving movement tracking
        state.allSeries.forEach((s) => {
          if (!state.sessionObservations.has(s.series_id)) {
            state.sessionObservations.set(s.series_id, []);
          }
          const obsList = state.sessionObservations.get(s.series_id);
          const alreadyRecorded = obsList.some((o) => o.date === s.observation_date);
          if (!alreadyRecorded && s.observation_date) {
            obsList.push({
              date: s.observation_date,
              modalPrice: s.modal_price,
            });
          }
        });

        populateDistrictDropdown();
      }
    } catch (err) {
      console.error('Failed to load catalog or prices:', err);
      elements.statTotalSeries.textContent = 'Unavailable';
      elements.statAcceptedSeries.textContent = 'Unavailable';
      elements.statReviewSeries.textContent = 'Unavailable';
    }
  }

  // Normalization Adapter for Price Record
  function adaptPriceRecord(s) {
    const marketName = s.market_canonical || s.market_raw || s.market || 'Unknown Market';
    let permitted = false;
    if (s.capabilities && typeof s.capabilities.price_display_permitted === 'boolean') {
      permitted = s.capabilities.price_display_permitted;
    } else if (typeof s.price_display_permitted === 'boolean') {
      permitted = s.price_display_permitted;
    } else {
      permitted = s.status === 'ACCEPTED' && s.market_alias_status === 'ACCEPTED';
    }

    return {
      series_id: s.series_id || `${s.district}|${marketName}|${s.commodity}|${s.variety}|${s.grade}`,
      district: s.district || 'Unknown District',
      market: marketName,
      market_raw: s.market_raw || marketName,
      market_canonical: s.market_canonical || marketName,
      commodity: s.commodity || 'Unknown Commodity',
      variety: s.variety || 'Common',
      grade: s.grade || s.grade_raw || 'FAQ',
      modal_price: typeof s.modal_price === 'number' ? s.modal_price : null,
      min_price: typeof s.min_price === 'number' ? s.min_price : null,
      max_price: typeof s.max_price === 'number' ? s.max_price : null,
      price_unit: s.price_unit || 'Rs./Quintal',
      observation_date: s.latest_observation_date || s.observation_date || null,
      age_days: typeof s.freshness_days === 'number' ? s.freshness_days : (typeof s.age_days === 'number' ? s.age_days : null),
      status: s.status || 'UNKNOWN',
      market_alias_status: s.market_alias_status || 'UNKNOWN',
      price_display_permitted: permitted,
    };
  }

  // 5-Part Cascading Dropdowns
  function setupSelectorCascade() {
    elements.selDistrict.addEventListener('change', onDistrictChange);
    elements.selMarket.addEventListener('change', onMarketChange);
    elements.selCommodity.addEventListener('change', onCommodityChange);
    elements.selVariety.addEventListener('change', onVarietyChange);
    elements.selGrade.addEventListener('change', onGradeChange);
    elements.btnUseInCalc.addEventListener('click', usePriceInCalculator);
    elements.btnRefresh.addEventListener('click', async () => {
      elements.btnRefresh.disabled = true;
      elements.btnRefresh.textContent = 'Refreshing...';
      try {
        await loadCatalogAndPrices();
        await loadHealth();
        if (state.selectedDistrict && state.selectedMarket && state.selectedCommodity && state.selectedVariety && state.selectedGrade) {
          loadExactSeriesObservation();
        }
      } finally {
        elements.btnRefresh.disabled = false;
        elements.btnRefresh.textContent = 'Refresh Snapshot';
      }
    });
  }

  function populateDistrictDropdown() {
    const districts = [...new Set(state.allSeries.map((s) => s.district).filter(Boolean))].sort();
    elements.selDistrict.innerHTML = '<option value="">-- Choose District --</option>';
    districts.forEach((d) => {
      const opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d;
      elements.selDistrict.appendChild(opt);
    });

    elements.selMarket.innerHTML = '<option value="">-- Choose Market --</option>';
    elements.selMarket.disabled = true;
    elements.selCommodity.innerHTML = '<option value="">-- Choose Commodity --</option>';
    elements.selCommodity.disabled = true;
    elements.selVariety.innerHTML = '<option value="">-- Choose Variety --</option>';
    elements.selVariety.disabled = true;
    elements.selGrade.innerHTML = '<option value="">-- Choose Grade --</option>';
    elements.selGrade.disabled = true;
  }

  function onDistrictChange() {
    state.selectedDistrict = elements.selDistrict.value;
    state.selectedMarket = '';
    state.selectedCommodity = '';
    state.selectedVariety = '';
    state.selectedGrade = '';

    elements.selMarket.innerHTML = '<option value="">-- Choose Market --</option>';
    elements.selCommodity.innerHTML = '<option value="">-- Choose Commodity --</option>';
    elements.selCommodity.disabled = true;
    elements.selVariety.innerHTML = '<option value="">-- Choose Variety --</option>';
    elements.selVariety.disabled = true;
    elements.selGrade.innerHTML = '<option value="">-- Choose Grade --</option>';
    elements.selGrade.disabled = true;

    if (!state.selectedDistrict) {
      elements.selMarket.disabled = true;
      resetObservationDisplay();
      return;
    }

    const filtered = state.allSeries.filter((s) => s.district === state.selectedDistrict);
    const markets = [...new Set(filtered.map((s) => s.market).filter(Boolean))].sort();
    markets.forEach((m) => {
      const opt = document.createElement('option');
      opt.value = m;
      opt.textContent = m;
      elements.selMarket.appendChild(opt);
    });
    elements.selMarket.disabled = false;
    resetObservationDisplay();
  }

  function onMarketChange() {
    state.selectedMarket = elements.selMarket.value;
    state.selectedCommodity = '';
    state.selectedVariety = '';
    state.selectedGrade = '';

    elements.selCommodity.innerHTML = '<option value="">-- Choose Commodity --</option>';
    elements.selVariety.innerHTML = '<option value="">-- Choose Variety --</option>';
    elements.selVariety.disabled = true;
    elements.selGrade.innerHTML = '<option value="">-- Choose Grade --</option>';
    elements.selGrade.disabled = true;

    if (!state.selectedMarket) {
      elements.selCommodity.disabled = true;
      resetObservationDisplay();
      return;
    }

    const filtered = state.allSeries.filter(
      (s) => s.district === state.selectedDistrict && s.market === state.selectedMarket
    );
    const commodities = [...new Set(filtered.map((s) => s.commodity).filter(Boolean))].sort();
    commodities.forEach((c) => {
      const opt = document.createElement('option');
      opt.value = c;
      opt.textContent = c;
      elements.selCommodity.appendChild(opt);
    });
    elements.selCommodity.disabled = false;
    resetObservationDisplay();
  }

  function onCommodityChange() {
    state.selectedCommodity = elements.selCommodity.value;
    state.selectedVariety = '';
    state.selectedGrade = '';

    elements.selVariety.innerHTML = '<option value="">-- Choose Variety --</option>';
    elements.selGrade.innerHTML = '<option value="">-- Choose Grade --</option>';
    elements.selGrade.disabled = true;

    if (!state.selectedCommodity) {
      elements.selVariety.disabled = true;
      resetObservationDisplay();
      return;
    }

    const filtered = state.allSeries.filter(
      (s) =>
        s.district === state.selectedDistrict &&
        s.market === state.selectedMarket &&
        s.commodity === state.selectedCommodity
    );
    const varieties = [...new Set(filtered.map((s) => s.variety).filter(Boolean))].sort();
    varieties.forEach((v) => {
      const opt = document.createElement('option');
      opt.value = v;
      opt.textContent = v;
      elements.selVariety.appendChild(opt);
    });
    elements.selVariety.disabled = false;
    resetObservationDisplay();
  }

  function onVarietyChange() {
    state.selectedVariety = elements.selVariety.value;
    state.selectedGrade = '';

    elements.selGrade.innerHTML = '<option value="">-- Choose Grade --</option>';

    if (!state.selectedVariety) {
      elements.selGrade.disabled = true;
      resetObservationDisplay();
      return;
    }

    const filtered = state.allSeries.filter(
      (s) =>
        s.district === state.selectedDistrict &&
        s.market === state.selectedMarket &&
        s.commodity === state.selectedCommodity &&
        s.variety === state.selectedVariety
    );
    const grades = [...new Set(filtered.map((s) => s.grade).filter(Boolean))].sort();
    grades.forEach((g) => {
      const opt = document.createElement('option');
      opt.value = g;
      opt.textContent = g;
      elements.selGrade.appendChild(opt);
    });
    elements.selGrade.disabled = false;
    resetObservationDisplay();
  }

  function onGradeChange() {
    state.selectedGrade = elements.selGrade.value;
    if (!state.selectedGrade) {
      resetObservationDisplay();
      return;
    }
    loadExactSeriesObservation();
  }

  function resetObservationDisplay() {
    state.latestObservation = null;
    elements.obsEmptyState.style.display = 'block';
    elements.obsVerifiedCard.style.display = 'none';
    elements.obsReviewCard.style.display = 'none';
  }

  // Display Exact Selected Series
  function loadExactSeriesObservation() {
    const match = state.allSeries.find(
      (s) =>
        s.district === state.selectedDistrict &&
        s.market === state.selectedMarket &&
        s.commodity === state.selectedCommodity &&
        s.variety === state.selectedVariety &&
        s.grade === state.selectedGrade
    );

    if (!match) {
      resetObservationDisplay();
      return;
    }

    state.latestObservation = match;
    elements.obsEmptyState.style.display = 'none';

    if (match.price_display_permitted) {
      // Verified Accepted Series Card
      elements.obsReviewCard.style.display = 'none';
      elements.obsVerifiedCard.style.display = 'block';

      elements.obsSeriesTitle.textContent = `${match.commodity} (${match.variety} - Grade ${match.grade})`;
      elements.obsMarketSubtitle.textContent = `${match.market} APMC, ${match.district} District`;
      elements.obsModalPrice.textContent = match.modal_price != null ? `₹ ${match.modal_price.toFixed(2)}` : 'Unavailable';
      elements.obsMinPrice.textContent = match.min_price != null ? `₹ ${match.min_price.toFixed(2)}` : 'Unavailable';
      elements.obsMaxPrice.textContent = match.max_price != null ? `₹ ${match.max_price.toFixed(2)}` : 'Unavailable';

      elements.obsDate.textContent = match.observation_date || 'Unknown';
      elements.obsAge.textContent = formatServerAge(match.age_days, match.observation_date);

      // Render Truth-Preserving Price Movement Panel
      renderPriceMovement(match);
    } else {
      // Review Preview Card (Price Withheld)
      elements.obsVerifiedCard.style.display = 'none';
      elements.obsReviewCard.style.display = 'block';

      elements.revDistrict.textContent = match.district;
      elements.revMarket.textContent = `${match.market} (Unapproved Market Identity)`;
      elements.revCommodity.textContent = match.commodity;
      elements.revVarietyGrade.textContent = `${match.variety} / ${match.grade}`;
      elements.revDate.textContent = match.observation_date || 'Unknown';
    }
  }

  // Truth-Preserving Price Movement Panel
  function renderPriceMovement(series) {
    if (!elements.priceMovementPanel || !elements.priceMovementContent) return;

    const obsList = state.sessionObservations.get(series.series_id) || [];
    // Genuine change requires >= 2 observations with distinct dates
    const distinctDateObs = [];
    const seenDates = new Set();
    for (const obs of obsList) {
      if (!seenDates.has(obs.date) && typeof obs.modalPrice === 'number') {
        seenDates.add(obs.date);
        distinctDateObs.push(obs);
      }
    }

    if (distinctDateObs.length >= 2) {
      // Sort chronologically by date
      distinctDateObs.sort((a, b) => a.date.localeCompare(b.date));
      const prior = distinctDateObs[distinctDateObs.length - 2];
      const latest = distinctDateObs[distinctDateObs.length - 1];
      const deltaP = latest.modalPrice - prior.modalPrice;
      const pctChange = prior.modalPrice > 0 ? (deltaP / prior.modalPrice) * 100 : 0;
      const deltaPrefix = deltaP >= 0 ? '+' : '';

      if (elements.movementCapabilityBadge) {
        elements.movementCapabilityBadge.textContent = 'SNAPSHOT_COMPARISON';
        elements.movementCapabilityBadge.className = 'badge badge-info';
      }

      elements.priceMovementContent.className = 'stat-box';
      elements.priceMovementContent.style.borderLeft = deltaP >= 0 ? '4px solid var(--color-crop-green)' : '4px solid var(--color-soil-rust)';
      elements.priceMovementContent.innerHTML = `
        <div class="stat-label">Change between imported snapshots (Not market trend)</div>
        <div class="stat-value" style="font-size: 1.5rem;">
          ${deltaPrefix}₹ ${Math.abs(deltaP).toFixed(2)} (${deltaPrefix}${pctChange.toFixed(2)}%)
        </div>
        <div class="stat-desc">
          Observed between ${prior.date} (₹ ${prior.modalPrice.toFixed(2)}) and ${latest.date} (₹ ${latest.modalPrice.toFixed(2)}).
        </div>
      `;
    } else {
      // Truthful unavailable state
      if (elements.movementCapabilityBadge) {
        elements.movementCapabilityBadge.textContent = 'CAPABILITY_UNAVAILABLE';
        elements.movementCapabilityBadge.className = 'badge badge-info';
      }

      elements.priceMovementContent.className = 'price-movement-unavailable';
      elements.priceMovementContent.innerHTML = `
        <h4>Price change unavailable &mdash; a second verified observation is required.</h4>
        <p>
          <strong>Dataset-first snapshot mode:</strong> currently containing 1 observation per series.
          In accordance with scientific truth-preserving rules, price change cannot be inferred from min/max spread, model predictions, or hypothetical fixtures. A second verified observation on a distinct date is required to establish temporal direction.
        </p>
      `;
    }
  }

  // Load Benchmark Scorecard from /api/v1/models/benchmark
  async function loadBenchmarks() {
    try {
      const resp = await fetchAPI('/api/v1/models/benchmark');
      if (resp.status === 'SUCCESS' && resp.data) {
        state.benchmarkData = resp.data;
        renderBenchmarkTable(resp.data.model_performance_summary || []);
        renderBenchmarkNarratives(resp.data);
      }
    } catch (err) {
      console.error('Failed to load benchmarks:', err);
      elements.benchmarkTbody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; color: var(--color-soil-rust);">
            Benchmark scorecard unavailable (${err.message}).
          </td>
        </tr>
      `;
      elements.bmWinnerModel.textContent = 'Unavailable';
      elements.bmRmseModel.textContent = 'Unavailable';
      elements.bmFoldNote.textContent = 'Benchmark dataset currently unavailable.';
    }
  }

  function renderBenchmarkTable(rows) {
    if (!rows.length) {
      elements.benchmarkTbody.innerHTML = `
        <tr><td colspan="7" style="text-align: center;">No benchmark rows returned.</td></tr>
      `;
      return;
    }

    elements.benchmarkTbody.innerHTML = '';
    rows.forEach((r) => {
      const tr = document.createElement('tr');
      if (r.model === 'naive_persistence') tr.className = 'highlight-row';

      const modelDisplayName = {
        naive_persistence: 'Naive Persistence (Baseline)',
        hist_gradient_boosting: 'Histogram Gradient Boosting',
        ridge_regression: 'Ridge Regression',
      }[r.model] || r.model;

      const skillStr = r.skill_vs_persistence_mae_pct != null
        ? `${Number(r.skill_vs_persistence_mae_pct).toFixed(2)}%`
        : '0.00%';

      const statusBadge = r.model === 'naive_persistence'
        ? '<span class="badge badge-success">Primary MAE Winner</span>'
        : (r.status === 'NON_WINNING_MAE_BEST_RMSE'
          ? '<span class="badge badge-info">Lowest RMSE</span>'
          : '<span class="badge badge-info">Challenger</span>');

      tr.innerHTML = `
        <th scope="row">${modelDisplayName}</th>
        <td class="num-cell"><strong>${Number(r.mae).toFixed(2)}</strong></td>
        <td class="num-cell">${Number(r.rmse).toFixed(2)}</td>
        <td class="num-cell">${skillStr}</td>
        <td class="num-cell">${Number(r.coverage_90_pct).toFixed(2)}%</td>
        <td class="num-cell">${Number(r.coverage_95_pct).toFixed(2)}%</td>
        <td>${statusBadge}</td>
      `;
      elements.benchmarkTbody.appendChild(tr);
    });
  }

  function renderBenchmarkNarratives(data) {
    const summary = data.model_performance_summary || [];
    const naive = summary.find((m) => m.model === 'naive_persistence');
    const hgb = summary.find((m) => m.model === 'hist_gradient_boosting');
    const breakdown = data.fold_level_breakdown_naive_90 || {};
    const scope = data.metric_denominators?.interval_metrics_scope || {};

    // 1. Primary Winner
    if (naive) {
      elements.bmWinnerModel.textContent = 'Naive Persistence';
      elements.bmWinnerDesc.textContent = `Achieves lowest MAE (${Number(naive.mae).toFixed(2)} INR/q). Persistence remains the reference standard on absolute loss across all benchmarked series.`;
    }

    // 2. RMSE Comparison
    if (hgb && naive) {
      elements.bmRmseModel.textContent = 'Histogram Gradient Boosting';
      const pct = hgb.rmse_improvement_vs_persistence_pct != null
        ? Number(hgb.rmse_improvement_vs_persistence_pct).toFixed(2)
        : (100 * (naive.rmse - hgb.rmse) / naive.rmse).toFixed(2);
      elements.bmRmseDesc.textContent = `Achieves lower RMSE (${Number(hgb.rmse).toFixed(2)} vs ${Number(naive.rmse).toFixed(2)} for Naive Persistence, a ${pct}% RMSE reduction), but persistence remains primary MAE winner.`;
    }

    // 3. Regime Generalization Gap
    const f2 = breakdown.F2;
    const f3 = breakdown.F3;
    const f4 = breakdown.F4;
    elements.bmRegimeTitle.textContent = 'Regime Generalization Gap';
    if (f2 && f3 && f4) {
      elements.bmRegimeDesc.textContent = `Severe undercoverage observed in later evaluation folds: F2 achieved ${Number(f2.coverage_pct).toFixed(2)}% (${Number(f2.issued_count).toLocaleString()} origins), while F3 (${Number(f3.coverage_pct).toFixed(2)}%, ${Number(f3.issued_count).toLocaleString()} origins) and F4 (${Number(f4.coverage_pct).toFixed(2)}%, ${Number(f4.issued_count).toLocaleString()} origins) fell well below 90% target.`;
    }

    // 4. Fold Cards
    if (elements.bmFoldGrid && (f2 || f3 || f4)) {
      elements.bmFoldGrid.innerHTML = '';
      const folds = [
        { id: 'F2', label: 'Fold F2', data: f2, border: 'var(--color-crop-green)' },
        { id: 'F3', label: 'Fold F3', data: f3, border: 'var(--color-soil-rust)' },
        { id: 'F4', label: 'Fold F4', data: f4, border: 'var(--color-soil-rust)' },
      ];

      folds.forEach((f) => {
        if (!f.data) return;
        const box = document.createElement('div');
        box.className = 'stat-box';
        box.style.borderLeft = `4px solid ${f.border}`;
        const cov = Number(f.data.coverage_pct).toFixed(2);
        const count = Number(f.data.issued_count).toLocaleString();
        box.innerHTML = `
          <div class="stat-label">${f.label}</div>
          <div class="stat-value" style="font-size: 1.375rem;">${cov}%</div>
          <div class="stat-desc">
            ${count} origins (90% target). Mean width: ${Number(f.data.mean_width).toFixed(1)} INR/q.
          </div>
        `;
        elements.bmFoldGrid.appendChild(box);
      });
    }

    // 5. Total Fold Note
    const totalIssued = scope.total_issued_origins || (
      (f2 ? f2.issued_count : 0) + (f3 ? f3.issued_count : 0) + (f4 ? f4.issued_count : 0)
    );
    if (totalIssued) {
      elements.bmFoldNote.textContent = `Evaluated across ${Number(totalIssued).toLocaleString()} total forecast origins across F2–F4 test folds under chronological expanding window.`;
    }
  }

  // Pre-fill Price from Verified Card into Calculator
  function usePriceInCalculator() {
    if (!state.latestObservation || !state.latestObservation.price_display_permitted) return;

    // Switch to Economics tab
    const econTab = document.getElementById('tab-economics');
    if (econTab) switchTab(econTab);

    // Transfer ONLY permitted observed current price, date, and provenance
    elements.econCurrentPrice.value = state.latestObservation.modal_price;
    elements.econOriginDate.value = state.latestObservation.observation_date || '';
    elements.econOriginStatus.value = 'OBSERVED_PRICE_TRANSFER';

    // Leave future prices and costs blank (do not assume defaults or fake +150 increase)
    elements.econFuturePoint.value = '';
    elements.econFutureLower.value = '';
    elements.econFutureUpper.value = '';
    elements.econStorageCost.value = '';
    elements.econHandlingCost.value = '';
    elements.econTransportCost.value = '';
    elements.econTransNow.value = '';
    elements.econTransLater.value = '';
    elements.econLossPct.value = '';
    elements.econMarkdownPct.value = '';

    markInputsStale();
    elements.econCurrentPrice.focus();
  }

  // Setup Economics Calculator Events
  function setupEconomicsEvents() {
    elements.btnPresetFixture.addEventListener('click', loadReferenceFixture);
    elements.btnPresetClear.addEventListener('click', clearEconomicsForm);
    elements.econForm.addEventListener('submit', onCalculateEconomics);
    elements.btnExportReceipt.addEventListener('click', downloadReceipt);

    // Invalidate results and disable receipt export on any input modification
    const inputs = elements.econForm.querySelectorAll('input, select');
    inputs.forEach((input) => {
      input.addEventListener('input', markInputsStale);
      input.addEventListener('change', markInputsStale);
    });
  }

  function markInputsStale() {
    elements.staleBanner.classList.add('visible');
    elements.staleBanner.style.display = 'block';
    elements.btnExportReceipt.disabled = true;
    state.lastEconomicsResult = null;
  }

  // Load Reference Mathematical Fixture (+470 INR gain control)
  function loadReferenceFixture() {
    elements.econQuantity.value = '10';
    elements.econCurrentPrice.value = '2500';
    elements.econFuturePoint.value = '2650';
    elements.econFutureLower.value = '';
    elements.econFutureUpper.value = '';
    elements.econHorizon.value = '7';
    elements.econOriginDate.value = '2026-11-13';
    elements.econOriginStatus.value = 'USER_ENTERED';

    elements.econStorageCost.value = '50';
    elements.econHandlingCost.value = '0';
    elements.econTransportCost.value = '0';
    elements.econTransNow.value = '0';
    elements.econTransLater.value = '0';

    elements.econLossPct.value = '2.0';
    elements.econMarkdownPct.value = '0.0';

    elements.econAnnualRate.value = '0.0';
    elements.econCarryingType.value = 'none';

    markInputsStale();
    onCalculateEconomics();
  }

  function clearEconomicsForm() {
    elements.econForm.reset();
    elements.econOriginStatus.value = 'USER_ENTERED';
    markInputsStale();
    elements.econInitialPrompt.style.display = 'block';
    elements.econMetricsGrid.style.display = 'none';
    elements.rangeResultsBox.style.display = 'none';
    elements.econDisclosuresBox.style.display = 'none';
    if (elements.waterfallCard) elements.waterfallCard.style.display = 'none';
    elements.staleBanner.style.display = 'none';
  }

  // Submit and Evaluate Economics Request
  async function onCalculateEconomics(e) {
    if (e) e.preventDefault();

    const quantity = parseFloat(elements.econQuantity.value);
    const currentPrice = parseFloat(elements.econCurrentPrice.value);

    if (isNaN(quantity) || quantity <= 0) {
      alert('Please enter a valid positive initial quantity in quintals.');
      elements.econQuantity.focus();
      return;
    }
    if (isNaN(currentPrice) || currentPrice <= 0) {
      alert('Please enter a valid positive current spot price in INR/quintal.');
      elements.econCurrentPrice.focus();
      return;
    }

    const futurePoint = elements.econFuturePoint.value.trim() !== ''
      ? parseFloat(elements.econFuturePoint.value)
      : null;
    const futureLower = elements.econFutureLower.value.trim() !== ''
      ? parseFloat(elements.econFutureLower.value)
      : null;
    const futureUpper = elements.econFutureUpper.value.trim() !== ''
      ? parseFloat(elements.econFutureUpper.value)
      : null;
    const horizon = parseInt(elements.econHorizon.value || '7', 10);

    // Build params dict with exact null/number distinction
    const params = {};
    if (elements.econStorageCost.value.trim() !== '') {
      params.storage_cost_per_quintal = parseFloat(elements.econStorageCost.value);
    }
    if (elements.econHandlingCost.value.trim() !== '') {
      params.handling_cost_per_quintal = parseFloat(elements.econHandlingCost.value);
    }
    if (elements.econTransportCost.value.trim() !== '') {
      params.incremental_transport_cost = parseFloat(elements.econTransportCost.value);
    }
    if (elements.econTransNow.value.trim() !== '') {
      params.transaction_cost_now = parseFloat(elements.econTransNow.value);
    }
    if (elements.econTransLater.value.trim() !== '') {
      params.transaction_cost_later = parseFloat(elements.econTransLater.value);
    }

    // Convert percentages to fractions exactly once
    if (elements.econLossPct.value.trim() !== '') {
      params.quantity_loss_fraction = parseFloat(elements.econLossPct.value) / 100.0;
    }
    if (elements.econMarkdownPct.value.trim() !== '') {
      params.quality_discount_fraction = parseFloat(elements.econMarkdownPct.value) / 100.0;
    }
    if (elements.econAnnualRate.value.trim() !== '') {
      params.annual_carrying_rate = parseFloat(elements.econAnnualRate.value) / 100.0;
    }
    params.carrying_cost_type = elements.econCarryingType.value;
    params.holding_period_days = horizon;

    const payload = {
      quantity_quintals: quantity,
      current_price: currentPrice,
      future_price_point: futurePoint,
      future_price_lower: futureLower,
      future_price_upper: futureUpper,
      holding_period_days: horizon,
      origin_date: elements.econOriginDate.value || '2026-11-13',
      origin_provenance_status: elements.econOriginStatus.value || 'USER_ENTERED',
      params: params,
    };

    // Request tokening: avoid out-of-order race conditions
    state.currentEvaluationRequestId += 1;
    const thisRequestId = state.currentEvaluationRequestId;

    elements.econCalcStatus.textContent = 'Calculating...';
    elements.econCalcStatus.style.color = 'var(--color-ink-muted)';
    elements.btnCalcSubmit.disabled = true;

    try {
      const resp = await fetchAPI('/api/v1/economics/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (thisRequestId !== state.currentEvaluationRequestId) return;

      if (resp.status === 'SUCCESS' && resp.data) {
        state.lastEconomicsResult = { request: payload, response: resp.data };
        renderEconomicsResult(resp.data);
        elements.econCalcStatus.textContent = 'Calculation complete.';
        elements.econCalcStatus.style.color = 'var(--color-crop-green)';
        elements.staleBanner.classList.remove('visible');
        elements.staleBanner.style.display = 'none';
        elements.btnExportReceipt.disabled = false;
      }
    } catch (err) {
      if (thisRequestId !== state.currentEvaluationRequestId) return;
      elements.econCalcStatus.textContent = `Error: ${err.message}`;
      elements.econCalcStatus.style.color = 'var(--color-soil-rust)';
    } finally {
      if (thisRequestId === state.currentEvaluationRequestId) {
        elements.btnCalcSubmit.disabled = false;
      }
    }
  }

  function renderEconomicsResult(data) {
    elements.econInitialPrompt.style.display = 'none';
    elements.econMetricsGrid.style.display = 'grid';

    // Gross proceeds
    elements.resGrossProceeds.textContent = formatINR(data.r_sell_gross);

    // Net proceeds
    if (data.r_sell_net !== null && data.r_sell_net !== undefined) {
      elements.resNetProceeds.textContent = formatINR(data.r_sell_net);
    } else {
      elements.resNetProceeds.textContent = 'Unavailable (Missing Cost)';
    }

    // Holding proceeds
    const holdVal = data.r_hold_point_net !== undefined && data.r_hold_point_net !== null
      ? data.r_hold_point_net
      : data.r_hold;
    if (holdVal !== null && holdVal !== undefined) {
      elements.resHoldingProceeds.textContent = formatINR(holdVal);
    } else {
      elements.resHoldingProceeds.textContent = 'Unavailable (Missing Cost)';
    }

    // Delta R (Net Incremental Benefit)
    if (data.delta_r_point !== null && data.delta_r_point !== undefined) {
      const val = data.delta_r_point;
      const prefix = val >= 0 ? '+ ' : '- ';
      elements.resDeltaR.textContent = `${prefix}₹ ${Math.abs(val).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      })}`;
      elements.resDeltaR.className = `result-metric-val tabular ${val >= 0 ? 'positive' : 'negative'}`;
      elements.resDeltaR.style.color = val >= 0 ? 'var(--color-crop-green)' : 'var(--color-soil-rust)';
    } else {
      elements.resDeltaR.textContent = 'Unavailable (Missing Cost)';
      elements.resDeltaR.className = 'result-metric-val tabular';
      elements.resDeltaR.style.color = 'var(--color-ink)';
    }

    // Break-even price
    elements.resBreakeven.textContent = formatINR(data.p_break_even);

    // Range results
    const rLower = data.delta_r_lower != null ? data.delta_r_lower : data.delta_r_min;
    const rUpper = data.delta_r_upper != null ? data.delta_r_upper : data.delta_r_max;
    const req = state.lastEconomicsResult?.request || data.request || {};
    const pLower = req.future_price_lower != null ? req.future_price_lower : req.future_price_min;
    const pUpper = req.future_price_upper != null ? req.future_price_upper : req.future_price_max;

    if (rLower != null && rUpper != null && pLower != null && pUpper != null) {
      elements.rangeResultsBox.style.display = 'block';
      elements.rangeFutureBounds.textContent = `₹ ${pLower} – ₹ ${pUpper}`;
      elements.rangeGainMin.textContent = `₹ ${Number(rLower).toFixed(2)}`;
      elements.rangeGainMax.textContent = `₹ ${Number(rUpper).toFixed(2)}`;
      if (elements.rangeGainPoint && data.delta_r_point != null) {
        elements.rangeGainPoint.textContent = `₹ ${Number(data.delta_r_point).toFixed(2)}`;
      }
    } else {
      elements.rangeResultsBox.style.display = 'none';
    }

    // Render Waterfall Decomposition
    renderWaterfallDecomposition(data);

    // Disclosures list
    elements.econDisclosuresList.innerHTML = '';
    const disclosures = [];
    if (data.disclaimer) disclosures.push(data.disclaimer);
    if (Array.isArray(data.gate_reasons)) disclosures.push(...data.gate_reasons);
    if (Array.isArray(data.missing_cost_inputs) && data.missing_cost_inputs.length > 0) {
      disclosures.push(`Missing parameters: ${data.missing_cost_inputs.join(', ')}`);
    }
    if (disclosures.length > 0) {
      elements.econDisclosuresBox.style.display = 'block';
      disclosures.forEach((disc) => {
        const li = document.createElement('li');
        li.textContent = disc;
        elements.econDisclosuresList.appendChild(li);
      });
    } else {
      elements.econDisclosuresBox.style.display = 'none';
    }
  }

  // Waterfall Decomposition Table Renderer
  function renderWaterfallDecomposition(data) {
    if (!elements.waterfallCard || !elements.waterfallTbody) return;

    if (data.r_sell_gross === null || data.r_sell_gross === undefined) {
      elements.waterfallCard.style.display = 'none';
      return;
    }

    elements.waterfallCard.style.display = 'block';
    elements.waterfallTbody.innerHTML = '';

    const holdVal = data.r_hold_point_net !== undefined && data.r_hold_point_net !== null
      ? data.r_hold_point_net
      : data.r_hold;

    const rows = [
      {
        step: '1. Immediate Gross Sale',
        formula: 'Q × P₀',
        amount: formatINR(data.r_sell_gross),
      },
      {
        step: '2. Spot Transaction Fee',
        formula: '− (Q × t_n)',
        amount: data.immediate_transaction_costs != null ? `− ${formatINR(data.immediate_transaction_costs)}` : '₹ 0.00',
      },
      {
        step: '3. Net Immediate Proceeds',
        formula: 'R_sell,net = Gross − Spot Fee',
        amount: formatINR(data.r_sell_net),
      },
      {
        step: '4. Post-Storage Gross Value',
        formula: 'Q × (1−L)(1−d) × P_H',
        amount: data.gross_storage_proceeds != null ? formatINR(data.gross_storage_proceeds) : (holdVal != null ? formatINR(holdVal + (data.total_direct_costs || 0) + (data.opportunity_cost || 0) + (data.later_transaction_costs || 0)) : 'Unavailable'),
      },
      {
        step: '5. Direct Storage & Handling',
        formula: '− (Q × c)',
        amount: data.total_direct_costs != null ? `− ${formatINR(data.total_direct_costs)}` : 'Unavailable',
      },
      {
        step: '6. Post-Storage Transaction Fee',
        formula: '− (Q(1−L) × t_l)',
        amount: data.later_transaction_costs != null ? `− ${formatINR(data.later_transaction_costs)}` : '₹ 0.00',
      },
      {
        step: '7. Carrying / Financing Cost',
        formula: '− (Q × P₀ × r × T/365)',
        amount: data.opportunity_cost != null ? `− ${formatINR(data.opportunity_cost)}` : '₹ 0.00',
      },
      {
        step: '8. Expected Net Holding Proceeds',
        formula: 'R_hold = Value − Costs − Fees',
        amount: formatINR(holdVal),
      },
      {
        step: '9. Net Incremental Benefit (ΔR)',
        formula: 'R_hold − R_sell,net',
        amount: data.delta_r_point != null ? (data.delta_r_point >= 0 ? `+ ${formatINR(data.delta_r_point)}` : `− ${formatINR(Math.abs(data.delta_r_point))}`) : 'Unavailable',
        isTotal: true,
      },
      {
        step: '10. Break-Even Future Price (P*)',
        formula: 'Target price where ΔR = 0',
        amount: formatINR(data.p_break_even) + ' / q',
      },
    ];

    rows.forEach((r) => {
      const tr = document.createElement('tr');
      if (r.isTotal) tr.className = 'total-row';
      tr.innerHTML = `
        <th scope="row">${r.step}</th>
        <td><code>${r.formula}</code></td>
        <td class="num-cell"><strong>${r.amount}</strong></td>
      `;
      elements.waterfallTbody.appendChild(tr);
    });
  }

  // Download Research Economic Receipt as JSON
  function downloadReceipt() {
    if (!state.lastEconomicsResult) {
      alert('Please perform an economic evaluation before downloading a receipt.');
      return;
    }

    const receipt = {
      receipt_id: 'REC-' + Math.random().toString(36).substring(2, 9).toUpperCase(),
      task_id: 'MP-UI-002',
      generated_at_utc: new Date().toISOString(),
      system_name: 'APMC Mandi Intelligence System',
      software_version: '1.0.0-rc1',
      advisory_status: 'BLOCKED',
      provenance_mode: state.lastEconomicsResult.request.origin_provenance_status,
      evaluation: state.lastEconomicsResult,
    };

    const blob = new Blob([JSON.stringify(receipt, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `apmc_research_receipt_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // DOMContentLoaded Entry
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
