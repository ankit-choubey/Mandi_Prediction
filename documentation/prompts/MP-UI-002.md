# MP-UI-002 — Research Instrument Interface Redesign

## Role and objective

You are working in the existing `Mandi_Prediction` repository. Redesign the already functional research interface into a distinctive, professor-ready **agricultural price research instrument**, not a generic admin dashboard and not a fictional trading terminal. Complete the implementation, tests, evidence, documentation, commit, and push in this single task.

The UI must make the real project legible in this order:

1. what was actually observed;
2. how trustworthy and fresh that observation is;
3. what the frozen retrospective models achieved;
4. how uncertainty behaved across folds;
5. what the user-entered hold-versus-sell mathematics computes;
6. what is unavailable or still scientifically unproven.

Do not retrain models, run Kaggle, create synthetic operational data, call an external market API, invent historical prices, activate Docker, deploy publicly, install frontend frameworks, or alter accepted mathematical definitions.

## Required reading before editing

Read completely:

- `documentation/RELEASE001R_INDEPENDENT_REVIEW.md`
- `documentation/MODEL_AND_MATH_VALIDATION.md`
- `documentation/PROJECT_EXECUTION_LEDGER.md`
- `documentation/PROFESSOR_PROGRESS_BRIEF.md`
- `documentation/RELEASE_RUNBOOK.md`
- `src/static/index.html`
- `src/static/styles.css`
- `src/static/app.js`
- `src/api.py`, `src/service.py`, `src/service_contracts.py`, `src/economic_model.py`
- the verified FC007 and FC008 report CSVs actually consumed by the service
- the current browser/integration tests and prior APP001B/RELEASE001 evidence

Preserve all unrelated dirty and untracked work. Never edit or stage `documentation/context.md`. Update ignored `brain/context.md`.

## Visual direction

Build a calm, editorial scientific interface inspired by an agricultural field notebook, a statistical report, and a precision instrument panel. Avoid the common AI-dashboard look: no excessive gradient blobs, glass cards, glowing neon, fake command-center labels, ornamental circuitry, meaningless animated dots, or a wall of equal-weight cards.

Use:

- warm paper/off-white background;
- deep ink text;
- restrained crop green, turmeric/ochre, soil/rust, and slate accents;
- serif display typography paired with a highly readable system sans and tabular numerals;
- thin rules, quiet surfaces, deliberate whitespace, asymmetric editorial composition;
- a small amount of purposeful motion only for state transitions, respecting `prefers-reduced-motion`;
- locally available/system fonts only—no Google Fonts, Tailwind CDN, icon CDN, or network dependency;
- simple inline/local SVG icons and data graphics where useful, with accessible labels.

Do not generate decorative raster imagery merely to fill space. Prefer CSS and SVG because the visual should remain sharp, reproducible, lightweight, and data-bound. If an illustration is added, it must be a small original local SVG with no invented empirical content.

## Information architecture

Replace the current generic tab-dashboard feeling with a responsive research narrative. A compact navigation rail or top index may switch sections, but the page should still read coherently when scrolled.

### 1. Research masthead

Show project name, a plain-language subtitle, dataset mode, service health, calendar, snapshot timestamp, and the research-only/advice-blocked status. Use exact API values. Say **Imported snapshot** or **Dataset mode**, never `LIVE`, `real time`, `telemetry`, or an equivalent unless a genuinely live source is later connected and verified.

Show a compact reproducibility drawer containing only real identifiers available to the UI/API. Never expose local paths, secrets, or invent shortened hashes. If a required hash is not exposed by a safe endpoint, show `Not exposed in this runtime` rather than hard-code it.

### 2. Observation workspace — primary screen

Make exact series selection the main interaction, not a secondary form. Preserve the five-part cascade: district, market, commodity, variety, grade. Preserve the prohibition on silent first-match selection.

After selection, present one strong observation composition:

- modal price as the dominant number with `INR/quintal`;
- min and max price if truly present;
- observation date and India-calendar age;
- district, canonical market, raw market, commodity, variety, grade;
- source/import mode and acceptance disposition;
- clear permitted/withheld state;
- a plain explanation of why active advice is blocked.

The four review identities must remain visibly separated and their prices withheld. Do not make them look verified.

### 3. Price movement panel — truth-preserving

