// ═══════════════════════════════════════════════════════════════
//  SHPSv2 — main.js
//  SHPS v2.0 | Structural Health Prediction System
// ═══════════════════════════════════════════════════════════════

// ─── Chart.js Global Defaults ──────────────────────────────────
Chart.defaults.color = '#acaaae';
Chart.defaults.borderColor = 'rgba(72, 71, 75, 0.15)';
Chart.defaults.font.family = "'Space Grotesk', sans-serif";

// ─── Constants ──────────────────────────────────────────────────
const COLORS = {
    primary:     '#3b82f6',
    primaryDim:  'rgba(59, 130, 246, 0.12)',
    secondary:   '#8eff71',
    error:       '#f87171',
    warning:     '#fb923c',
    outline:     '#48474b',
    surface:     '#131316',
    onSurface:   '#acaaae',
};

// ─── State ──────────────────────────────────────────────────────
let forecastChart   = null;
let shapChart       = null;
let baseHealthScore = null;  // Set after each full predict call
let lastWhatIfScore = null;  // Tracks what value to diff against

let currentInputs = null;
let currentPredictData = null;
let currentForecastData = null;
let currentExplainData = null;
let currentWhatIfData = null;

// ─── Helpers ────────────────────────────────────────────────────
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    };
}

const updateText = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = val;
};

// ─── Gauge Updater ──────────────────────────────────────────────
// Circumference = 2 * π * 96 ≈ 603.2
const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 96;

function updateGauge(score) {
    const ring = document.getElementById('gauge_val');
    if (!ring) return;

    // score = 0 → full offset (empty), score = 100 → offset 0 (full)
    const offset = GAUGE_CIRCUMFERENCE * (1 - (score / 100));
    ring.style.strokeDashoffset = offset;

    // Colour the ring based on health
    if (score > 80) {
        ring.style.stroke = COLORS.secondary;  // Green — Good
    } else if (score >= 50) {
        ring.style.stroke = COLORS.warning;    // Orange — Fair
    } else {
        ring.style.stroke = COLORS.error;      // Red — Critical
    }
}

// ─── Simulate Data ──────────────────────────────────────────────
async function simulateData() {
    try {
        const res  = await fetch('/simulate');
        const data = await res.json();

        // Fill both desktop and mobile forms
        const fieldMap = {
            'construction_year':  ['construction_year',   'm_construction_year'],
            'last_inspection_year':['last_inspection_year','m_last_inspection_year'],
            'concrete_grade_mpa': ['concrete_grade_mpa',  'm_concrete_grade_mpa'],
            'elevation_m':        ['elevation_m',          'm_elevation_m'],
            'load_kn':            ['load_kn',              'm_load_kn'],
            'cyclic_load_freq':   ['cyclic_load_freq',     'm_cyclic_load_freq'],
            'support_type':       ['support_type',         'm_support_type'],
            'env_condition':      ['env_condition',        'm_env_condition'],
            'vibration_mms':      ['vibration_mms',        'm_vibration_mms'],
        };

        for (const [key, ids] of Object.entries(fieldMap)) {
            ids.forEach(id => {
                const el = document.getElementById(id);
                if (el && data[key] !== undefined) el.value = data[key];
            });
        }

        // Also sync the whatif slider to the new load_kn
        const slider  = document.getElementById('whatif_load_kn');
        const display = document.getElementById('whatif_load_display');
        if (slider && data.load_kn) {
            slider.value = data.load_kn;
            if (display) display.innerText = `${data.load_kn} kN`;
        }

        refreshUI();
    } catch (err) {
        console.error('[SHPSv2] Simulation failed:', err);
    }
}

// ─── Get Form Data ───────────────────────────────────────────────
function getFormData(prefix = '') {
    const get = (id) => document.getElementById(prefix + id);
    return {
        construction_year:   parseInt(get('construction_year')?.value   || 2005),
        last_inspection_year:parseInt(get('last_inspection_year')?.value || 2020),
        concrete_grade_mpa:  parseInt(get('concrete_grade_mpa')?.value  || 35),
        elevation_m:         parseFloat(get('elevation_m')?.value       || 25),
        load_kn:             parseFloat(get('load_kn')?.value           || 1500),
        cyclic_load_freq:    parseFloat(get('cyclic_load_freq')?.value  || 120),
        support_type:        parseInt(get('support_type')?.value        || 2),
        env_condition:       parseInt(get('env_condition')?.value       || 2),
        vibration_mms:       parseFloat(get('vibration_mms')?.value     || 3.5),
    };
}

