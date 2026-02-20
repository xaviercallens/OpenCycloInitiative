/* ═══════════════════════════════════════════════════════ */
/*  C.Y.C.L.O.S. HUD — Live Telemetry Bridge              */
/*  Connects HUD widgets to the OpenCyclo Telemetry API    */
/* ═══════════════════════════════════════════════════════ */

/**
 * TelemetryBridge
 * ────────────────
 * Establishes a WebSocket connection to the OpenCyclo Telemetry API
 * (telemetry_api.py) and maps incoming sensor data to HUD widget state.
 *
 * Connection: ws://<host>:8420/ws/telemetry
 *
 * The bridge operates in two modes:
 *   1. LIVE  — Connected to telemetry_api.py (real or simulated sensors)
 *   2. LOCAL — Fallback to internal simulation (no API available)
 *
 * Usage:
 *   const bridge = new TelemetryBridge('ws://localhost:8420/ws/telemetry');
 *   bridge.onData = (snapshot) => updateHUD(snapshot);
 *   bridge.connect();
 */

class TelemetryBridge {
    constructor(wsUrl = null) {
        // Auto-detect WebSocket URL from current location or use provided
        this.wsUrl = wsUrl || this._autoDetectUrl();
        this.ws = null;
        this.connected = false;
        this.reconnectInterval = 3000; // ms
        this.reconnectTimer = null;
        this.maxReconnectAttempts = 100;
        this.reconnectCount = 0;

        // Telemetry state — maps directly to HUD widget state
        this.state = {
            // From telemetry_api.py snapshot
            profile: 'GARAGE',
            operatingState: 'IDLE',
            uptime_s: 0,

            // Sensor metrics
            ph: 6.80,
            density_g_l: 0.50,
            green_ratio: 1.20,
            led_freq_hz: 82.5,
            led_duty_pct: 50.0,
            pump_speed_pct: 65.0,
            pump_freq_hz: 32.5,
            temperature_c: 24.0,
            co2_valve_open: false,

            // Derived metrics (computed by bridge)
            vortexRPM: 3400,
            shearRate: 1240,
            kLa: 135,
            x1: 0.12,
            x2: 0.87,
            x3: 0.01,
            fleEfficiency: 98.7,
            co2Total: 42.853,
            co2Today: 4.28,
            threatDetected: false,

            // Node identity
            node: {
                id: 'CONTES_ALPHA_01',
                lat: 43.8113,
                lon: 7.3167,
                location: 'Contes, France',
            },

            // Connection status
            mode: 'LOCAL', // 'LIVE' or 'LOCAL'
            lastUpdate: null,
        };

        // Callback for data consumers (HUD widgets)
        this.onData = null;
        this.onConnectionChange = null;

        // History buffers for charts
        this.history = {
            ph: [],
            density: [],
            shear: [],
            temperature: [],
        };
        this.maxHistory = 200;
    }

    /**
     * Auto-detect WebSocket URL based on page location
     */
    _autoDetectUrl() {
        // If running from file:// protocol, assume localhost
        if (typeof window !== 'undefined' && window.location.protocol === 'file:') {
            return 'ws://localhost:8420/ws/telemetry';
        }
        // If running from a web server, use same host
        const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${proto}//${window.location.hostname}:8420/ws/telemetry`;
    }

    /**
     * Connect to the telemetry WebSocket
     */
    connect() {
        if (this.ws && this.ws.readyState <= WebSocket.OPEN) {
            return; // Already connected or connecting
        }

        console.log(`[BRIDGE] Connecting to ${this.wsUrl}...`);
        this._updateUplink('CONNECTING');

        try {
            this.ws = new WebSocket(this.wsUrl);

            this.ws.onopen = () => {
                console.log('[BRIDGE] WebSocket connected — LIVE mode active');
                this.connected = true;
                this.reconnectCount = 0;
                this.state.mode = 'LIVE';
                this._updateUplink('LIVE');
                if (this.onConnectionChange) this.onConnectionChange('LIVE');

                // Send keep-alive ping every 10s
                this._startKeepAlive();
            };

            this.ws.onmessage = (event) => {
                try {
                    const snapshot = JSON.parse(event.data);
                    this._processSnapshot(snapshot);
                } catch (e) {
                    console.warn('[BRIDGE] Failed to parse telemetry:', e);
                }
            };

            this.ws.onclose = (event) => {
                console.log(`[BRIDGE] WebSocket closed (code: ${event.code})`);
                this.connected = false;
                this.state.mode = 'LOCAL';
                this._updateUplink('LOCAL');
                if (this.onConnectionChange) this.onConnectionChange('LOCAL');
                this._stopKeepAlive();
                this._scheduleReconnect();
            };

            this.ws.onerror = (error) => {
                console.warn('[BRIDGE] WebSocket error — falling back to LOCAL mode');
                this.state.mode = 'LOCAL';
                this._updateUplink('LOCAL');
            };

        } catch (e) {
            console.warn('[BRIDGE] WebSocket construction failed:', e);
            this.state.mode = 'LOCAL';
            this._updateUplink('LOCAL');
            this._scheduleReconnect();
        }
    }