The owner wants price change visible, but the current accepted service does not provide verified historical series or a continuously updating feed. Therefore implement the component with capability-aware states:

- If the backend supplies two or more real dated observations for the exact series, compute and display the absolute and percentage change with both dates and units.
- If only the current imported observation exists, display: `Price change unavailable — a second verified observation is required.`
- A browser-session comparison may be shown only after a later snapshot refresh produces a genuinely different observation date for the same exact series. Label it `Change between imported snapshots`, never market trend.
- Never derive movement from min/max spread, model predictions, fixture values, or invented previous prices.
- Do not add a fake chart. An unavailable chart state is the correct output when history is unavailable.

If implementing genuine change would require a new backend endpoint or source not already in the repository, do not expand scope silently. Keep the honest unavailable state and record the exact future data contract needed.

### 4. Model evidence studio

Render the verified point-model comparison from the backend, not literals in the page:

- Persistence/naive: MAE `106.9553697357`, RMSE `298.8336641813`;
- Ridge and HGB values from the service/report;
- make it obvious that HGB is worse on primary MAE but better on RMSE;
- use the exact point evaluation population and distinguish it from the interval population;
- explain MAE and RMSE in one sentence each without claiming causal outlier mitigation or variance reduction.

Create an accessible SVG or HTML comparison graphic with a table fallback. Use a zero or clearly declared scale origin. Provide exact values in text; do not encode meaning by color alone.

### 5. Uncertainty laboratory

Show the 90% and 95% empirical coverage, interval widths, issued-origin count, series count, and fold evidence from the backend. F2/F3/F4 must remain neutral fold identifiers. Explicitly show F1 abstention/no calibration. Clearly state:

- intervals are retrospective empirical calibration outputs;
- exchangeability and distribution-free future coverage are not guaranteed;
- F3/F4 undercoverage is observed, but its cause is unresolved;
- overall coverage is dominated by F2 and must not hide fold-level deterioration.

Use a coverage target marker and observed bars/dots, with exact screen-reader text and a table fallback. Do not label folds calm, volatile, crisis, or any causal regime.

### 6. Hold-versus-sell mathematics workbench

Keep the existing API-backed calculator and all accepted contracts. Improve layout so that inputs, provenance, formula, and outputs are visually connected.

Show the canonical equations with definitions:

`R_sell = Q(p0 - tn)`

`R_hold = Q[(1-L)((1-d)pH - tl) - c - p0 f]`

`Delta R = R_hold - R_sell`

and the accepted break-even expression from the validation record. Render accessible HTML/math text; do not require a remote math library.

Requirements:

- blank remains different from numeric zero;
- no cost defaults are silently assumed;
- financing and opportunity carrying modes remain distinct;
- user-entered provenance is never presented as observed;
- preserve the +470 fixture, 7% financing `436.438356...`, and lower/point/upper `-20 / 470 / 960` controls;
- retain gross/net separation and incomplete-parameter nulls;
- keep `advisory_action = BLOCKED` prominent but not alarmist;
- display a result decomposition/waterfall only from returned API components, with a textual table fallback;
- receipt download must remain functional and truthful.

### 7. Evidence and limitations appendix

Provide an expandable section with:

- observed/imported/synthetic/user-entered legend;
- current model and interval scopes;
- accepted versus review series counts;
- commercial tariff status: local directory has 0 received quotations out of 22 entries, not proof that tariffs do not exist anywhere;
- prospective performance unobserved;
- forecast/history endpoint availability;
- current Step 13 status;
- concise professor-demo narrative.

Do not expose internal filesystem paths or overwhelm the default view; use disclosure panels.

## Responsive and accessibility requirements

- Desktop target: 1440x900 and 1280x800.
- Tablet target: 768px wide.
- Mobile targets: 375x667 and 390x844.
- No horizontal page overflow at any target.
- Controls at least 44px high where practical.
- Keyboard-only operation for every selection, navigation item, disclosure, calculator control, refresh, and receipt action.
- Visible focus indicator; logical focus order; skip link; semantic headings/landmarks.
- Proper form labels, descriptions, error association, `aria-live` only for meaningful async updates.
- WCAG AA contrast for normal text and critical states.
- Do not rely on red/green alone.
- Print stylesheet for a clean professor evidence handout: selected observation, model evidence, uncertainty, calculator result, provenance, timestamp, and limitations; hide interactive-only controls.