// ─── Main Refresh ────────────────────────────────────────────────
async function refreshUI() {
    const formData = getFormData();

    // Show loading state on key elements
    ['health_score_val'].forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.innerText = '...'; el.classList.add('loading'); }
    });

    try {
        // Predict + Explain are critical — fail loudly if either errors
        const [predictRes, explainRes] = await Promise.all([
            fetch('/predict', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(formData)
            }),
            fetch('/explain', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(formData)
            })
        ]);

        // Error handling for non-OK responses (e.g., 422 Validation Error)
        if (!predictRes.ok || !explainRes.ok) {
            const errData = await predictRes.json();
            const errMsg = errData.details ? errData.details[0].msg : (errData.error || "Analysis failed");
            showValidationError(errMsg);
            return;
        }

        const predictData = await predictRes.json();
        const explainData = await explainRes.json();

        // Remove loading classes
        document.querySelectorAll('.loading').forEach(el => el.classList.remove('loading'));

        updatePredictionUI(predictData, formData);
        updateShapChart(explainData);

        // Forecast is optional — fetch independently and handle gracefully
        fetch('/forecast', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(formData)
        }).then(r => r.json()).then(forecastData => {
            if (!forecastData.unavailable) {
                updateForecastChart(forecastData);
                currentForecastData = forecastData;
            } else {
                const canvas = document.getElementById('forecastChart');
                if (canvas) {
                    const ctx = canvas.getContext('2d');
                    if (forecastChart) { forecastChart.destroy(); forecastChart = null; }
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    ctx.fillStyle = '#acaaae';
                    ctx.font = '12px monospace';
                    ctx.textAlign = 'center';
                    ctx.fillText('Forecast offline — run models/train_lstm.py', canvas.width / 2, canvas.height / 2);
                }
            }
        }).catch(() => {});

        const forecastData = { years: [], deterioration: [], confidence_upper: [], confidence_lower: [] };

        currentInputs = formData;
        currentPredictData = predictData;
        currentExplainData = explainData;

        baseHealthScore = predictData.health_score;
        lastWhatIfScore = predictData.health_score;

        // Sync slider
        const loadEl    = document.getElementById('load_kn');
        const sliderEl  = document.getElementById('whatif_load_kn');
        const displayEl = document.getElementById('whatif_load_display');
        if (loadEl && sliderEl) {
            sliderEl.value = loadEl.value;
            if (displayEl) displayEl.innerText = `${loadEl.value} kN`;
        }
        updateText('whatif_delta_val', '±0.0<span class="text-sm font-medium text-on-surface pl-1">%</span>');
        updateText('whatif_health_display', predictData.health_score.toFixed(1) + '%');
        updateText('whatif_condition', `Current: ${predictData.condition}`);

    } catch (err) {
        console.error('[SHPSv2] Refresh failed:', err);
        showValidationError("Inference logic offline. Review cross-node connectivity or container status.", false);
    } finally {
        document.querySelectorAll('.loading').forEach(el => el.classList.remove('loading'));
    }
}

