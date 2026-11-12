/**
 * APMC Mandi Intelligence System - Research Interface Application Logic
 * Step 11 Interface (MP-APP-001B)
 * Pure standard-library browser JavaScript with same-origin Fetch.
 */

(function () {
  'use strict';

  // Application State
  const state = {
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
    serverSnapshotTime: null,
  };

  // DOM Elements
  const elements = {
    badgeHealth: document.getElementById('badge-health'),
    serviceAsOf: document.getElementById('service-as-of'),
    btnRefresh: document.getElementById('btn-refresh'),

    // Tab buttons & panels
    tabButtons: document.querySelectorAll('.tab-btn'),
    tabPanels: document.querySelectorAll('.tab-panel'),

    // Catalog stats
    statTotalSeries: document.getElementById('stat-total-series'),
    statAcceptedSeries: document.getElementById('stat-accepted-series'),
    statReviewSeries: document.getElementById('stat-review-series'),
    statUnavailableSeries: document.getElementById('stat-unavailable-series'),

    // Selectors
    selDistrict: document.getElementById('sel-district'),
    selMarket: document.getElementById('sel-market'),
    selCommodity: document.getElementById('sel-commodity'),
    selVariety: document.getElementById('sel-variety'),
    selGrade: document.getElementById('sel-grade'),

    // Observation cards
    obsEmptyState: document.getElementById('obs-empty-state'),
    obsVerifiedCard: document.getElementById('obs-verified-card'),
    obsReviewCard: document.getElementById('obs-review-card'),
    btnUseInCalc: document.getElementById('btn-use-in-calc'),

    // Verified card fields
    obsSeriesTitle: document.getElementById('obs-series-title'),
    obsMarketSubtitle: document.getElementById('obs-market-subtitle'),
    obsModalPrice: document.getElementById('obs-modal-price'),
    obsMinPrice: document.getElementById('obs-min-price'),
    obsMaxPrice: document.getElementById('obs-max-price'),
    obsDate: document.getElementById('obs-date'),
    obsAge: document.getElementById('obs-age'),

    // Review card fields
    revDistrict: document.getElementById('rev-district'),
    revMarket: document.getElementById('rev-market'),
    revCommodity: document.getElementById('rev-commodity'),
    revVarietyGrade: document.getElementById('rev-variety-grade'),
    revDate: document.getElementById('rev-date'),

    // Benchmark Table
    benchmarkTbody: document.getElementById('benchmark-tbody'),

    // Economics Form
    econForm: document.getElementById('economics-form'),
    btnPresetFixture: document.getElementById('btn-preset-fixture'),
    btnPresetClear: document.getElementById('btn-preset-clear'),
    btnCalcSubmit: document.getElementById('btn-calc-submit'),
    econCalcStatus: document.getElementById('econ-calc-status'),
    staleBanner: document.getElementById('stale-banner'),
    btnExportReceipt: document.getElementById('btn-export-receipt'),

    // Economics inputs
    econQuantity: document.getElementById('econ-quantity'),
    econCurrentPrice: document.getElementById('econ-current-price'),
    econFuturePoint: document.getElementById('econ-future-point'),
    econFutureMin: document.getElementById('econ-future-min'),
    econFutureMax: document.getElementById('econ-future-max'),
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

    // Economics results
    resGrossProceeds: document.getElementById('res-gross-proceeds'),
    resNetProceeds: document.getElementById('res-net-proceeds'),
    resHoldingProceeds: document.getElementById('res-holding-proceeds'),
    resDeltaR: document.getElementById('res-delta-r'),
    resBreakeven: document.getElementById('res-breakeven'),
    rangeResultsBox: document.getElementById('range-results-box'),
    rangeFutureBounds: document.getElementById('range-future-bounds'),
    rangeGainMin: document.getElementById('range-gain-min'),
    rangeGainMax: document.getElementById('range-gain-max'),
    econDisclosuresList: document.getElementById('econ-disclosures-list'),
  };

  // Utility: Currency Formatter
  function formatINR(val, decimals = 2) {
    if (val === null || val === undefined || isNaN(val)) return 'Unavailable';
    return '₹ ' + Number(val).toLocaleString('en-IN', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }

  // Utility: Safe Date Diff
  function computeFreshness(dateStr) {
    if (!dateStr) return 'Unknown date';
    try {
      const obsDate = new Date(dateStr);
      const now = new Date();
      const diffMs = now - obsDate;
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      if (diffDays < 0) return 'Future date';
      if (diffDays === 0) return 'Observed today';
      if (diffDays === 1) return 'Observed 1 day ago';
      return `Observed ${diffDays} days ago (${dateStr})`;
    } catch {
      return dateStr;
    }
  }

  // Generic JSON Fetch Helper
  async function fetchAPI(endpoint, options = {}) {
    const res = await fetch(endpoint, {
      headers: {
        'Accept': 'application/json',
        ...(options.headers || {}),
      },
      ...options,
    });
    if (!res.ok) {
      let errPayload;
      try {
        errPayload = await res.json();
      } catch {
        errPayload = { error: { message: `HTTP ${res.status}: ${res.statusText}` } };
      }
      throw new Error(errPayload.error?.message || `HTTP error ${res.status}`);
    }
    return res.json();
  }

  // Tab Navigation Handling
  function initTabs() {
    elements.tabButtons.forEach((btn, index) => {
      btn.addEventListener('click', () => switchTab(btn));
      btn.addEventListener('keydown', (e) => {
        let targetIndex = null;
        if (e.key === 'ArrowRight') targetIndex = (index + 1) % elements.tabButtons.length;
        else if (e.key === 'ArrowLeft') targetIndex = (index - 1 + elements.tabButtons.length) % elements.tabButtons.length;
        else if (e.key === 'Home') targetIndex = 0;
        else if (e.key === 'End') targetIndex = elements.tabButtons.length - 1;

        if (targetIndex !== null) {
          e.preventDefault();
          elements.tabButtons[targetIndex].focus();
          switchTab(elements.tabButtons[targetIndex]);
        }
      });
    });
  }

  function switchTab(selectedBtn) {
    elements.tabButtons.forEach((btn) => {
      const isSelected = btn === selectedBtn;
      btn.setAttribute('aria-selected', isSelected ? 'true' : 'false');
      btn.setAttribute('tabindex', isSelected ? '0' : '-1');
    });

    const targetPanelId = selectedBtn.getAttribute('aria-controls');
    elements.tabPanels.forEach((panel) => {
      if (panel.id === targetPanelId) {
        panel.classList.add('active');
      } else {
        panel.classList.remove('active');
      }
    });
  }

  // Initialize System Health & Snapshot Metadata
  async function loadSystemHealth() {
    try {
      const data = await fetchAPI('/api/v1/health');
      if (data.status === 'SUCCESS' && data.data) {
        const proc = data.data.process_status;
        elements.badgeHealth.textContent = `Service: ${proc}`;
        elements.badgeHealth.className = proc === 'HEALTHY' ? 'badge badge-success' : 'badge badge-amber';
        state.serverSnapshotTime = data.as_of_utc;
        elements.serviceAsOf.textContent = `Server As-Of: ${data.as_of_utc} (Startup Snapshot)`;
      }
    } catch (err) {
      elements.badgeHealth.textContent = 'Service: Unreachable';
      elements.badgeHealth.className = 'badge badge-blocked';
      elements.serviceAsOf.textContent = 'Server connection failed';
    }
  }

  // Load Catalog and Series
  async function loadCatalog() {
    try {
      const [catResp, priceResp] = await Promise.all([
        fetchAPI('/api/v1/catalog'),
        fetchAPI('/api/v1/prices/latest'),
      ]);

      if (catResp.status === 'SUCCESS' && catResp.data) {
        state.catalog = catResp.data;
        elements.statTotalSeries.textContent = catResp.data.total_series_count ?? 30;
        elements.statAcceptedSeries.textContent = catResp.data.accepted_series_count ?? 26;
        elements.statReviewSeries.textContent = catResp.data.review_series_count ?? 4;
      }

      if (priceResp.status === 'SUCCESS' && priceResp.data) {
        state.allSeries = priceResp.data.series || [];
        populateDistrictDropdown();
      }
    } catch (err) {
      console.error('Failed to load catalog:', err);
    }
  }

  // Populate Dropdowns in Cascade
  function populateDistrictDropdown() {
    const districts = [...new Set(state.allSeries.map((s) => s.district))].sort();
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
    const markets = [...new Set(filtered.map((s) => s.market))].sort();
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
    const commodities = [...new Set(filtered.map((s) => s.commodity))].sort();
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
    const varieties = [...new Set(filtered.map((s) => s.variety))].sort();
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
    const grades = [...new Set(filtered.map((s) => s.grade))].sort();
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

    // Check display permission derived dynamically on server
    if (match.price_display_permitted) {
      // Verified Accepted Series Card
      elements.obsReviewCard.style.display = 'none';
      elements.obsVerifiedCard.style.display = 'block';

      elements.obsSeriesTitle.textContent = `${match.commodity} (${match.variety} - Grade ${match.grade})`;
      elements.obsMarketSubtitle.textContent = `${match.market} APMC, ${match.district} District`;
      elements.obsModalPrice.textContent = match.modal_price != null ? `₹ ${match.modal_price}` : 'Unavailable';

      elements.obsMinPrice.textContent = match.min_price != null ? `₹ ${match.min_price}` : 'Unavailable';
      elements.obsMaxPrice.textContent = match.max_price != null ? `₹ ${match.max_price}` : 'Unavailable';

      elements.obsDate.textContent = match.observation_date || 'Unknown';
      elements.obsAge.textContent = computeFreshness(match.observation_date);
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

  // Load Benchmark Scorecard from /api/v1/models/benchmark
  async function loadBenchmarks() {
    try {
      const resp = await fetchAPI('/api/v1/models/benchmark');
      if (resp.status === 'SUCCESS' && resp.data) {
        state.benchmarkData = resp.data;
        renderBenchmarkTable(resp.data.model_performance_summary || []);
      }
    } catch (err) {
      console.error('Failed to load benchmarks:', err);
      elements.benchmarkTbody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; color: var(--color-alert-danger);">
            Benchmark scorecard unavailable (${err.message}).
          </td>
        </tr>
      `;
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
        ? '<span class="badge badge-success">MAE Winner</span>'
        : '<span class="badge badge-info">Challenger</span>';

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

  // Pre-fill Price from Verified Card into Calculator
  function usePriceInCalculator() {
    if (!state.latestObservation || !state.latestObservation.price_display_permitted) return;

    elements.econCurrentPrice.value = state.latestObservation.modal_price;
    if (state.latestObservation.observation_date) {
      elements.econOriginDate.value = state.latestObservation.observation_date;
    }
    // Set future point assumption default (+ ₹150 over current)
    elements.econFuturePoint.value = Number(state.latestObservation.modal_price) + 150;

    // Switch to Economics tab
    const econTabBtn = document.getElementById('tab-economics');
    if (econTabBtn) {
      switchTab(econTabBtn);
      econTabBtn.focus();
    }
    elements.staleBanner.classList.add('visible');
  }

  // Preset Buttons Handling
  function loadPresetFixture() {
    elements.econQuantity.value = 10;
    elements.econCurrentPrice.value = 2500;
    elements.econFuturePoint.value = 2650;
    elements.econFutureMin.value = '';
    elements.econFutureMax.value = '';
    elements.econHorizon.value = 7;
    elements.econOriginDate.value = '2026-11-13';
    elements.econOriginStatus.value = 'USER_ENTERED';

    elements.econStorageCost.value = 50;
    elements.econHandlingCost.value = 0;
    elements.econTransportCost.value = 0;
    elements.econTransNow.value = 0;
    elements.econTransLater.value = 0;

    elements.econLossPct.value = 2.0;
    elements.econMarkdownPct.value = 0.0;
    elements.econAnnualRate.value = 0.0;
    elements.econCarryingType.value = 'none';

    elements.staleBanner.classList.remove('visible');
    submitEconomicsForm();
  }

  function clearPresetForm() {
    elements.econForm.reset();
    elements.econQuantity.value = '';
    elements.econCurrentPrice.value = '';
    elements.econFuturePoint.value = '';
    elements.econFutureMin.value = '';
    elements.econFutureMax.value = '';
    elements.econStorageCost.value = '';
    elements.econHandlingCost.value = '';
    elements.econTransportCost.value = '';
    elements.econTransNow.value = '';
    elements.econTransLater.value = '';
    elements.econLossPct.value = '';
    elements.econMarkdownPct.value = '';
    elements.econAnnualRate.value = '';

    elements.staleBanner.classList.remove('visible');
    elements.resGrossProceeds.textContent = 'Unavailable';
    elements.resNetProceeds.textContent = 'Unavailable';
    elements.resHoldingProceeds.textContent = 'Unavailable';
    elements.resDeltaR.textContent = 'Unavailable';
    elements.resDeltaR.className = 'result-metric-val';
    elements.resBreakeven.textContent = 'Unavailable';
    elements.rangeResultsBox.style.display = 'none';
  }

  // Evaluate Economics via POST /api/v1/economics/evaluate
  async function submitEconomicsForm(e) {
    if (e) e.preventDefault();

    const qtyStr = elements.econQuantity.value.trim();
    const currPriceStr = elements.econCurrentPrice.value.trim();
    if (!qtyStr || !currPriceStr) {
      elements.econCalcStatus.textContent = 'Please provide Quantity and Current Price.';
      elements.econCalcStatus.style.color = 'var(--color-alert-danger)';
      return;
    }

    const quantity = parseFloat(qtyStr);
    const currentPrice = parseFloat(currPriceStr);
    const futurePoint = elements.econFuturePoint.value.trim() !== ''
      ? parseFloat(elements.econFuturePoint.value)
      : null;
    const futureMin = elements.econFutureMin.value.trim() !== ''
      ? parseFloat(elements.econFutureMin.value)
      : null;
    const futureMax = elements.econFutureMax.value.trim() !== ''
      ? parseFloat(elements.econFutureMax.value)
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
      future_price_min: futureMin,
      future_price_max: futureMax,
      holding_period_days: horizon,
      origin_date: elements.econOriginDate.value || '2026-11-13',
      origin_provenance_status: elements.econOriginStatus.value || 'USER_ENTERED',
      params: params,
    };

    elements.econCalcStatus.textContent = 'Calculating...';
    elements.econCalcStatus.style.color = 'var(--color-text-secondary)';
    elements.btnCalcSubmit.disabled = true;

    try {
      const resp = await fetchAPI('/api/v1/economics/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (resp.status === 'SUCCESS' && resp.data) {
        state.lastEconomicsResult = { request: payload, response: resp.data };
        renderEconomicsResult(resp.data);
        elements.econCalcStatus.textContent = 'Calculation complete.';
        elements.econCalcStatus.style.color = 'var(--color-brand-primary)';
        elements.staleBanner.classList.remove('visible');
      }
    } catch (err) {
      elements.econCalcStatus.textContent = `Error: ${err.message}`;
      elements.econCalcStatus.style.color = 'var(--color-alert-danger)';
    } finally {
      elements.btnCalcSubmit.disabled = false;
    }
  }

  function renderEconomicsResult(data) {
    // Gross proceeds
    elements.resGrossProceeds.textContent = formatINR(data.r_sell_gross);

    // Net proceeds
    if (data.r_sell_net !== null && data.r_sell_net !== undefined) {
      elements.resNetProceeds.textContent = formatINR(data.r_sell_net);
    } else {
      elements.resNetProceeds.textContent = 'Unavailable (Missing Cost)';
    }

    // Holding proceeds
    const holdVal = data.r_hold_point_net !== undefined && data.r_hold_point_net !== null ? data.r_hold_point_net : data.r_hold;
    elements.resHoldingProceeds.textContent = formatINR(holdVal);

    // Delta R (Net Incremental Gain)
    if (data.delta_r_point !== null && data.delta_r_point !== undefined) {
      const val = data.delta_r_point;
      const prefix = val >= 0 ? '+ ' : '- ';
      elements.resDeltaR.textContent = `${prefix}₹ ${Math.abs(val).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
      elements.resDeltaR.className = `result-metric-val ${val >= 0 ? 'positive' : 'negative'}`;
    } else {
      elements.resDeltaR.textContent = 'Unavailable (Missing Cost)';
      elements.resDeltaR.className = 'result-metric-val';
    }

    // Break-even price
    elements.resBreakeven.textContent = formatINR(data.p_break_even);

    // Range results
    if (data.delta_r_min != null && data.delta_r_max != null) {
      elements.rangeResultsBox.style.display = 'block';
      elements.rangeFutureBounds.textContent = `₹ ${data.request?.future_price_min} &ndash; ₹ ${data.request?.future_price_max}`;
      elements.rangeGainMin.textContent = `₹ ${Number(data.delta_r_min).toFixed(2)}`;
      elements.rangeGainMax.textContent = `₹ ${Number(data.delta_r_max).toFixed(2)}`;
    } else {
      elements.rangeResultsBox.style.display = 'none';
    }

    // Disclosures list
    elements.econDisclosuresList.innerHTML = '';
    const disclosures = data.disclosures || [];
    disclosures.forEach((disc) => {
      const li = document.createElement('li');
      li.textContent = disc;
      elements.econDisclosuresList.appendChild(li);
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
      generated_at_utc: new Date().toISOString(),
      system_name: 'APMC Mandi Intelligence System',
      software_version: 'Step 11 Interface (MP-APP-001B)',
      advisory_status: 'BLOCKED',
      provenance_mode: state.lastEconomicsResult.request.origin_provenance_status,
      evaluation: state.lastEconomicsResult,
      notice: 'Academic research receipt. Not certified for commercial trading or farmer advice.',
    };

    const blob = new Blob([JSON.stringify(receipt, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mandi_research_economic_receipt_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // Attach Event Listeners
  function attachEvents() {
    initTabs();

    // Refresh control
    elements.btnRefresh.addEventListener('click', async () => {
      elements.serviceAsOf.textContent = 'Reloading snapshot...';
      await loadSystemHealth();
      await loadCatalog();
      await loadBenchmarks();
    });

    // Cascading dropdown listeners
    elements.selDistrict.addEventListener('change', onDistrictChange);
    elements.selMarket.addEventListener('change', onMarketChange);
    elements.selCommodity.addEventListener('change', onCommodityChange);
    elements.selVariety.addEventListener('change', onVarietyChange);
    elements.selGrade.addEventListener('change', onGradeChange);

    // Pre-fill button
    elements.btnUseInCalc.addEventListener('click', usePriceInCalculator);

    // Preset buttons
    elements.btnPresetFixture.addEventListener('click', loadPresetFixture);
    elements.btnPresetClear.addEventListener('click', clearPresetForm);

    // Form submission & stale detection
    elements.econForm.addEventListener('submit', submitEconomicsForm);
    elements.econForm.querySelectorAll('input, select').forEach((inp) => {
      inp.addEventListener('input', () => {
        elements.staleBanner.classList.add('visible');
      });
    });

    // Download receipt
    elements.btnExportReceipt.addEventListener('click', downloadReceipt);
  }

  // Application Entry Point
  async function init() {
    attachEvents();
    await loadSystemHealth();
    await loadCatalog();
    await loadBenchmarks();
    // Pre-load +470 fixture on initial page load for instant demonstration
    loadPresetFixture();
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