    /**
     * Process incoming telemetry snapshot from the API
     */
    _processSnapshot(snapshot) {
        const metrics = snapshot.metrics || {};

        // Map API metrics to HUD state
        if (metrics.ph !== undefined) this.state.ph = metrics.ph;
        if (metrics.density_g_l !== undefined) this.state.density_g_l = metrics.density_g_l;
        if (metrics.green_ratio !== undefined) this.state.green_ratio = metrics.green_ratio;
        if (metrics.led_freq_hz !== undefined) this.state.led_freq_hz = metrics.led_freq_hz;
        if (metrics.led_duty_pct !== undefined) this.state.led_duty_pct = metrics.led_duty_pct;
        if (metrics.pump_speed_pct !== undefined) this.state.pump_speed_pct = metrics.pump_speed_pct;
        if (metrics.pump_freq_hz !== undefined) this.state.pump_freq_hz = metrics.pump_freq_hz;
        if (metrics.temperature_c !== undefined) this.state.temperature_c = metrics.temperature_c;
        if (metrics.co2_valve_open !== undefined) this.state.co2_valve_open = !!metrics.co2_valve_open;

        // Map top-level fields
        if (snapshot.profile) this.state.profile = snapshot.profile;
        if (snapshot.state) this.state.operatingState = snapshot.state;
        if (snapshot.uptime_s) this.state.uptime_s = snapshot.uptime_s;
        if (snapshot.node) this.state.node = snapshot.node;

        // Compute derived metrics
        this._computeDerived();

        // Update history buffers
        this._pushHistory('ph', this.state.ph);
        this._pushHistory('density', this.state.density_g_l);
        this._pushHistory('shear', this.state.shearRate);
        this._pushHistory('temperature', this.state.temperature_c);

        this.state.lastUpdate = Date.now();

        // Notify consumers
        if (this.onData) this.onData(this.state);
    }

    /**
     * Compute derived HUD metrics from raw sensor data
     */
    _computeDerived() {
        const s = this.state;

        // Vortex RPM: pump speed % → approximate RPM
        // Industrial pump: 50Hz → ~3600 RPM at 100%
        s.vortexRPM = Math.round(s.pump_speed_pct * 52);

        // Shear rate: proportional to vortex angular velocity
        // G ≈ ω * R / δ, simplified
        s.shearRate = Math.round(s.vortexRPM * 0.38 + 200 + Math.random() * 50);

        // kLa: mass transfer coefficient (correlates with pump speed + gas flow)
        s.kLa = Math.round(80 + s.pump_speed_pct * 0.85 + Math.random() * 5);

        // FLE efficiency: ratio of LED frequency to expected vortex frequency
        const idealFreq = s.pump_freq_hz * 2.54; // Empirical ratio
        const freqDelta = Math.abs(s.led_freq_hz - idealFreq) / idealFreq;
        s.fleEfficiency = Math.max(0, Math.min(100, 100 - freqDelta * 200));

        // Han model states (simplified steady-state)
        // When FLE is high: mostly in x2 (processing)
        const fle = s.fleEfficiency / 100;
        s.x2 = Math.min(0.95, 0.50 + fle * 0.45);
        s.x1 = Math.max(0.02, (1 - s.x2) * 0.9);
        s.x3 = Math.max(0.005, 1 - s.x1 - s.x2);

        // CO₂ total: estimated from density × volume × stoichiometric ratio
        const volumeL = s.profile === 'GARAGE' ? 19.0 : 1000.0;
        const biomassKg = s.density_g_l * volumeL / 1000;
        s.co2Total = biomassKg * 1.83;
        s.co2Today = s.co2Total * 0.1; // Rough daily fraction
    }

    /**
     * Push a value to a history buffer
     */
    _pushHistory(key, value) {
        if (!this.history[key]) this.history[key] = [];
        this.history[key].push(value);
        if (this.history[key].length > this.maxHistory) {
            this.history[key].shift();
        }
    }

    /**
     * Get history buffer for a metric (used by chart widgets)
     */
    getHistory(key) {
        return this.history[key] || [];
    }

    /**
     * Update the uplink indicator in the HUD
     */
    _updateUplink(status) {
        const el = document.getElementById('topbar-uplink');
        if (!el) return;

        const dot = el.querySelector('.uplink-dot');
        const text = el.querySelector('span:last-child');
        if (!text) return;

        switch (status) {
            case 'LIVE':
                text.textContent = 'LIVE UPLINK';
                if (dot) {
                    dot.style.background = '#00FF66';
                    dot.style.boxShadow = '0 0 12px rgba(0,255,102,0.5)';
                }
                break;
            case 'CONNECTING':
                text.textContent = 'CONNECTING...';
                if (dot) {
                    dot.style.background = '#FFC400';
                    dot.style.boxShadow = '0 0 12px rgba(255,196,0,0.5)';
                }
                break;
            case 'LOCAL':
                text.textContent = 'LOCAL SIM';
                if (dot) {
                    dot.style.background = '#00E5FF';
                    dot.style.boxShadow = '0 0 12px rgba(0,229,255,0.5)';
                }
                break;
        }
    }