function showValidationError(msg, isPhysics = true) {
    const title = isPhysics ? "Physics Constraint Violation" : "System Integrity Error";
    const icon  = isPhysics ? "warning" : "hub";
    
    // Clear loading indicators
    document.querySelectorAll('.loading').forEach(el => {
        el.innerText = 'ERR';
        el.classList.remove('loading');
    });

    // Display error in the log
    const logEl = document.getElementById('analysis_log_text');
    if (logEl) {
        logEl.innerHTML = `<div class="p-4 bg-error/10 border border-error/20 rounded-lg fade-in">
            <h4 class="text-error font-bold font-headline uppercase text-xs mb-1 flex items-center gap-2 tracking-widest">
                <span class="material-symbols-outlined text-sm">${icon}</span>
                ${title}
            </h4>
            <p class="text-on-background text-sm leading-relaxed">${msg.replace('Value error, ', '')}</p>
        </div>`;
    }

    // Reset markers
    updateText('analysis_risk',   isPhysics ? 'CRITICAL' : 'OFFLINE');
    updateText('analysis_stress', isPhysics ? 'OUT OF BOUNDS' : 'UNSTABLE');
    updateText('rul_display_full', isPhysics ? 'N/A — Logic Conflict' : 'N/A — System Offline');

    // Update safety badge
    const badge = document.getElementById('safety_status_badge');
    if (badge) {
        badge.innerText = isPhysics ? "UNSTABLE DATA" : "NODE DISCONNECTED";
        badge.style.color = COLORS.error;
        badge.style.borderColor = `${COLORS.error}40`;
    }

    // Update gauge to 0
    updateGauge(0);
}

// ─── Prediction UI ───────────────────────────────────────────────
function updatePredictionUI(data, formData) {
    const score = data.health_score;

    // Health score number
    updateText('health_score_val', score.toFixed(1));

    // Update gauge ring
    updateGauge(score);

    // Condition + colour
    const condColor = data.priority_color; // SSOT from backend

    const condEl = document.getElementById('condition_label');
    if (condEl) {
        condEl.innerText = `Condition: ${data.condition}`;
        condEl.style.color = condColor;
    }

    // Safety status badge
    const badge = document.getElementById('safety_status_badge');
    if (badge) {
        badge.innerText = data.safety_status;
        badge.style.color = condColor;
        badge.style.borderColor = `${condColor}40`;
    }

    // Status pulse dot
    const pulse = document.getElementById('status_pulse');
    if (pulse) {
        pulse.style.background = condColor;
        pulse.style.boxShadow  = `0 0 8px ${condColor}CC`;
    }

    // System status label
    updateText('system_status_label', `System Active // ${data.safety_status}`);

    // RUL
    const rul    = data.RUL_years.toFixed(1);
    const margin = data.margin.toFixed(1); // SSOT margin from backend
    updateText('rul_years',           rul + ' yr');
    updateText('rul_mini',            rul + ' yr');
    updateText('rul_confidence',      `Confidence: ±${margin} Yrs`);
    updateText('rul_confidence_mini', `±${margin} yr`);
    updateText('rul_display_full',    data.RUL_display);

    // Load card
    if (formData) {
        updateText('load_card_val', `${formData.load_kn} kN`);
    }

    // Maintenance action
    applyMaintenanceAction(data);

    // Technical Analysis Log
    updateAnalysisLog(data);

    // Command Queue
    updateCommandQueue(data);
}

// ─── Maintenance Action Card ─────────────────────────────────────
function applyMaintenanceAction(data) {
    const box   = document.getElementById('maintenance_action_box');
    const label = document.getElementById('maintenance_action_label');
    const title = document.getElementById('action_title');
    if (!box || !label || !title) return;

    label.innerText = data.maintenance_action.label;
    title.innerText = 'Action Required';

    // Reset classes first
    box.className = 'bg-surface border border-outline/20 p-5 rounded-xl border-l-[3px] transition-all duration-500';

    if (data.maintenance_action.color === 'green') {
        box.classList.add('border-l-secondary');
        title.style.color = COLORS.secondary;
        label.style.color = '#d1fae5';
    } else if (data.maintenance_action.color === 'orange') {
        box.classList.add('border-l-warning');
        title.style.color = COLORS.warning;
        label.style.color = '#fed7aa';
    } else {
        box.classList.add('border-l-error');
        box.style.background = 'rgba(248,113,113,0.04)';
        title.style.color = COLORS.error;
        label.style.color = '#fca5a5';
    }
}

