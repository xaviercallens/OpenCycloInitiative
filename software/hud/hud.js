/* ═══════════════════════════════════════════════════════ */
/*  C.Y.C.L.O.S. HUD — JavaScript Engine                  */
/*  Cognitive Yield & Carbon Logistics Operating System     */
/* ═══════════════════════════════════════════════════════ */

(() => {
    'use strict';

    // ─── DESIGN TOKENS ───
    const C = {
        CYAN: '#00E5FF',
        CYAN_DIM: 'rgba(0,229,255,0.15)',
        CYAN_GLOW: 'rgba(0,229,255,0.4)',
        EMERALD: '#00FF66',
        EMERALD_DIM: 'rgba(0,255,102,0.15)',
        EMERALD_GLOW: 'rgba(0,255,102,0.4)',
        AMBER: '#FFC400',
        CRIMSON: '#FF0033',
        VOID: '#03050A',
        TEXT_DIM: 'rgba(255,255,255,0.35)',
    };


    // ═══════════════════════════════════════════════════════
    //  SIMULATED TELEMETRY STATE
    // ═══════════════════════════════════════════════════════

    const state = {
        time: 0,
        vortexRPM: 3400,
        pumpPct: 50,
        density: 0.5,
        ph: 6.8,
        temp: 24.1,
        co2Valve: false,
        ledDuty: 82,
        ledFreq: 82,
        shearRate: 1240,
        kLa: 135,
        co2Total: 42.853,
        x1: 0.12, x2: 0.87, x3: 0.01,
        fleEfficiency: 98.7,
        growthHistory: [],
        shearHistory: [],
        threatDetected: false,
    };

    // Pre-fill histories
    for (let i = 0; i < 200; i++) {
        state.shearHistory.push(1100 + Math.random() * 300);
    }
    for (let i = 0; i < 100; i++) {
        state.growthHistory.push(0.1 * Math.exp(0.03 * i));
    }


    // ═══════════════════════════════════════════════════════
    //  BOOT SEQUENCE
    // ═══════════════════════════════════════════════════════

    const bootMessages = [
        '> INIT C.Y.C.L.O.S. v2.0...',
        '> LOADING DIGITAL TWIN KERNEL...',
        '> ESTABLISHING ROS2 LINK.........',
        '> PINN SURROGATE ENGINE: ONLINE',
        '> OPENCV PIPELINE: 60 FPS LOCK',
        '> MQTT TELEMETRY BRIDGE: SYNCED',
        '> UPLINK SECURED.',
        '',
        '> ALL SYSTEMS NOMINAL.',
    ];

    function runBootSequence() {
        const overlay = document.getElementById('boot-overlay');
        const scanline = document.getElementById('boot-scanline');
        const hexGrid = document.getElementById('boot-hex');
        const terminal = document.getElementById('boot-terminal');
        const status = document.getElementById('boot-status');
        const hud = document.getElementById('hud-container');

        // T+0.0s: Pitch black (already)
        // T+0.3s: Scanline sweep
        setTimeout(() => {
            scanline.classList.add('active');
        }, 300);

        // T+0.8s: Hex grid appears
        setTimeout(() => {
            hexGrid.classList.add('visible');
        }, 800);

        // T+1.0s: Terminal cascade
        setTimeout(() => {
            terminal.classList.add('visible');
            let idx = 0;
            const typeInterval = setInterval(() => {
                if (idx < bootMessages.length) {
                    terminal.textContent += bootMessages[idx] + '\n';
                    idx++;
                } else {
                    clearInterval(typeInterval);
                }
            }, 180);
        }, 1000);

        // T+2.5s: Status update
        setTimeout(() => {
            status.textContent = 'SYSTEMS ONLINE';
            status.style.color = C.EMERALD;
        }, 2500);

        // T+3.2s: Fade out boot, show HUD
        setTimeout(() => {
            overlay.classList.add('done');
            hud.classList.remove('hidden');
            hud.style.opacity = '1';

            // Slide in widgets
            setTimeout(() => activateWidgets(), 200);
            setTimeout(() => startAllEngines(), 600);
        }, 3200);
    }

    function activateWidgets() {
        document.querySelectorAll('.widget').forEach((w, i) => {
            setTimeout(() => w.classList.add('in'), i * 120);
        });
    }


    // ═══════════════════════════════════════════════════════
    //  CLOCK
    // ═══════════════════════════════════════════════════════

    function updateClock() {
        const now = new Date();
        const h = String(now.getHours()).padStart(2, '0');
        const m = String(now.getMinutes()).padStart(2, '0');
        const s = String(now.getSeconds()).padStart(2, '0');
        document.getElementById('clock').textContent = `${h}:${m}:${s}`;
    }


    // ═══════════════════════════════════════════════════════
    //  HEX GRID BACKGROUND
    // ═══════════════════════════════════════════════════════

    function drawHexGrid() {
        const canvas = document.getElementById('hex-grid-bg');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        const size = 30;
        const w = size * 2;
        const h = Math.sqrt(3) * size;

        ctx.strokeStyle = 'rgba(0, 229, 255, 0.04)';
        ctx.lineWidth = 0.5;

        for (let row = -1; row < canvas.height / h + 1; row++) {
            for (let col = -1; col < canvas.width / w + 1; col++) {
                const x = col * w * 0.75;
                const y = row * h + (col % 2 ? h / 2 : 0);
                drawHex(ctx, x, y, size);
            }
        }
    }

    function drawHex(ctx, cx, cy, r) {
        ctx.beginPath();
        for (let i = 0; i < 6; i++) {
            const angle = Math.PI / 3 * i - Math.PI / 6;
            const x = cx + r * Math.cos(angle);
            const y = cy + r * Math.sin(angle);
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.stroke();
    }


    // ═══════════════════════════════════════════════════════
    //  WIDGET A: PHASE-LOCK RING (Arc Reactor Style)
    // ═══════════════════════════════════════════════════════

    let phaseLockAngle = 0;

    function drawPhaseLock() {
        const canvas = document.getElementById('phase-lock-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        phaseLockAngle += 0.02;

        // Outer ring (Vortex RPM — Cyan)
        drawArcRing(ctx, cx, cy, 115, 8, C.CYAN, C.CYAN_GLOW, phaseLockAngle, 12, 0.7);

        // Inner ring (LED PWM — Emerald, counter-rotating)
        drawArcRing(ctx, cx, cy, 90, 6, C.EMERALD, C.EMERALD_GLOW, -phaseLockAngle * 1.2, 8, 0.6);

        // Center ring
        ctx.beginPath();
        ctx.arc(cx, cy, 55, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(0,229,255,0.15)';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Tick marks
        for (let i = 0; i < 60; i++) {
            const a = (Math.PI * 2 / 60) * i + phaseLockAngle;
            const inner = i % 5 === 0 ? 118 : 120;
            const outer = 125;
            ctx.beginPath();
            ctx.moveTo(cx + Math.cos(a) * inner, cy + Math.sin(a) * inner);
            ctx.lineTo(cx + Math.cos(a) * outer, cy + Math.sin(a) * outer);
            ctx.strokeStyle = i % 5 === 0 ? C.CYAN : 'rgba(0,229,255,0.2)';
            ctx.lineWidth = i % 5 === 0 ? 2 : 1;
            ctx.stroke();
        }

        // Update efficiency display
        const eff = state.fleEfficiency + Math.sin(state.time * 0.5) * 0.3;
        document.getElementById('fle-value').textContent = eff.toFixed(1) + '%';
    }

    function drawArcRing(ctx, cx, cy, r, w, color, glow, angle, segments, gapRatio) {
        const segAngle = (Math.PI * 2) / segments;
        const gap = segAngle * (1 - gapRatio);

        for (let i = 0; i < segments; i++) {
            const start = angle + segAngle * i + gap / 2;
            const end = start + segAngle - gap;

            ctx.beginPath();
            ctx.arc(cx, cy, r, start, end);
            ctx.strokeStyle = color;
            ctx.lineWidth = w;
            ctx.shadowColor = glow;
            ctx.shadowBlur = 12;
            ctx.stroke();
            ctx.shadowBlur = 0;
        }
    }


    // ═══════════════════════════════════════════════════════
    //  WIDGET B: SHEAR STRESS ECG
    // ═══════════════════════════════════════════════════════

    function drawShearMonitor() {
        const canvas = document.getElementById('shear-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;

        ctx.clearRect(0, 0, w, h);

        // Background grid
        ctx.strokeStyle = 'rgba(0,229,255,0.06)';
        ctx.lineWidth = 0.5;
        for (let y = 20; y < h; y += 20) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(w, y);
            ctx.stroke();
        }

        // Danger threshold line
        const dangerY = 15;
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = C.CRIMSON;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, dangerY);
        ctx.lineTo(w, dangerY);
        ctx.stroke();
        ctx.setLineDash([]);

        // Label
        ctx.font = '9px "Fira Code"';
        ctx.fillStyle = C.CRIMSON;
        ctx.fillText('G_CRIT = 5,000 s⁻¹', w - 120, dangerY - 4);

        // ECG line
        const data = state.shearHistory;
        const maxVal = 5000;
        ctx.beginPath();
        for (let i = 0; i < data.length; i++) {
            const x = (i / data.length) * w;
            const y = h - (data[i] / maxVal) * (h - 20);
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.strokeStyle = C.CYAN;
        ctx.lineWidth = 1.5;
        ctx.shadowColor = C.CYAN_GLOW;
        ctx.shadowBlur = 8;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Update value
        const current = data[data.length - 1];
        document.getElementById('shear-value').textContent = Math.round(current).toLocaleString();
    }


    // ═══════════════════════════════════════════════════════
    //  WIDGET C: NANOBUBBLE PENETRATION
    // ═══════════════════════════════════════════════════════

    const bubbles = [];
    for (let i = 0; i < 80; i++) {
        bubbles.push({
            x: Math.random(),
            y: Math.random(),
            r: 1 + Math.random() * 2,
            v: 0.002 + Math.random() * 0.004,
            opacity: 0.3 + Math.random() * 0.7,
        });
    }

    function drawNanobubble() {
        const canvas = document.getElementById('nanobubble-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;

        ctx.clearRect(0, 0, w, h);

        // Bar graph background
        const barCount = 20;
        const barW = (w - 40) / barCount;
        for (let i = 0; i < barCount; i++) {
            const val = Math.sin(state.time * 0.3 + i * 0.4) * 0.3 + 0.6;
            const barH = val * (h - 20);
            const x = 20 + i * barW;
            const y = h - barH;

            ctx.fillStyle = `rgba(0, 229, 255, ${0.1 + val * 0.15})`;
            ctx.fillRect(x + 1, y, barW - 2, barH);

            ctx.strokeStyle = C.CYAN_DIM;
            ctx.lineWidth = 0.5;
            ctx.strokeRect(x + 1, y, barW - 2, barH);
        }

        // Rising micro-dots (nanobubbles)
        bubbles.forEach(b => {
            b.y -= b.v;
            if (b.y < 0) {
                b.y = 1;
                b.x = Math.random();
            }

            ctx.beginPath();
            ctx.arc(20 + b.x * (w - 40), b.y * h, b.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(0, 229, 255, ${b.opacity * 0.6})`;
            ctx.shadowColor = C.CYAN_GLOW;
            ctx.shadowBlur = 6;
            ctx.fill();
            ctx.shadowBlur = 0;
        });

        // kLa readout
        const kla = state.kLa + Math.sin(state.time * 0.7) * 5;
        document.getElementById('kla-value').textContent = Math.round(kla);
    }


    // ═══════════════════════════════════════════════════════
    //  WIDGET D: YOLO VISION FEED
    // ═══════════════════════════════════════════════════════

    function drawVisionFeed() {
        const canvas = document.getElementById('vision-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;

        ctx.clearRect(0, 0, w, h);

        // Dark background with noise
        ctx.fillStyle = '#0a0f14';
        ctx.fillRect(0, 0, w, h);

        // Simulated monochrome fluid texture
        for (let i = 0; i < 120; i++) {
            const x = Math.random() * w;
            const y = Math.random() * h;
            const r = 2 + Math.random() * 6;
            const brightness = 15 + Math.random() * 30;
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${brightness}, ${brightness + 10}, ${brightness}, 0.5)`;
            ctx.fill();
        }

        // Healthy cells — cyan bounding boxes
        const cells = [
            { x: 50, y: 40, w: 35, h: 30 },
            { x: 120, y: 70, w: 28, h: 25 },
            { x: 200, y: 50, w: 32, h: 28 },
            { x: 160, y: 130, w: 30, h: 26 },
            { x: 80, y: 140, w: 34, h: 30 },
            { x: 260, y: 100, w: 28, h: 25 },
        ];

        cells.forEach(cell => {
            // Jitter animation
            const jx = cell.x + Math.sin(state.time * 2 + cell.x) * 2;
            const jy = cell.y + Math.cos(state.time * 1.5 + cell.y) * 2;

            ctx.strokeStyle = C.CYAN;
            ctx.lineWidth = 1;
            ctx.shadowColor = C.CYAN_GLOW;
            ctx.shadowBlur = 4;
            ctx.strokeRect(jx, jy, cell.w, cell.h);
            ctx.shadowBlur = 0;

            // Label
            ctx.font = '7px "Fira Code"';
            ctx.fillStyle = C.CYAN;
            ctx.fillText('CHLOR_OK|99%', jx, jy - 3);
        });

        // Threat detection (occasional)
        if (state.threatDetected) {
            const tx = 240 + Math.sin(state.time) * 10;
            const ty = 40 + Math.cos(state.time * 0.7) * 10;

            // Crimson bounding box
            ctx.strokeStyle = C.CRIMSON;
            ctx.lineWidth = 2;
            ctx.shadowColor = C.CRIMSON;
            ctx.shadowBlur = 10;
            ctx.strokeRect(tx, ty, 50, 45);

            // Crosshair
            ctx.beginPath();
            ctx.moveTo(tx + 25, ty - 10);
            ctx.lineTo(tx + 25, ty + 55);
            ctx.moveTo(tx - 10, ty + 22);
            ctx.lineTo(tx + 60, ty + 22);
            ctx.stroke();
            ctx.shadowBlur = 0;

            // Label
            ctx.font = '8px "Fira Code"';
            ctx.fillStyle = C.CRIMSON;
            ctx.fillText('THREAT: BRACHIONUS', tx - 20, ty - 14);

            document.getElementById('vision-status').innerHTML =
                '<span class="val-crimson">■ THREAT DETECTED: BRACHIONUS // INITIATING pH SHOCK</span>';
        } else {
            document.getElementById('vision-status').innerHTML =
                '<span class="val-emerald">■</span> ALL CLEAR — NO THREATS DETECTED';
        }

        // Scanline effect
        const scanY = (state.time * 60) % h;
        ctx.fillStyle = 'rgba(0, 229, 255, 0.03)';
        ctx.fillRect(0, scanY, w, 3);
    }


    // ═══════════════════════════════════════════════════════
    //  WIDGET E: HAN STATE MATRIX (Updates)
    // ═══════════════════════════════════════════════════════

    function updateHanMatrix() {
        // Subtle fluctuation
        const dx = Math.sin(state.time * 0.3) * 2;
        const x1 = Math.max(1, Math.round(state.x1 * 100 + dx));
        const x2 = Math.max(1, Math.round(state.x2 * 100 - dx * 0.8));
        const x3 = Math.max(0, 100 - x1 - x2);

        const e = (v, label) => {
            const el = document.getElementById(label);
            if (el) el.querySelector('.han-value').textContent = v + '%';
        };

        e(x1, 'han-x1');
        e(x2, 'han-x2');
        e(x3, 'han-x3');
    }


    // ═══════════════════════════════════════════════════════
    //  WIDGET F: GROWTH CURVE
    // ═══════════════════════════════════════════════════════

    function drawGrowthCurve() {
        const canvas = document.getElementById('growth-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;

        ctx.clearRect(0, 0, w, h);

        const data = state.growthHistory;
        const maxD = Math.max(...data, 1);

        // Filled area under curve
        ctx.beginPath();
        ctx.moveTo(0, h);
        for (let i = 0; i < data.length; i++) {
            const x = (i / data.length) * w;
            const y = h - (data[i] / maxD) * (h - 10);
            ctx.lineTo(x, y);
        }
        ctx.lineTo(w, h);
        ctx.closePath();

        const grad = ctx.createLinearGradient(0, 0, 0, h);
        grad.addColorStop(0, 'rgba(0, 255, 102, 0.25)');
        grad.addColorStop(1, 'rgba(0, 255, 102, 0.02)');
        ctx.fillStyle = grad;
        ctx.fill();

        // Line
        ctx.beginPath();
        for (let i = 0; i < data.length; i++) {
            const x = (i / data.length) * w;
            const y = h - (data[i] / maxD) * (h - 10);
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.strokeStyle = C.EMERALD;
        ctx.lineWidth = 2;
        ctx.shadowColor = C.EMERALD_GLOW;
        ctx.shadowBlur = 10;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Current value
        document.getElementById('growth-density').textContent = state.density.toFixed(2);
    }


    // ═══════════════════════════════════════════════════════
    //  CENTER: REACTOR HOLOGRAM (2D Canvas)
    // ═══════════════════════════════════════════════════════

    const particles = [];
    const PARTICLE_COUNT = 2000;

    function initParticles(cx, cy) {
        particles.length = 0;
        for (let i = 0; i < PARTICLE_COUNT; i++) {
            const angle = Math.random() * Math.PI * 2;
            const r = 40 + Math.random() * 120;
            const z = (Math.random() - 0.5) * 300;
            particles.push({
                angle,
                r,
                z,
                speed: 0.008 + Math.random() * 0.012,
                size: 1 + Math.random() * 1.5,
            });
        }
    }

    function drawReactor() {
        const canvas = document.getElementById('reactor-canvas');
        if (!canvas) return;

        if (canvas.width !== canvas.parentElement.clientWidth) {
            canvas.width = canvas.parentElement.clientWidth;
            canvas.height = canvas.parentElement.clientHeight;
            initParticles(canvas.width / 2, canvas.height / 2);
        }

        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;
        const cx = w / 2;
        const cy = h / 2;

        ctx.clearRect(0, 0, w, h);

        // Cylinder wireframe
        const cylW = 180;
        const cylH = 340;
        const cylTop = cy - cylH / 2;
        const cylBot = cy + cylH / 2;

        ctx.strokeStyle = 'rgba(0, 229, 255, 0.12)';
        ctx.lineWidth = 1;

        // Vertical lines
        for (let i = 0; i < 24; i++) {
            const angle = (Math.PI * 2 / 24) * i;
            const xOff = Math.cos(angle) * cylW / 2;
            const depth = Math.sin(angle);
            ctx.globalAlpha = 0.15 + Math.max(0, depth) * 0.15;
            ctx.beginPath();
            ctx.moveTo(cx + xOff, cylTop);
            ctx.lineTo(cx + xOff, cylBot);
            ctx.stroke();
        }
        ctx.globalAlpha = 1;

        // Ellipse rings
        const rings = 8;
        for (let i = 0; i <= rings; i++) {
            const y = cylTop + (cylH / rings) * i;
            ctx.beginPath();
            ctx.ellipse(cx, y, cylW / 2, 18, 0, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(0, 229, 255, 0.08)';
            ctx.lineWidth = 0.5;
            ctx.stroke();
        }

        // Light guides (4 vertical bars pulsing violet/blue)
        const guidePositions = [-60, -20, 20, 60];
        const pulse = (Math.sin(state.time * 82 * 0.05) * 0.5 + 0.5); // 82 Hz simulated
        guidePositions.forEach(gx => {
            const gradient = ctx.createLinearGradient(cx + gx, cylTop + 20, cx + gx, cylBot - 20);
            gradient.addColorStop(0, `rgba(120, 80, 255, ${0.1 + pulse * 0.3})`);
            gradient.addColorStop(0.5, `rgba(180, 120, 255, ${0.2 + pulse * 0.4})`);
            gradient.addColorStop(1, `rgba(120, 80, 255, ${0.1 + pulse * 0.3})`);

            ctx.fillStyle = gradient;
            ctx.fillRect(cx + gx - 3, cylTop + 20, 6, cylH - 40);

            // Glow
            ctx.shadowColor = `rgba(160, 100, 255, ${0.3 + pulse * 0.3})`;
            ctx.shadowBlur = 15;
            ctx.fillRect(cx + gx - 1, cylTop + 20, 2, cylH - 40);
            ctx.shadowBlur = 0;
        });

        // Swirling particles (Rankine vortex)
        particles.forEach(p => {
            p.angle += p.speed;

            // 3D projection
            const x3d = Math.cos(p.angle) * p.r;
            const y3d = p.z;
            const z3d = Math.sin(p.angle) * p.r;

            const scale = 300 / (300 + z3d);
            const sx = cx + x3d * scale;
            const sy = cy + y3d * scale * 0.6;

            // Depth-based opacity
            const depthAlpha = 0.2 + scale * 0.5;

            // Check if near light guide → flash white
            const nearGuide = guidePositions.some(gx => Math.abs(x3d - gx) < 15);
            const flashAlpha = nearGuide ? 0.8 + pulse * 0.2 : 0;

            if (flashAlpha > 0.5) {
                ctx.fillStyle = `rgba(255, 255, 255, ${flashAlpha * depthAlpha})`;
            } else {
                ctx.fillStyle = `rgba(0, 255, 102, ${depthAlpha * 0.6})`;
            }

            ctx.beginPath();
            ctx.arc(sx, sy, p.size * scale, 0, Math.PI * 2);
            ctx.fill();
        });

        // Slowly move particles upward (vortex lift)
        particles.forEach(p => {
            p.z -= 0.3;
            if (p.z < -150) p.z = 150;
        });
    }


    // ═══════════════════════════════════════════════════════
    //  FOOTER: AI WAVEFORM
    // ═══════════════════════════════════════════════════════

    function drawWaveform() {
        const canvas = document.getElementById('waveform-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;
        const cy = h / 2;

        ctx.clearRect(0, 0, w, h);

        // Center line
        ctx.strokeStyle = 'rgba(0,229,255,0.1)';
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(0, cy);
        ctx.lineTo(w, cy);
        ctx.stroke();

        // Waveform
        ctx.beginPath();
        for (let x = 0; x < w; x++) {
            const t = x / w * Math.PI * 8;
            const amp = Math.sin(t + state.time * 3) *
                Math.sin(t * 0.3 + state.time) *
                15 + Math.sin(t * 7 + state.time * 5) * 3;
            const y = cy + amp;
            x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.strokeStyle = C.CYAN;
        ctx.lineWidth = 1.5;
        ctx.shadowColor = C.CYAN_GLOW;
        ctx.shadowBlur = 8;
        ctx.stroke();
        ctx.shadowBlur = 0;
    }


    // ═══════════════════════════════════════════════════════
    //  FOOTER: CO₂ TICKER
    // ═══════════════════════════════════════════════════════

    function updateTicker() {
        state.co2Total += 0.001 + Math.random() * 0.003;
        const formatted = state.co2Total.toFixed(3).replace(/^(\d)/, '0,$1');
        document.getElementById('co2-ticker').textContent = formatted;
    }


    // ═══════════════════════════════════════════════════════
    //  FOOTER: TERMINAL FEED
    // ═══════════════════════════════════════════════════════

    const terminalMessages = [
        { msg: '[AI.PID] pH at {ph}. CO₂ solenoid: PROPORTIONAL', type: 'normal' },
        { msg: '[AI.PINN] Tensor inference {inf}ms. Vortex stable.', type: 'normal' },
        { msg: '[AI.VIS] Frame processed. {cells} cells tracked. No anomaly.', type: 'normal' },
        { msg: '[SYS.PUMP] VFD frequency: {rpm} RPM. Shear: NOMINAL', type: 'normal' },
        { msg: '[AI.HAN] FLE sync: {fle}%. PQ state optimal.', type: 'normal' },
        { msg: '[SYS.LED] PWM locked at {freq} Hz. Energy draw: -{savings}%', type: 'normal' },
        { msg: '[MQTT] Telemetry published to /opencyclo/contes/status', type: 'normal' },
        { msg: '[AI.TWIN] Digital twin delta: {delta}%. Reality sync LOCKED', type: 'normal' },
    ];

    function addTerminalLine() {
        const feed = document.getElementById('terminal-feed');
        const template = terminalMessages[Math.floor(Math.random() * terminalMessages.length)];

        let msg = template.msg
            .replace('{ph}', state.ph.toFixed(1))
            .replace('{inf}', (12 + Math.random() * 6).toFixed(0))
            .replace('{cells}', (40 + Math.floor(Math.random() * 30)).toString())
            .replace('{rpm}', Math.round(state.vortexRPM).toLocaleString())
            .replace('{fle}', state.fleEfficiency.toFixed(1))
            .replace('{freq}', state.ledFreq.toString())
            .replace('{savings}', '47')
            .replace('{delta}', (0.5 + Math.random() * 2).toFixed(1));

        const line = document.createElement('div');
        line.className = 'terminal-line' + (template.type === 'alert' ? ' alert' : '');
        line.textContent = '> ' + msg;
        feed.appendChild(line);

        // Keep max 8 lines
        while (feed.children.length > 8) {
            feed.removeChild(feed.firstChild);
        }

        feed.scrollTop = feed.scrollHeight;
    }


    // ═══════════════════════════════════════════════════════
    //  SIMULATE TELEMETRY STATE CHANGES
    // ═══════════════════════════════════════════════════════

    function updateSimulation(dt) {
        state.time += dt;

        // Biomass growth (logistic)
        const maxDensity = 8.0;
        const growthRate = 0.0005;
        state.density += growthRate * state.density * (1 - state.density / maxDensity) * dt;
        state.density = Math.max(0.1, Math.min(maxDensity, state.density));

        // pH drift
        state.ph += (Math.sin(state.time * 0.1) * 0.02);
        state.ph = Math.max(6.5, Math.min(7.5, state.ph));

        // Temperature
        state.temp = 24.0 + Math.sin(state.time * 0.05) * 0.3;

        // RPM variation
        state.vortexRPM = 3400 + Math.sin(state.time * 0.2) * 50;

        // Shear history update
        state.shearHistory.push(1100 + Math.random() * 300 + Math.sin(state.time) * 100);
        if (state.shearHistory.length > 200) state.shearHistory.shift();

        // Growth history
        state.growthHistory.push(state.density);
        if (state.growthHistory.length > 100) state.growthHistory.shift();

        // CO₂ accumulation
        state.co2Total += state.density * 0.0001;

        // Random threat detection (rare — every ~60s for 5s)
        state.threatDetected = Math.sin(state.time * 0.1) > 0.95;

        // Update stat displays
        document.getElementById('stat-rpm').textContent = Math.round(state.vortexRPM).toLocaleString();
        document.getElementById('stat-density').textContent = state.density.toFixed(2);
        document.getElementById('stat-ph').textContent = state.ph.toFixed(2);
        document.getElementById('stat-temp').textContent = state.temp.toFixed(1);
    }


    // ═══════════════════════════════════════════════════════
    //  MAIN RENDER LOOP
    // ═══════════════════════════════════════════════════════

    let lastTime = 0;
    let frameCount = 0;

    function render(timestamp) {
        const dt = Math.min((timestamp - lastTime) / 1000, 0.1) || 0.016;
        lastTime = timestamp;
        frameCount++;

        updateSimulation(dt);
        updateClock();

        // Render all widgets
        drawPhaseLock();
        drawShearMonitor();
        drawNanobubble();
        drawVisionFeed();
        updateHanMatrix();
        drawGrowthCurve();
        drawReactor();
        drawWaveform();

        // Slower updates
        if (frameCount % 60 === 0) updateTicker();
        if (frameCount % 120 === 0) addTerminalLine();

        requestAnimationFrame(render);
    }

    function startAllEngines() {
        drawHexGrid();
        requestAnimationFrame(render);
        // Initial terminal lines
        addTerminalLine();
        setTimeout(addTerminalLine, 500);
        setTimeout(addTerminalLine, 1200);
    }

    // Handle resize
    window.addEventListener('resize', () => {
        drawHexGrid();
        const rc = document.getElementById('reactor-canvas');
        if (rc) {
            rc.width = rc.parentElement.clientWidth;
            rc.height = rc.parentElement.clientHeight;
            initParticles(rc.width / 2, rc.height / 2);
        }
    });


    // ═══════════════════════════════════════════════════════
    //  TELEMETRY BRIDGE INTEGRATION
    // ═══════════════════════════════════════════════════════

    let bridge = null;

    function initTelemetryBridge() {
        if (typeof window.TelemetryBridge === 'undefined') {
            console.log('[HUD] TelemetryBridge not loaded — using LOCAL simulation only');
            return;
        }

        bridge = new window.TelemetryBridge();

        bridge.onData = (liveState) => {
            // Override internal simulation state with live data
            state.ph = liveState.ph;
            state.density = liveState.density_g_l;
            state.temp = liveState.temperature_c;
            state.vortexRPM = liveState.vortexRPM;
            state.shearRate = liveState.shearRate;
            state.kLa = liveState.kLa;
            state.fleEfficiency = liveState.fleEfficiency;
            state.x1 = liveState.x1;
            state.x2 = liveState.x2;
            state.x3 = liveState.x3;
            state.co2Total = liveState.co2Total;
            state.threatDetected = liveState.threatDetected;
            state.ledFreq = liveState.led_freq_hz;

            // Use live history if available
            if (bridge.getHistory('shear').length > 10) {
                state.shearHistory = bridge.getHistory('shear');
            }
            if (bridge.getHistory('density').length > 10) {
                state.growthHistory = bridge.getHistory('density');
            }

            // Apply to DOM elements
            window.applyTelemetryToHUD(liveState);
        };

        bridge.onConnectionChange = (mode) => {
            addTerminalLine();  // Log the connection event
        };

        // Attempt connection (non-blocking — falls back gracefully)
        bridge.connect();
    }


    // ═══════════════════════════════════════════════════════
    //  INIT
    // ═══════════════════════════════════════════════════════

    document.addEventListener('DOMContentLoaded', () => {
        runBootSequence();
        // Attempt live bridge after boot completes
        setTimeout(initTelemetryBridge, 3500);
    });

})();