    /**
     * Reconnect with exponential backoff
     */
    _scheduleReconnect() {
        if (this.reconnectCount >= this.maxReconnectAttempts) {
            console.log('[BRIDGE] Max reconnect attempts reached. Staying in LOCAL mode.');
            return;
        }

        const delay = Math.min(
            this.reconnectInterval * Math.pow(1.5, this.reconnectCount),
            30000 // max 30s
        );

        this.reconnectCount++;
        console.log(`[BRIDGE] Reconnecting in ${(delay / 1000).toFixed(1)}s (attempt ${this.reconnectCount})`);

        this.reconnectTimer = setTimeout(() => this.connect(), delay);
    }

    /**
     * Keep-alive pings
     */
    _startKeepAlive() {
        this._keepAliveId = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send('ping');
            }
        }, 10000);
    }

    _stopKeepAlive() {
        if (this._keepAliveId) {
            clearInterval(this._keepAliveId);
            this._keepAliveId = null;
        }
    }

    /**
     * Disconnect and clean up
     */
    disconnect() {
        this._stopKeepAlive();
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
        if (this.ws) {
            this.ws.onclose = null; // Prevent reconnect
            this.ws.close();
        }
        this.connected = false;
        this.state.mode = 'LOCAL';
    }

    /**
     * Fetch a one-shot REST status (for initial load)
     */
    async fetchStatus() {
        const httpUrl = this.wsUrl
            .replace('ws://', 'http://')
            .replace('wss://', 'https://')
            .replace('/ws/telemetry', '/api/v1/status');

        try {
            const resp = await fetch(httpUrl);
            if (resp.ok) {
                const snapshot = await resp.json();
                this._processSnapshot(snapshot);
                return true;
            }
        } catch (e) {
            console.warn('[BRIDGE] REST fetch failed:', e.message);
        }
        return false;
    }

    /**
     * Fetch CO₂ accumulation stats
     */
    async fetchCO2Stats() {
        const httpUrl = this.wsUrl
            .replace('ws://', 'http://')
            .replace('wss://', 'https://')
            .replace('/ws/telemetry', '/api/v1/co2');

        try {
            const resp = await fetch(httpUrl);
            if (resp.ok) {
                const data = await resp.json();
                this.state.co2Total = data.co2_kg_total || 0;
                this.state.co2Today = data.co2_kg_today || 0;
                return data;
            }
        } catch (e) {
            // Silent fallback
        }
        return null;
    }
}


// ═══════════════════════════════════════════════════════
//  HUD INTEGRATION HOOKS
//  These functions map TelemetryBridge state → DOM elements
// ═══════════════════════════════════════════════════════

/**
 * Apply live telemetry state to HUD DOM elements.
 * Called every time new data arrives from the bridge.
 */
function applyTelemetryToHUD(state) {
    // Stat displays
    _setText('stat-rpm', Math.round(state.vortexRPM).toLocaleString());
    _setText('stat-density', state.density_g_l.toFixed(2));
    _setText('stat-ph', state.ph.toFixed(2));
    _setText('stat-temp', state.temperature_c.toFixed(1));

    // Phase lock efficiency
    _setText('fle-value', state.fleEfficiency.toFixed(1) + '%');

    // Shear
    _setText('shear-value', Math.round(state.shearRate).toLocaleString());

    // kLa
    _setText('kla-value', Math.round(state.kLa));

    // Growth
    _setText('growth-density', state.density_g_l.toFixed(2));

    // Han states
    _setText('han-x1', Math.round(state.x1 * 100) + '%', '.han-value');
    _setText('han-x2', Math.round(state.x2 * 100) + '%', '.han-value');
    _setText('han-x3', Math.round(state.x3 * 100) + '%', '.han-value');

    // CO₂ ticker
    const co2Formatted = state.co2Total.toFixed(3).replace(/^(\d)/, '0,$1');
    _setText('co2-ticker', co2Formatted);

    // Vision threat
    const visionStatus = document.getElementById('vision-status');
    if (visionStatus) {
        visionStatus.innerHTML = state.threatDetected
            ? '<span class="val-crimson">■ THREAT DETECTED: BRACHIONUS // INITIATING pH SHOCK</span>'
            : '<span class="val-emerald">■</span> ALL CLEAR — NO THREATS DETECTED';
    }

    // Operating state badge
    const nodeEl = document.querySelector('.topbar-node');
    if (nodeEl) {
        nodeEl.textContent = `NODE: ${state.node.id} | ${state.operatingState}`;
    }
}

function _setText(id, value, childSelector) {
    const el = document.getElementById(id);
    if (!el) return;
    if (childSelector) {
        const child = el.querySelector(childSelector);
        if (child) child.textContent = value;
    } else {
        el.textContent = value;
    }
}


// ═══════════════════════════════════════════════════════
//  EXPORT / INIT
// ═══════════════════════════════════════════════════════

// Make available globally for hud.js to use
window.TelemetryBridge = TelemetryBridge;
window.applyTelemetryToHUD = applyTelemetryToHUD;