// ─── Technical Analysis Log ──────────────────────────────────────
function updateAnalysisLog(data) {
    const hs   = data.health_score;
    // Map backend priority_color to an overall risk rating
    const risk = data.priority_color === 'green' ? 'LOW (<5%)' : data.priority_color === 'orange' ? 'MODERATE' : 'HIGH (>40%)';
    const idx  = data.RUL_years < 10 ? 'ELEVATED' : 'NOMINAL';

    const logEl = document.getElementById('analysis_log_text');
    if (logEl) {
        logEl.innerHTML = `Structural assessment complete. Health index at <span style="color:#f0edf1;font-weight:600">${hs.toFixed(1)}%</span>.
Condition rated <span style="color:${data.priority_color};font-weight:600">${data.condition}</span> — ${data.safety_status}. Reason: ${data.status_reason}.
RUL estimated at <span style="color:#f0edf1;font-weight:600">${data.RUL_display}</span>.
Stress index classification: <strong style="color:#f0edf1">${idx}</strong>. Chloride ingress and environmental loads under continuous monitoring.`;
    }

    updateText('analysis_risk',   risk);
    updateText('analysis_stress', idx);
}

// ─── Command Queue ───────────────────────────────────────────────
function updateCommandQueue(data) {
    const textEl = document.getElementById('command_queue_text');
    const headEl = document.getElementById('command_queue_header');
    const btnEl  = document.getElementById('download_report_btn');
    if (!textEl) return;

    let col = COLORS.secondary;
    if (data.maintenance_action.color === 'orange') col = COLORS.warning;
    else if (data.maintenance_action.color === 'red') col = COLORS.error;

    textEl.innerHTML = data.maintenance_action.label + 
        `<br><br>Priority: <strong style="color:${col};text-transform:uppercase">${data.maintenance_action.priority}</strong>`;
    
    if (headEl) headEl.style.color = col;
    if (btnEl) {
        btnEl.style.borderColor = col;
        btnEl.style.color = col;
        // Also update hover state via style injection or simple class if needed
        // For now, let's just sync the base colors.
    }
}

// ─── Forecast Chart ──────────────────────────────────────────────
function updateForecastChart(data) {
    const ctx = document.getElementById('forecastChart');
    if (!ctx) return;
    if (forecastChart) forecastChart.destroy();

    forecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.years,
            datasets: [
                {
                    label: 'Mean Trend',
                    data: data.deterioration,
                    borderColor: COLORS.primary,
                    backgroundColor: 'transparent',
                    fill: false,
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 0,
                    hitRadius: 14,
                    pointHoverRadius: 4,
                    pointHoverBackgroundColor: COLORS.primary,
                },
                {
                    label: '95% Confidence',
                    data: data.confidence_upper,
                    borderColor: 'transparent',
                    backgroundColor: COLORS.primaryDim,
                    fill: '+1',
                    pointRadius: 0,
                    tension: 0.4,
                    hitRadius: 0,
                },
                {
                    label: 'Lower',
                    data: data.confidence_lower,
                    borderColor: 'transparent',
                    backgroundColor: 'transparent',
                    fill: false,
                    pointRadius: 0,
                    tension: 0.4,
                    hitRadius: 0,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: {
                        font: { size: 9, family: "'JetBrains Mono', monospace" },
                        color: COLORS.onSurface,
                        maxTicksLimit: 6,
                    }
                },
                y: {
                    min: 0,
                    max: 100,
                    reverse: true,
                    grid: { color: 'rgba(72,71,75,0.12)', drawBorder: false },
                    ticks: {
                        font: { size: 9, family: "'JetBrains Mono', monospace" },
                        color: COLORS.onSurface,
                        callback: (v) => v + '%'
                    }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#131316',
                    titleColor: '#f0edf1',
                    bodyColor: '#acaaae',
                    borderColor: 'rgba(72,71,75,0.4)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    usePointStyle: true,
                    boxPadding: 6,
                    titleFont: { family: "'Space Grotesk', sans-serif", weight: 'bold', size: 11 },
                    bodyFont:  { family: "'JetBrains Mono', monospace", size: 10 },
                }
            }
        }
    });
}

