/* ═══════════════════════════════════════════════════════ */
/*  Cyclo-Earth: Project Genesis — JavaScript Engine       */
/*  Interactive Planetary Symbiosis Simulator               */
/* ═══════════════════════════════════════════════════════ */

(() => {
    'use strict';

    // ─── COLORS ───
    const CC = {
        VOID: '#03050A',
        CYAN: '#00E5FF',
        EMERALD: '#00FF66',
        AMBER: '#FFC400',
        CRIMSON: '#FF4500',
    };

    // ═══════════════════════════════════════════════════════
    //  CLIMATE MODEL (Simplified Hector-lite in browser)
    // ═══════════════════════════════════════════════════════

    const CLIMATE = {
        // Baseline
        co2_2025: 421,       // ppm
        temp_2025: 1.2,      // °C anomaly
        bau_emissions: 10.5, // GtC/yr (BAU fossil)
        bau_growth: 0.005,   // BAU emission growth rate

        // Conversion
        ppm_per_gtc: 2.12 / 1000 * 1e3, // ~0.47 ppm per GtC

        // Climate sensitivity
        ecs: 3.0,            // °C per doubling
        airborne_fraction: 0.44,

        // Stoichiometry
        co2_to_c_ratio: 12 / 44, // GtCO2 → GtC
    };

    function runSimulation(reactorSlider, biocharSlider, reforestSlider) {
        const years = [];
        const co2_psc = [];
        const co2_bau = [];
        const temp_psc = [];
        const temp_bau = [];
        const net_emissions = [];

        // Scale slider values (0-100) to physical parameters
        const reactorPower = reactorSlider / 100;
        const biocharPower = biocharSlider / 100;
        const reforestPower = reforestSlider / 100;

        // Fleet scaling: 1 unit → 100M nodes (exponential)
        const initialModules = Math.max(1, Math.pow(10, reactorPower * 8));
        const growthRate = 1.0 + reactorPower * 1.5; // 1x to 2.5x/yr
        const maxModules = 1e8;

        // Biochar: 0 to 500M hectares
        const biocharHectares = biocharPower * 500e6;
        const biocharYield = 0.35;
        const biocharCarbonContent = 0.78;

        // Reforestation: 0 to 1 trillion trees
        const trees = reforestPower * 1e12;
        const treeSeqPerYear = 22; // kg CO₂ per tree per year
        const treeGtC = (trees * treeSeqPerYear * 1e-12) * CLIMATE.co2_to_c_ratio;

        let co2 = CLIMATE.co2_2025;
        let co2_b = CLIMATE.co2_2025;
        let temp = CLIMATE.temp_2025;
        let temp_b = CLIMATE.temp_2025;
        let goldenCross = null;
        let cumulBiochar = 0;

        for (let year = 2025; year <= 2100; year++) {
            const t = year - 2025;

            // BAU emissions
            const bauEmissions = CLIMATE.bau_emissions * (1 + CLIMATE.bau_growth * t);

            // --- PSC Fluxes ---

            // F_cyclo: fleet CO₂ capture
            const nModules = Math.min(initialModules * Math.pow(growthRate, t), maxModules);
            const capturePerModule = 6.0 * 1000 * 1.83 * 0.92 * 365.25 / 1e15; // GtCO₂
            const fCyclo = nModules * capturePerModule;
            const fCycloGtC = fCyclo * CLIMATE.co2_to_c_ratio;

            // F_char: biochar sequestration
            const biomassFromCyclo = fCyclo / 1.83; // Gt dry biomass
            const charC = biomassFromCyclo * biocharYield * biocharCarbonContent * (biocharPower);
            cumulBiochar += charC;

            // F_soil: soil feedback
            const soilGain = cumulBiochar * 0.004 * (1 - Math.exp(-cumulBiochar * 5));

            // Reforestation
            const reforestC = treeGtC * Math.min(1, t / 20); // Trees mature over 20 years

            // Net emissions
            const netGtC = bauEmissions - fCycloGtC - charC - soilGain - reforestC;

            // PSC climate step
            const dCO2 = netGtC * CLIMATE.airborne_fraction * 0.47;
            co2 = Math.max(200, co2 + dCO2);

            // BAU climate step
            const dCO2_bau = bauEmissions * CLIMATE.airborne_fraction * 0.47;
            co2_b = co2_b + dCO2_bau;

            // Temperature (simplified ECS)
            const rf = 5.35 * Math.log(co2 / 280);
            temp = rf * (CLIMATE.ecs / (5.35 * Math.log(2)));

            const rf_b = 5.35 * Math.log(co2_b / 280);
            temp_b = rf_b * (CLIMATE.ecs / (5.35 * Math.log(2)));

            // Golden Cross detection
            if (netGtC < 0 && goldenCross === null) {
                goldenCross = year;
            }

            years.push(year);
            co2_psc.push(co2);
            co2_bau.push(co2_b);
            temp_psc.push(temp);
            temp_bau.push(temp_b);
            net_emissions.push(netGtC);
        }

        const final = years.length - 1;
        return {
            years,
            co2_psc,
            co2_bau,
            temp_psc,
            temp_bau,
            net_emissions,
            goldenCross,
            final_co2: co2_psc[final],
            final_temp: temp_psc[final],
            final_co2_bau: co2_bau[final],
            final_temp_bau: temp_bau[final],
            nModulesMax: Math.min(initialModules * Math.pow(growthRate, 75), maxModules),
        };
    }

    // ═══════════════════════════════════════════════════════
    //  3D GLOBE (Canvas 2D with projection)
    // ═══════════════════════════════════════════════════════

    let globeAngle = 0;
    const dots = [];
    const reactorNodes = [];

    // Generate landmass dots (simplified)
    function generateGlobeDots() {
        dots.length = 0;
        // Generate ~3000 random points on sphere, filter to crude landmass
        for (let i = 0; i < 3000; i++) {
            const lat = (Math.random() - 0.5) * Math.PI;
            const lon = Math.random() * Math.PI * 2;

            // Very crude land filter (approximate)
            const isLand = isLandApprox(lat * 180 / Math.PI, lon * 180 / Math.PI);

            dots.push({
                lat, lon,
                isLand,
                brightness: isLand ? 0.3 + Math.random() * 0.4 : 0,
                size: isLand ? 1 + Math.random() * 1.5 : 0.5,
            });
        }
    }

    function isLandApprox(latDeg, lonDeg) {
        // Very rough approximation — enough for visual effect
        // North America
        if (latDeg > 25 && latDeg < 70 && lonDeg > 190 && lonDeg < 310) return Math.random() > 0.4;
        // South America
        if (latDeg > -55 && latDeg < 12 && lonDeg > 280 && lonDeg < 330) return Math.random() > 0.5;
        // Europe
        if (latDeg > 35 && latDeg < 70 && lonDeg > -10 + 360 && lonDeg < 40 + 360) return Math.random() > 0.5;
        if (latDeg > 35 && latDeg < 70 && lonDeg > 350) return Math.random() > 0.5;
        if (latDeg > 35 && latDeg < 70 && lonDeg < 40) return Math.random() > 0.5;
        // Africa
        if (latDeg > -35 && latDeg < 35 && lonDeg > 345 || (latDeg > -35 && latDeg < 35 && lonDeg < 50)) return Math.random() > 0.5;
        // Asia
        if (latDeg > 10 && latDeg < 70 && lonDeg > 40 && lonDeg < 180) return Math.random() > 0.4;
        // Australia
        if (latDeg > -40 && latDeg < -10 && lonDeg > 110 && lonDeg < 155) return Math.random() > 0.5;
        return false;
    }

    function generateReactorNodes(power) {
        reactorNodes.length = 0;
        const count = Math.floor(power * 200);
        for (let i = 0; i < count; i++) {
            const lat = (Math.random() - 0.5) * Math.PI * 0.85;
            const lon = Math.random() * Math.PI * 2;
            // Bias toward industrial zones / coastlines
            if (isLandApprox(lat * 180 / Math.PI, lon * 180 / Math.PI) || Math.random() > 0.7) {
                reactorNodes.push({ lat, lon, phase: Math.random() * Math.PI * 2 });
            }
        }
    }

    function drawGlobe(canvas, reactorPower, healthLevel) {
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        if (canvas.width !== canvas.parentElement.clientWidth) {
            canvas.width = canvas.parentElement.clientWidth;
            canvas.height = canvas.parentElement.clientHeight;
        }

        const w = canvas.width;
        const h = canvas.height;
        const cx = w / 2;
        const cy = h / 2;
        const R = Math.min(w, h) * 0.32;

        ctx.clearRect(0, 0, w, h);

        // Starfield background
        if (!canvas._stars) {
            canvas._stars = [];
            for (let i = 0; i < 300; i++) {
                canvas._stars.push({
                    x: Math.random() * w,
                    y: Math.random() * h,
                    s: 0.5 + Math.random() * 1,
                    b: 0.3 + Math.random() * 0.7,
                });
            }
        }
        canvas._stars.forEach(s => {
            ctx.beginPath();
            ctx.arc(s.x, s.y, s.s, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255,255,255,${s.b * 0.4})`;
            ctx.fill();
        });

        // Atmospheric haze
        const hazeAlpha = 0.03 + healthLevel * 0.04;
        const hazeColor = healthLevel > 0.5
            ? `rgba(0, 255, 102, ${hazeAlpha})`
            : `rgba(255, 69, 0, ${hazeAlpha})`;
        const hazeGrad = ctx.createRadialGradient(cx, cy, R * 0.8, cx, cy, R * 1.6);
        hazeGrad.addColorStop(0, 'transparent');
        hazeGrad.addColorStop(0.5, hazeColor);
        hazeGrad.addColorStop(1, 'transparent');
        ctx.fillStyle = hazeGrad;
        ctx.fillRect(0, 0, w, h);

        // Atmosphere glow ring
        ctx.beginPath();
        ctx.arc(cx, cy, R + 8, 0, Math.PI * 2);
        ctx.strokeStyle = healthLevel > 0.5
            ? `rgba(0, 229, 255, ${0.08 + healthLevel * 0.08})`
            : `rgba(255, 69, 0, 0.06)`;
        ctx.lineWidth = 16;
        ctx.stroke();

        // Globe circle (dark ocean)
        ctx.beginPath();
        ctx.arc(cx, cy, R, 0, Math.PI * 2);
        ctx.fillStyle = '#060a12';
        ctx.fill();

        globeAngle += 0.003;

        // Plot landmass dots
        dots.forEach(d => {
            if (!d.isLand) return;
            const x3d = Math.cos(d.lat) * Math.cos(d.lon + globeAngle);
            const y3d = Math.sin(d.lat);
            const z3d = Math.cos(d.lat) * Math.sin(d.lon + globeAngle);

            if (z3d < -0.1) return; // behind globe

            const sx = cx + x3d * R;
            const sy = cy - y3d * R;
            const alpha = 0.1 + z3d * 0.5;

            ctx.beginPath();
            ctx.arc(sx, sy, d.size * (0.5 + z3d * 0.5), 0, Math.PI * 2);
            ctx.fillStyle = `rgba(180, 200, 220, ${alpha * d.brightness})`;
            ctx.fill();
        });

        // Reactor nodes (cyan dots)
        reactorNodes.forEach(n => {
            const x3d = Math.cos(n.lat) * Math.cos(n.lon + globeAngle);
            const y3d = Math.sin(n.lat);
            const z3d = Math.cos(n.lat) * Math.sin(n.lon + globeAngle);

            if (z3d < 0) return;

            const sx = cx + x3d * R;
            const sy = cy - y3d * R;
            const pulse = 0.5 + Math.sin(performance.now() * 0.003 + n.phase) * 0.5;

            ctx.beginPath();
            ctx.arc(sx, sy, 2 + pulse * 2, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(0, 229, 255, ${0.3 + z3d * 0.5 + pulse * 0.2})`;
            ctx.shadowColor = CC.CYAN;
            ctx.shadowBlur = 8;
            ctx.fill();
            ctx.shadowBlur = 0;
        });

        // Contes beacon (always visible — lat 43.8°N, lon 7.3°E)
        const contesLat = 43.8 * Math.PI / 180;
        const contesLon = 7.3 * Math.PI / 180;
        const cx3d = Math.cos(contesLat) * Math.cos(contesLon + globeAngle);
        const cy3d = Math.sin(contesLat);
        const cz3d = Math.cos(contesLat) * Math.sin(contesLon + globeAngle);

        if (cz3d > 0) {
            const csx = cx + cx3d * R;
            const csy = cy - cy3d * R;
            const cPulse = 0.5 + Math.sin(performance.now() * 0.005) * 0.5;

            // Outer ring
            ctx.beginPath();
            ctx.arc(csx, csy, 6 + cPulse * 4, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(0, 255, 102, ${0.4 + cPulse * 0.4})`;
            ctx.lineWidth = 1.5;
            ctx.shadowColor = CC.EMERALD;
            ctx.shadowBlur = 12;
            ctx.stroke();

            // Inner dot
            ctx.beginPath();
            ctx.arc(csx, csy, 3, 0, Math.PI * 2);
            ctx.fillStyle = CC.EMERALD;
            ctx.fill();
            ctx.shadowBlur = 0;
        }

        // Biochar green aura on land (based on biochar slider)
        if (healthLevel > 0.2) {
            dots.forEach(d => {
                if (!d.isLand || Math.random() > healthLevel * 0.3) return;
                const x3d = Math.cos(d.lat) * Math.cos(d.lon + globeAngle);
                const y3d = Math.sin(d.lat);
                const z3d = Math.cos(d.lat) * Math.sin(d.lon + globeAngle);
                if (z3d < 0) return;

                const sx = cx + x3d * R;
                const sy = cy - y3d * R;

                ctx.beginPath();
                ctx.arc(sx, sy, 3, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(0, 255, 102, ${z3d * healthLevel * 0.15})`;
                ctx.fill();
            });
        }
    }


    // ═══════════════════════════════════════════════════════
    //  TIMELINE CHART
    // ═══════════════════════════════════════════════════════

    function drawTimeline(canvas, results) {
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;
        const pad = { l: 35, r: 10, t: 10, b: 20 };

        ctx.clearRect(0, 0, w, h);

        const plotW = w - pad.l - pad.r;
        const plotH = h - pad.t - pad.b;

        // Axes
        ctx.strokeStyle = 'rgba(255,255,255,0.08)';
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(pad.l, pad.t);
        ctx.lineTo(pad.l, h - pad.b);
        ctx.lineTo(w - pad.r, h - pad.b);
        ctx.stroke();

        // Y-axis label
        ctx.font = '8px "Fira Code"';
        ctx.fillStyle = 'rgba(255,255,255,0.3)';
        ctx.fillText('CO₂', 2, pad.t + 8);

        // X-axis years
        [2025, 2050, 2075, 2100].forEach(yr => {
            const x = pad.l + ((yr - 2025) / 75) * plotW;
            ctx.fillText(yr.toString(), x - 10, h - 4);
        });

        const allCO2 = [...results.co2_bau, ...results.co2_psc];
        const minCO2 = Math.min(...allCO2) - 20;
        const maxCO2 = Math.max(...allCO2) + 20;

        const toX = (i) => pad.l + (i / (results.years.length - 1)) * plotW;
        const toY = (v) => pad.t + plotH - ((v - minCO2) / (maxCO2 - minCO2)) * plotH;

        // BAU line (red)
        ctx.beginPath();
        results.co2_bau.forEach((v, i) => {
            const x = toX(i), y = toY(v);
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.strokeStyle = CC.CRIMSON;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 3]);
        ctx.stroke();
        ctx.setLineDash([]);

        // PSC line (cyan → emerald based on health)
        ctx.beginPath();
        results.co2_psc.forEach((v, i) => {
            const x = toX(i), y = toY(v);
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.strokeStyle = results.goldenCross ? CC.EMERALD : CC.CYAN;
        ctx.lineWidth = 2;
        ctx.shadowColor = results.goldenCross ? CC.EMERALD : CC.CYAN;
        ctx.shadowBlur = 6;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Golden Cross marker
        if (results.goldenCross) {
            const gcIdx = results.goldenCross - 2025;
            const gcX = toX(gcIdx);
            ctx.beginPath();
            ctx.moveTo(gcX, pad.t);
            ctx.lineTo(gcX, h - pad.b);
            ctx.strokeStyle = 'rgba(0,255,102,0.3)';
            ctx.lineWidth = 1;
            ctx.setLineDash([2, 2]);
            ctx.stroke();
            ctx.setLineDash([]);

            ctx.font = '7px "Fira Code"';
            ctx.fillStyle = CC.EMERALD;
            ctx.fillText(`NET ZERO ${results.goldenCross}`, gcX - 25, pad.t + 10);
        }

        // Legend
        ctx.font = '7px "Fira Code"';
        ctx.fillStyle = CC.CRIMSON;
        ctx.fillText('BAU', w - pad.r - 22, pad.t + 10);
        ctx.fillStyle = results.goldenCross ? CC.EMERALD : CC.CYAN;
        ctx.fillText('PSC', w - pad.r - 22, pad.t + 20);
    }


    // ═══════════════════════════════════════════════════════
    //  REALITY SYNC CHART
    // ═══════════════════════════════════════════════════════

    let syncTime = 0;

    function drawSyncChart() {
        const canvas = document.getElementById('sync-chart-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;

        ctx.clearRect(0, 0, w, h);
        syncTime += 0.05;

        // Simulated line (cyan dashed)
        ctx.beginPath();
        for (let x = 0; x < w; x++) {
            const t = x / w * 24;
            const y = h / 2 - Math.sin(t * 0.3 + 0.5) * 15 - t * 0.7;
            x === 0 ? ctx.moveTo(x, y + h * 0.3) : ctx.lineTo(x, y + h * 0.3);
        }
        ctx.setLineDash([3, 3]);
        ctx.strokeStyle = 'rgba(0,229,255,0.4)';
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.setLineDash([]);

        // Real line (emerald solid)
        ctx.beginPath();
        for (let x = 0; x < w; x++) {
            const t = x / w * 24;
            const y = h / 2 - Math.sin(t * 0.3 + 0.3) * 14 - t * 0.65 + Math.sin(t + syncTime) * 2;
            x === 0 ? ctx.moveTo(x, y + h * 0.3) : ctx.lineTo(x, y + h * 0.3);
        }
        ctx.strokeStyle = CC.EMERALD;
        ctx.lineWidth = 1.5;
        ctx.shadowColor = 'rgba(0,255,102,0.3)';
        ctx.shadowBlur = 4;
        ctx.stroke();
        ctx.shadowBlur = 0;
    }


    // ═══════════════════════════════════════════════════════
    //  UI UPDATE ENGINE
    // ═══════════════════════════════════════════════════════

    let currentResults = null;
    let goldenShown = false;

    function formatModules(n) {
        if (n < 1000) return `${Math.round(n)} Units`;
        if (n < 1e6) return `${(n / 1e3).toFixed(1)}K Units`;
        if (n < 1e9) return `${(n / 1e6).toFixed(1)}M Nodes`;
        return `${(n / 1e9).toFixed(1)}B Nodes`;
    }

    function formatHectares(pct) {
        const ha = pct / 100 * 500e6;
        if (ha < 1e6) return `${(ha / 1e3).toFixed(0)}K Hectares`;
        return `${(ha / 1e6).toFixed(0)}M Hectares`;
    }

    function formatTrees(pct) {
        const trees = pct / 100 * 1e12;
        if (trees < 1e9) return `${(trees / 1e6).toFixed(0)}M Trees`;
        return `${(trees / 1e9).toFixed(0)}B Trees`;
    }

    function onSliderChange() {
        const reactorVal = parseInt(document.getElementById('slider-reactors').value);
        const biocharVal = parseInt(document.getElementById('slider-biochar').value);
        const reforestVal = parseInt(document.getElementById('slider-reforest').value);

        // Update labels
        const modules = Math.max(1, Math.pow(10, reactorVal / 100 * 8));
        document.getElementById('val-reactors').textContent = formatModules(modules);
        document.getElementById('val-biochar').textContent = formatHectares(biocharVal);
        document.getElementById('val-reforest').textContent = formatTrees(reforestVal);

        // Run simulation
        currentResults = runSimulation(reactorVal, biocharVal, reforestVal);

        // Update globe reactor nodes
        generateReactorNodes(reactorVal / 100);

        // Update scoreboard
        updateScoreboard(currentResults);

        // Draw timeline
        drawTimeline(document.getElementById('timeline-canvas'), currentResults);
    }

    function updateScoreboard(r) {
        const tempEl = document.getElementById('score-temp');
        const co2El = document.getElementById('score-co2');
        const goldenEl = document.getElementById('score-golden');
        const barTemp = document.getElementById('bar-temp');
        const barCO2 = document.getElementById('bar-co2');
        const atmoOverlay = document.getElementById('atmo-overlay');

        // By 2100 values
        const finalTemp = r.final_temp;
        const finalCO2 = r.final_co2;

        tempEl.textContent = (finalTemp >= 0 ? '+' : '') + finalTemp.toFixed(1);
        co2El.textContent = Math.round(finalCO2);

        // Color coding
        const isCool = finalTemp < 1.5;
        tempEl.className = 'score-value' + (isCool ? ' cool' : (finalTemp < 2.0 ? ' cool' : ''));
        co2El.className = 'score-value' + (finalCO2 < 400 ? ' safe' : (finalCO2 < 450 ? ' cool' : ''));

        // Bars
        const tempPct = Math.min(100, Math.max(0, (finalTemp / 4) * 100));
        const co2Pct = Math.min(100, Math.max(0, ((finalCO2 - 280) / 300) * 100));
        barTemp.style.width = tempPct + '%';
        barCO2.style.width = co2Pct + '%';
        barTemp.className = 'score-bar-fill' + (isCool ? ' cool' : '');
        barCO2.className = 'score-bar-fill' + (finalCO2 < 400 ? ' cool' : '');

        // Golden Cross
        if (r.goldenCross) {
            goldenEl.textContent = r.goldenCross;
            goldenEl.className = 'score-value golden-cross-value safe';

            // Show celebration (once per threshold crossing)
            if (!goldenShown) {
                goldenShown = true;
                const popup = document.getElementById('golden-popup');
                popup.classList.remove('hidden');
                popup.classList.add('show');
                setTimeout(() => {
                    popup.classList.remove('show');
                    popup.classList.add('hidden');
                }, 4000);
            }
        } else {
            goldenEl.textContent = 'NEVER';
            goldenEl.className = 'score-value golden-cross-value';
            goldenShown = false;
        }

        // Atmosphere overlay
        const healthLevel = Math.max(0, Math.min(1, 1 - (finalTemp - 1.0) / 2.5));
        if (healthLevel > 0.5) {
            atmoOverlay.classList.add('healthy');
        } else {
            atmoOverlay.classList.remove('healthy');
        }
    }


    // ═══════════════════════════════════════════════════════
    //  LIVE CO₂ TICKER
    // ═══════════════════════════════════════════════════════

    let liveCO2 = 42.58;

    function updateLiveCO2() {
        liveCO2 += 0.01 + Math.random() * 0.02;
        document.getElementById('live-co2').textContent = liveCO2.toFixed(2);
    }


    // ═══════════════════════════════════════════════════════
    //  MAIN RENDER LOOP
    // ═══════════════════════════════════════════════════════

    let frameCount = 0;

    function render() {
        frameCount++;

        // Globe
        const reactorVal = parseInt(document.getElementById('slider-reactors')?.value || '0');
        const healthLevel = currentResults
            ? Math.max(0, Math.min(1, 1 - (currentResults.final_temp - 1.0) / 2.5))
            : 0.2;

        drawGlobe(document.getElementById('globe-canvas'), reactorVal / 100, healthLevel);

        // Sync chart (slower)
        if (frameCount % 3 === 0) drawSyncChart();
        if (frameCount % 60 === 0) updateLiveCO2();

        requestAnimationFrame(render);
    }


    // ═══════════════════════════════════════════════════════
    //  INIT & BOOT
    // ═══════════════════════════════════════════════════════

    function boot() {
        const overlay = document.getElementById('loading-overlay');
        const status = document.getElementById('loader-status');
        const app = document.getElementById('app');

        generateGlobeDots();

        setTimeout(() => status.textContent = 'Compiling climate equations...', 500);
        setTimeout(() => status.textContent = 'Initializing WebGL globe...', 1200);
        setTimeout(() => status.textContent = 'Connecting to alpha node...', 2000);

        setTimeout(() => {
            status.textContent = 'Earth System Model ready.';

            // Run default simulation (no intervention)
            currentResults = runSimulation(0, 0, 0);
            drawTimeline(document.getElementById('timeline-canvas'), currentResults);
            updateScoreboard(currentResults);

            // Transition
            setTimeout(() => {
                overlay.classList.add('done');
                app.classList.remove('hidden');
                app.style.opacity = '1';

                // Bind sliders
                ['slider-reactors', 'slider-biochar', 'slider-reforest'].forEach(id => {
                    document.getElementById(id).addEventListener('input', onSliderChange);
                });

                // Bind Initiate Button
                const initiateBtn = document.getElementById('initiate-btn');
                if (initiateBtn) {
                    initiateBtn.addEventListener('click', () => {
                        const heroHeader = document.getElementById('hero-header');
                        heroHeader.style.transition = 'opacity 1s ease';
                        heroHeader.style.opacity = '0';
                        setTimeout(() => heroHeader.classList.add('hidden'), 1000);
                    });
                }

                // Start render loop
                requestAnimationFrame(render);
            }, 500);
        }, 2500);
    }

    // Resize handler
    window.addEventListener('resize', () => {
        const canvas = document.getElementById('globe-canvas');
        if (canvas) {
            canvas.width = canvas.parentElement.clientWidth;
            canvas.height = canvas.parentElement.clientHeight;
            canvas._stars = null; // Regenerate starfield
        }
    });

    document.addEventListener('DOMContentLoaded', boot);

})();