## Engineering constraints

- Remain vanilla HTML/CSS/JavaScript served by the standard-library backend.
- No npm, bundler, framework, CDN, tracking, analytics, external font, or external asset request.
- Same-origin API only.
- No model or score changes.
- Do not hard-code values already available from the backend.
- If a presentation value is not currently returned, prefer a labelled unavailable state. Add a narrow read-only endpoint only when the value already exists in verified tracked artifacts and the endpoint can be tested for exact parity.
- Keep release launcher and Docker configuration working.
- Keep page weight small and startup fast; report actual measured HTML/CSS/JS/SVG byte sizes and browser-load timing scope without claiming network performance.
- Sanitize any displayed text and avoid unsafe `innerHTML` for API data.

## Real-browser acceptance matrix

Run a real browser against a temporary loopback service and verify, at minimum:

1. page loads with zero console errors and zero failed network requests;
2. no external network requests are made;
3. district → market → commodity → variety → grade keyboard cascade works;
4. Lucknow/Banthara/Wheat/Dara/FAQ shows the actual current API observation and date;
5. review identities never expose a price;
6. price-change component correctly renders unavailable with one observation;
7. benchmark screen values exactly match API/source reports;
8. interval overall and fold values exactly match API/source reports;
9. +470 fixture passes;
10. financing 7% result rounds from the exact API value and is not recomputed differently in the DOM;
11. lower/point/upper results are -20/470/960 for the accepted control;
12. omitted versus zero inputs remain distinct;
13. receipt download produces valid JSON matching the visible result;
14. refresh preserves or safely resets selection without stale mismatched data;
15. 1440, 1280, 768, 390, and 375 widths have no horizontal overflow;
16. keyboard navigation and focus order pass a manual trace;
17. reduced-motion preference removes nonessential animation;
18. print preview is readable and includes limitations;
19. service degraded mode renders honestly without crashing;
20. all existing browser flows and review gates remain green.

Use screenshots as supporting evidence, not as the test itself. Save desktop, mobile, and print evidence. Record viewport dimensions in the receipt.

## Test and evidence requirements

- Run the complete `tests/` and `backing/` suites.
- Run the original 29 review gates unchanged.
- Run the existing 21 browser flows; extend rather than weaken them.
- Add focused UI contract tests for every new truth-preserving state.
- Test a clean tracked-only export so the UI does not depend on ignored private data.
- Record exact pass/fail/skip/warning counts and commands.
- Create `experiments/reports/UI002/` with a self-excluding SHA-256 manifest, browser acceptance receipt, API-to-DOM parity receipt, accessibility/keyboard receipt, responsive receipt, asset/network receipt, screenshots, and summary.
- Never describe a substring/static-source check as a real browser interaction.
- Do not rewrite historical receipts.

## Documentation and state updates

Update:

- `documentation/MODEL_AND_MATH_VALIDATION.md`
- `documentation/PROJECT_EXECUTION_LEDGER.md`
- `documentation/PROFESSOR_PROGRESS_BRIEF.md`
- ignored `brain/context.md`

Record that UI002 is a presentation refinement under accepted Step 11, not an additional canonical milestone and not completion of Step 13. Preserve every limitation concerning imported snapshot mode, absent historical movement, unresolved interval undercoverage, prospective performance, and commercial costs.

## Stop conditions

Stop and report instead of fabricating if:

- required data for a chart or change metric does not exist;
- a real browser cannot be run;
- the API and verified artifact disagree;
- completing an item would require model retraining, synthetic operational data, an external API, new paid infrastructure, Docker activation, or public deployment.

An honest unavailable component is an acceptable and required result. Do not create placeholder empirical values.

## Delivery

Stage only files intentionally changed for UI002. Check for secrets and unrelated dirty work. Commit with:

`feat(ui): redesign research evidence interface [MP-UI-002]`

Push normally to `origin/main` only after all acceptance checks pass. Finish with:

- exact commit SHA and GitHub verification;
- achieved versus required table;
- tests and browser evidence;
- asset/network measurements;
- screenshots and report paths;
- limitations and deferred items;
- milestone accounting: Step 13 remains the one unfinished canonical research milestone; Docker smoke remains a separate optional infrastructure acceptance check; arrivals and weather remain the two optional ablations.