// ─── SHAP Chart ──────────────────────────────────────────────────
function updateShapChart(data) {
    const ctx = document.getElementById('shapChart');
    if (!ctx) return;
    if (shapChart) shapChart.destroy();

    const sorted = Object.entries(data.shap_values)
        .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
        .slice(0, 12);

    const getColor = (v) => v >= 0
        ? 'rgba(59, 130, 246, 0.75)'   // Blue — positive (helpful to health)
        : 'rgba(248, 113, 113, 0.55)'; // Red  — negative (harmful to health)

    shapChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sorted.map(f => f[0].replace(/_/g, ' ').toUpperCase()),
            datasets: [{
                data: sorted.map(f => f[1]),
                backgroundColor: sorted.map(f => getColor(f[1])),
                borderRadius: 2,
                barThickness: 11,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: { color: 'rgba(72,71,75,0.1)', drawBorder: false },
                    ticks: { font: { size: 9, family: "'JetBrains Mono', monospace" }, color: COLORS.onSurface }
                },
                y: {
                    grid: { display: false },
                    ticks: { font: { size: 9, family: "'JetBrains Mono', monospace" }, color: COLORS.onSurface }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#131316',
                    titleColor: '#f0edf1',
                    bodyColor: '#acaaae',
                    borderColor: 'rgba(72,71,75,0.4)',
                    borderWidth: 1,
                    padding: 10,
                    titleFont: { family: "'Space Grotesk', sans-serif", weight: 'bold', size: 10 },
                    bodyFont:  { family: "'JetBrains Mono', monospace", size: 10 },
                    callbacks: {
                        label: (ctx) => ` Impact: ${ctx.raw.toFixed(3)}`
                    }
                }
            }
        }
    });
}

// ─── What-If Handler ─────────────────────────────────────────────
const handleWhatIf = debounce(async (loadVal) => {
    const baseParams = getFormData();

    try {
        const res = await fetch('/whatif', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                base_params:   baseParams,
                changed_field: 'load_kn',
                changed_value: parseFloat(loadVal)
            })
        });

        if (!res.ok) {
            const errData = await res.json();
            const errMsg = errData.details ? errData.details[0].msg : (errData.error || "What-If failed");
            showValidationError(errMsg);
            return;
        }
        const data = await res.json();

        // Compute delta vs the last known full predict score
        const refScore = lastWhatIfScore ?? baseHealthScore ?? data.health_score;
        const delta    = data.health_score - refScore;
        
        currentWhatIfData = {
            base_load: baseParams.load_kn,
            new_load: parseFloat(loadVal),
            new_health_score: data.health_score,
            delta: delta,
            condition: data.condition
        };

        const isPos    = delta > 0;
        const sign     = isPos ? '+' : (delta === 0 ? '±' : '');
        const deltaColor = isPos ? COLORS.secondary : COLORS.error;
        updateText('whatif_delta_val',
            `${sign}${delta.toFixed(1)}<span class="text-sm font-medium pl-1" style="color:${deltaColor}">%</span>`
        );

        // Update projected health
        updateText('whatif_health_display', data.health_score.toFixed(1) + '%');
        updateText('whatif_condition', `Projected: ${data.condition}`);

        // Also update main health display and gauge
        updateText('health_score_val', data.health_score.toFixed(1));
        updateGauge(data.health_score);

        // Pulse dot
        const pulse = document.getElementById('status_pulse');
        if (pulse) {
            const c = data.priority_color; // SSOT from backend
            pulse.style.background = c;
            pulse.style.boxShadow  = `0 0 8px ${c}CC`;
        }

    } catch (err) {
        console.error('[SHPSv2] What-If failed:', err);
        showValidationError("Simulator disconnected. Real-time inference node responding with timeout.", false);
    }
}, 60);

// ─── Mobile Drawer ───────────────────────────────────────────────
function openMobileDrawer() {
    const drawer  = document.getElementById('mobile_drawer');
    const overlay = document.getElementById('mobile_drawer_overlay');
    if (drawer)  { drawer.classList.remove('hidden'); setTimeout(() => drawer.style.transform  = 'translateY(0)', 10); }
    if (overlay) { overlay.classList.remove('hidden'); }
}
function closeMobileDrawer() {
    const drawer  = document.getElementById('mobile_drawer');
    const overlay = document.getElementById('mobile_drawer_overlay');
    if (drawer)  { drawer.style.transform = 'translateY(100%)'; setTimeout(() => drawer.classList.add('hidden'), 310); }
    if (overlay) { overlay.classList.add('hidden'); }
}

// Sync mobile → desktop fields before analyze
function syncMobileToDesktop() {
    const pairs = [
        ['m_construction_year',   'construction_year'],
        ['m_last_inspection_year','last_inspection_year'],
        ['m_concrete_grade_mpa',  'concrete_grade_mpa'],
        ['m_elevation_m',         'elevation_m'],
        ['m_load_kn',             'load_kn'],
        ['m_cyclic_load_freq',    'cyclic_load_freq'],
        ['m_support_type',        'support_type'],
        ['m_env_condition',       'env_condition'],
        ['m_vibration_mms',       'vibration_mms'],
    ];
    pairs.forEach(([mId, dId]) => {
        const mEl = document.getElementById(mId);
        const dEl = document.getElementById(dId);
        if (mEl && dEl) dEl.value = mEl.value;
    });
}

// ─── Download Report ─────────────────────────────────────────────
async function downloadReport() {
    if (!currentInputs || !currentPredictData) {
        alert("Please run an analysis first to generate a report.");
        return;
    }
    
    const payload = {
        inputs: currentInputs,
        results: currentPredictData,
        forecast: currentForecastData,
        explanation: currentExplainData,
        whatif: currentWhatIfData
    };
    
    // UI Loading state
    const btn = document.getElementById('download_report_btn');
    const originalText = btn.innerText;
    if (btn) btn.innerText = "GENERATING...";
    
    try {
        // Create a hidden form to submit the data directly for a robust browser download
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/report';
        form.style.display = 'none';

        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'report_data';
        input.value = JSON.stringify(payload);

        form.appendChild(input);
        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    } catch (err) {
        console.error('[SHPSv2] Report generation failed:', err);
        alert("Report generation failed. See console.");
    } finally {
        if (btn) btn.innerText = originalText;
    }
}

// ─── DOM Ready ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {

    // Desktop buttons
    document.getElementById('simulate_btn')?.addEventListener('click', simulateData);
    document.getElementById('analyze_btn')?.addEventListener('click',  refreshUI);

    // Mobile controls (bottom of page)
    document.getElementById('simulate_btn_mobile')?.addEventListener('click', simulateData);
    document.getElementById('analyze_btn_mobile')?.addEventListener('click',  refreshUI);

    // FAB
    document.getElementById('mobile_fab')?.addEventListener('click', openMobileDrawer);

    // Mobile drawer buttons
    document.getElementById('mobile_simulate_btn')?.addEventListener('click', simulateData);
    document.getElementById('mobile_analyze_btn')?.addEventListener('click', () => {
        syncMobileToDesktop();
        refreshUI();
    });

    // What-If slider
    const slider  = document.getElementById('whatif_load_kn');
    const display = document.getElementById('whatif_load_display');

    if (slider && display) {
        slider.addEventListener('input', (e) => {
            const val = e.target.value;
            display.innerText = `${val} kN`;
            // Sync to the load_kn input field
            const loadEl = document.getElementById('load_kn');
            if (loadEl) loadEl.value = val;
            handleWhatIf(val);
        });
    }

    // Adjust Parameters button — sync slider to current load_kn
    document.getElementById('adjust_params_btn')?.addEventListener('click', () => {
        const loadEl  = document.getElementById('load_kn');
        const sliderEl = document.getElementById('whatif_load_kn');
        const displayEl = document.getElementById('whatif_load_display');
        if (loadEl && sliderEl) {
            sliderEl.value = loadEl.value;
            if (displayEl) displayEl.innerText = `${loadEl.value} kN`;
        }
        // Scroll to slider section
        document.getElementById('whatif_load_kn')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });

    // Download Report Button
    document.getElementById('download_report_btn')?.addEventListener('click', downloadReport);

    // Auto-load on startup
    simulateData();
});
