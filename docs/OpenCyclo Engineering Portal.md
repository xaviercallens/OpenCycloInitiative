<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenCyclo Engineering Portal | Active Development Hub</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@300;400;600;800&display=swap');
        
        :root {
            --slate-950: #020617;
            --cyan-500: #06b6d4;
            --emerald-500: #10b981;
            --amber-500: #f59e0b;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--slate-950);
            color: #e2e8f0;
            overflow-x: hidden;
        }

        .mono { font-family: 'JetBrains Mono', monospace; }

        .hud-border {
            border: 1px solid rgba(6, 182, 212, 0.2);
            background: rgba(15, 23, 42, 0.8);
            backdrop-filter: blur(10px);
        }

        .sidebar-item {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border-left: 2px solid transparent;
        }

        .sidebar-item:hover, .sidebar-active {
            background: rgba(6, 182, 212, 0.1);
            border-left-color: var(--cyan-500);
            color: var(--cyan-500);
            padding-left: 1.5rem;
        }

        .chart-container {
            position: relative;
            width: 100%;
            height: 280px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
        }

        .tech-card {
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: border-color 0.3s;
        }

        .tech-card:hover {
            border-color: rgba(6, 182, 212, 0.4);
        }

        /* Scanline Effect */
        .scanline {
            width: 100%;
            height: 100px;
            background: linear-gradient(to bottom, transparent, rgba(6, 182, 212, 0.02), transparent);
            position: fixed;
            top: -100px;
            animation: scan 12s linear infinite;
            pointer-events: none;
            z-index: 100;
        }
        @keyframes scan { from { top: -100px; } to { top: 100vh; } }

        /* Custom Scrollbar */
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: var(--slate-950); }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }
    </style>
</head>
<!-- Chosen Palette: "Stark-Tech Engineering"
     Background: Slate 950 (#020617) for high-contrast focus.
     Primary Tech: Cyan 500 (#06b6d4) for UI/Blueprints.
     Primary Bio: Emerald 500 (#10b981) for validation/success.
     Alert/Warning: Amber 500 (#f59e0b) for issues/OQ resolution.
-->

<!-- Application Structure Plan:
    1. Navigation Hub: Sidebar access to Library, Evaluation Lab, Code Repository, Simulation, and Global Feedback.
    2. Engineering HUD: Top-level stats on the Stoichiometric Constant (1.83) and current build status.
    3. Module: Technical Library (DOC-01 to DOC-12 explorer).
    4. Module: OQ Evaluation Lab (Interactive data charts for fluidics and shear stress).
    5. Module: Hardware Repository (Direct links to GitHub assets).
    6. Module: Hacker Lab (Submission form for decentralized node data).
-->

<!-- Visualization & Content Choices:
    - Performance Plot: Chart.js visualization of Shear Stress vs. Growth Rate.
    - Stoichiometry HUD: Large metrics for the 1.83 factor.
    - No SVG/Mermaid: Icons replaced with Unicode (⚙️, 💻, 🔬, 🌍).
-->

<!-- CONFIRMATION: NO SVG used. NO Mermaid JS used. -->

<body class="flex flex-col h-screen">

    <div class="scanline"></div>

    <!-- Header / HUD Stats -->
    <header class="h-16 border-b border-white/10 flex items-center px-6 justify-between shrink-0 z-50 bg-slate-950">
        <div class="flex items-center gap-4">
            <div class="w-8 h-8 border border-cyan-500 flex items-center justify-center font-bold text-cyan-500 mono text-lg">E</div>
            <div class="leading-none">
                <h1 class="text-sm font-black uppercase tracking-tighter">OpenCyclo <span class="text-cyan-500">Engineering Portal</span></h1>
                <p class="text-[8px] text-slate-500 uppercase tracking-widest font-bold mono">Active Environment: v2.0.4-Build</p>
            </div>
        </div>
        
        <div class="hidden md:flex gap-8 text-[10px] mono font-bold uppercase tracking-widest text-slate-400">
            <div class="flex items-center gap-2">
                <span class="status-dot bg-emerald-500"></span> 
                <span>STOICHIOMETRY: 1.83kg_CO2/kg</span>
            </div>
            <div class="flex items-center gap-2">
                <span class="status-dot bg-cyan-500"></span> 
                <span>ALPHA_NODE: Contes, FR</span>
            </div>
            <div class="flex items-center gap-2">
                <span class="status-dot bg-amber-500"></span> 
                <span>OQ_PROTOCOL: ACTIVE</span>
            </div>
        </div>
    </header>

    <div class="flex flex-grow overflow-hidden">
        
        <!-- Navigation Sidebar -->
        <aside class="w-64 border-r border-white/5 flex flex-col p-4 gap-6 shrink-0 bg-slate-900/50">
            <div class="space-y-1">
                <div class="text-[9px] font-bold text-slate-500 uppercase tracking-widest px-4 mb-2">Core_Modules</div>
                <button onclick="switchModule('library')" id="nav-library" class="sidebar-item sidebar-active w-full text-left px-4 py-3 text-xs font-bold uppercase flex items-center gap-3">
                    <span>📚</span> Technical Library
                </button>
                <button onclick="switchModule('repo')" id="nav-repo" class="sidebar-item w-full text-left px-4 py-3 text-xs font-bold uppercase flex items-center gap-3">
                    <span>💻</span> Code & CAD Hub
                </button>
                <button onclick="switchModule('lab')" id="nav-lab" class="sidebar-item w-full text-left px-4 py-3 text-xs font-bold uppercase flex items-center gap-3">
                    <span>🔬</span> Evaluation Lab
                </button>
                <button onclick="switchModule('sim')" id="nav-sim" class="sidebar-item w-full text-left px-4 py-3 text-xs font-bold uppercase flex items-center gap-3">
                    <span>🧠</span> CycloTwin SITL
                </button>
                <button onclick="switchModule('hacker')" id="nav-hacker" class="sidebar-item w-full text-left px-4 py-3 text-xs font-bold uppercase flex items-center gap-3">
                    <span>🛠️</span> Experiment Feed
                </button>
            </div>

            <div class="mt-auto p-4 hud-border rounded-sm">
                <div class="text-[8px] font-bold text-cyan-500 uppercase mb-2">Build Target</div>
                <div class="text-xl font-black">10.0 Gt</div>
                <div class="text-[8px] text-slate-500 uppercase">Annual Removal Goal</div>
            </div>
        </aside>

        <!-- Main Workspace -->
        <main class="flex-grow overflow-y-auto p-8 relative">
            
            <!-- Technical Library Module -->
            <div id="module-library" class="module animate-fade-in">
                <div class="flex justify-between items-end mb-8 border-b border-white/10 pb-6">
                    <div>
                        <h2 class="text-3xl font-black uppercase tracking-tighter">Technical <span class="text-cyan-500">Registry</span></h2>
                        <p class="text-slate-400 text-sm mt-1">Exploring strategic documents DOC-01 through DOC-12.</p>
                    </div>
                    <div class="text-[10px] mono text-slate-500">12 TOTAL FILES FOUND</div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" id="library-grid">
                    <!-- Cards injected by JS -->
                </div>
            </div>

            <!-- Repository Module -->
            <div id="module-repo" class="module hidden animate-fade-in">
                <div class="flex justify-between items-end mb-8 border-b border-white/10 pb-6">
                    <div>
                        <h2 class="text-3xl font-black uppercase tracking-tighter">Code & <span class="text-cyan-500">CAD Assets</span></h2>
                        <p class="text-slate-400 text-sm mt-1">Direct repository integration: xaviercallens/OpenCycloInitiative</p>
                    </div>
                    <a href="https://github.com/xaviercallens/OpenCycloInitiative" target="_blank" class="bg-white text-slate-950 px-4 py-2 text-[10px] font-black uppercase hover:bg-cyan-500 transition">View Repo</a>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div class="hud-border p-8 border-l-4 border-cyan-500">
                        <div class="flex justify-between mb-6">
                            <span class="text-3xl">⚙️</span>
                            <span class="text-[9px] mono text-cyan-500">/CAD/SMU-1000/</span>
                        </div>
                        <h4 class="font-bold mb-2 uppercase">Industrial Blueprints</h4>
                        <p class="text-xs text-slate-400 mb-6 leading-relaxed">
                            Complete .STEP and .STL assemblies for the SMU-1000 industrial unit. Optimized 3:1 H:D ratio for maximizing volumetric light intensity.
                        </p>
                        <div class="space-y-1 text-[9px] mono text-slate-500">
                            <div class="flex justify-between"><span>smu-frame-v1.step</span> <span class="text-emerald-500">✓</span></div>
                            <div class="flex justify-between"><span>sparger-nanobubble.stl</span> <span class="text-emerald-500">✓</span></div>
                            <div class="flex justify-between"><span>vortex-manifold.step</span> <span class="text-emerald-500">✓</span></div>
                        </div>
                    </div>

                    <div class="hud-border p-8 border-l-4 border-emerald-500">
                        <div class="flex justify-between mb-6">
                            <span class="text-3xl">🧠</span>
                            <span class="text-[9px] mono text-emerald-500">/scripts/python/</span>
                        </div>
                        <h4 class="font-bold mb-2 uppercase">AI Control Logic</h4>
                        <p class="text-xs text-slate-400 mb-6 leading-relaxed">
                            Python-based control loops for ROS2 hardware abstraction. Includes YOLOv8 models for biosecurity and culture density monitoring.
                        </p>
                        <div class="space-y-1 text-[9px] mono text-slate-500">
                            <div class="flex justify-between"><span>biosecurity_yolo.py</span> <span class="text-emerald-500">✓</span></div>
                            <div class="flex justify-between"><span>sparge_freq_opt.py</span> <span class="text-emerald-500">✓</span></div>
                            <div class="flex justify-between"><span>telemetry_sync.py</span> <span class="text-emerald-500">✓</span></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Evaluation Lab Module -->
            <div id="module-lab" class="module hidden animate-fade-in">
                <div class="flex justify-between items-end mb-8 border-b border-white/10 pb-6">
                    <div>
                        <h2 class="text-3xl font-black uppercase tracking-tighter">OQ <span class="text-amber-500">Evaluation Lab</span></h2>
                        <p class="text-slate-400 text-sm mt-1">Reviewing resolution protocols OQ1-OQ8. Evaluate fluid dynamics and growth efficiency.</p>
                    </div>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div class="lg:col-span-2 hud-border p-8">
                        <h4 class="text-xs font-bold uppercase mb-6 text-slate-400">Shear Stress vs. Growth Rate Validation</h4>
                        <div class="chart-container">
                            <canvas id="labChart"></canvas>
                        </div>
                        <div class="mt-6 p-4 bg-slate-900 border border-white/5 text-[10px] mono">
                            <span class="text-amber-500 font-bold uppercase">FINDING [OQ-03]:</span> 
                            Tangential offset of 38mm reduced shear stress by 14.2% while maintaining CO2 mass transfer rates > 0.8g/L-h.
                        </div>
                    </div>
                    
                    <div class="space-y-4">
                        <div class="hud-border p-6 bg-amber-500/5 border-l-2 border-amber-500">
                            <h5 class="text-[10px] font-bold text-amber-500 uppercase mb-2">Complement Proposal</h5>
                            <p class="text-xs text-slate-300 mb-4">Have you validated the 3:1 H:D ratio on smaller 10L prototypes? Share your findings.</p>
                            <button class="w-full py-2 bg-amber-500 text-slate-950 text-[10px] font-black uppercase">Submit Peer Evaluation</button>
                        </div>
                        <div class="hud-border p-6 bg-cyan-500/5 border-l-2 border-cyan-500">
                            <h5 class="text-[10px] font-bold text-cyan-500 uppercase mb-2">Review Protocol OQ-06</h5>
                            <p class="text-xs text-slate-300">Analysis of the synthetic data pipeline for YOLOv8 sniper-vision training.</p>
                            <button class="w-full py-2 border border-cyan-500 text-cyan-500 text-[10px] font-bold uppercase">Read DOC-06</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Hacker Experiment Feed -->
            <div id="module-hacker" class="module hidden animate-fade-in">
                <div class="mb-8">
                    <h2 class="text-3xl font-black uppercase tracking-tighter">Global <span class="text-emerald-500">Hacker Feed</span></h2>
                    <p class="text-slate-400 text-sm mt-1">Decentralized inventors sharing real-world growth data from the V0.1 Alpha Garage Pilot (DOC-07).</p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
                    <!-- Submission Form -->
                    <div class="hud-border p-8 bg-emerald-500/5 border-emerald-500/20">
                        <h4 class="text-xs font-bold uppercase mb-6 text-emerald-500">Post Build Data</h4>
                        <div class="space-y-4">
                            <div>
                                <label class="block text-[10px] uppercase font-bold text-slate-500 mb-1">Pilot Location</label>
                                <input type="text" placeholder="e.g. Berlin, DE" class="w-full bg-slate-950 border border-white/10 p-2 text-xs focus:border-emerald-500 outline-none">
                            </div>
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <label class="block text-[10px] uppercase font-bold text-slate-500 mb-1">CO2 Absorption ($g/L-h$)</label>
                                    <input type="text" placeholder="0.85" class="w-full bg-slate-950 border border-white/10 p-2 text-xs focus:border-emerald-500 outline-none">
                                </div>
                                <div>
                                    <label class="block text-[10px] uppercase font-bold text-slate-500 mb-1">Culture Density ($g/L$)</label>
                                    <input type="text" placeholder="5.2" class="w-full bg-slate-950 border border-white/10 p-2 text-xs focus:border-emerald-500 outline-none">
                                </div>
                            </div>
                            <button class="w-full py-3 bg-emerald-500 text-slate-950 text-xs font-black uppercase hover:bg-white transition">Sync to Project Genesis</button>
                        </div>
                    </div>

                    <!-- Live Feed (Mock) -->
                    <div class="space-y-4">
                        <div class="hud-border p-4 bg-slate-900/40">
                            <div class="flex justify-between items-start mb-2">
                                <span class="text-[9px] font-bold text-emerald-500 uppercase">Status: SUCCESS</span>
                                <span class="text-[9px] mono text-slate-500">2h ago</span>
                            </div>
                            <p class="text-[11px] text-slate-300"><strong>User_0842 (San Diego, US):</strong> Validated 19L Garage Pilot. Reached 0.72g/L-h using standard aquarium limewood sparger. High bio-stability achieved.</p>
                        </div>
                        <div class="hud-border p-4 bg-slate-900/40">
                            <div class="flex justify-between items-start mb-2">
                                <span class="text-[9px] font-bold text-amber-500 uppercase">Status: PENDING</span>
                                <span class="text-[9px] mono text-slate-500">5h ago</span>
                            </div>
                            <p class="text-[11px] text-slate-300"><strong>Hacker_X (Lyon, FR):</strong> Testing Raspberry Pi Zero W integration for real-time pH tuning. Encountered sensor drift in high salinity.</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- SIM Simulation Module -->
            <div id="module-sim" class="module hidden animate-fade-in">
                <div class="flex justify-between items-center mb-12">
                    <h2 class="text-3xl font-black uppercase tracking-tighter">CycloTwin <span class="text-cyan-500">SITL</span></h2>
                    <span class="text-[10px] font-bold bg-cyan-500/10 text-cyan-400 px-3 py-1 border border-cyan-500/30">SIMULATION MODE: ACTIVE</span>
                </div>
                
                <div class="flex flex-col items-center justify-center min-h-[400px] border border-dashed border-white/10 rounded-lg p-12 text-center bg-slate-900/20">
                    <div class="text-5xl mb-6">🧠</div>
                    <h3 class="text-xl font-bold uppercase mb-2">Software-in-the-Loop Environment</h3>
                    <p class="text-sm text-slate-500 max-w-md mb-8 leading-relaxed">
                        Connect your local ROS2 workspace to the CycloTwin multi-physics backend. Test AI biosecurity models against synthetic Godot/Blender vision streams.
                    </p>
                    <div class="flex gap-4">
                        <button class="px-6 py-2 bg-cyan-500 text-slate-950 text-[10px] font-black uppercase">Launch SITL Engine</button>
                        <button class="px-6 py-2 border border-white/20 text-white text-[10px] font-bold uppercase">Download Mock Dataset</button>
                    </div>
                </div>
            </div>

        </main>
    </div>

    <!-- Background Decoration -->
    <div class="fixed bottom-0 right-0 p-4 pointer-events-none opacity-20">
        <div class="text-[150px] font-black text-slate-900 select-none">OPENCYCLO</div>
    </div>

    <script>
        // --- DATA REGISTRY ---
        const docs = [
            { id: "DOC-01", title: "State of Art BioCCUS 2026", phase: "Strategy", icon: "📚" },
            { id: "DOC-02", title: "Evolution Roadmap", phase: "Strategy", icon: "📊" },
            { id: "DOC-03", title: "OpenCyclo Manifesto", phase: "Hardware", icon: "📜" },
            { id: "DOC-04", title: "Blueprint SMU-1000", phase: "Hardware", icon: "⚙️" },
            { id: "DOC-05", title: "Asset Specifications", phase: "Hardware", icon: "📁" },
            { id: "DOC-06", title: "Resolution OQ1-OQ8", phase: "Hardware", icon: "🔬" },
            { id: "DOC-07", title: "Garage Hacker Pilot", phase: "Validation", icon: "🛠️" },
            { id: "DOC-08", title: "CycloTwin Spec", phase: "Digital Twin", icon: "🧠" },
            { id: "DOC-09", title: "Implementation Guide", phase: "Digital Twin", icon: "💻" },
            { id: "DOC-10", title: "JARVIS HUD Spec", phase: "Planetary", icon: "🖥️" },
            { id: "DOC-11", title: "CycloEarth engine", phase: "Planetary", icon: "🌍" },
            { id: "DOC-12", title: "Project Genesis GCP", phase: "Planetary", icon: "📡" }
        ];

        // --- APP LOGIC ---

        function switchModule(id) {
            // Update UI
            document.querySelectorAll('.module').forEach(m => m.classList.add('hidden'));
            document.getElementById(`module-${id}`).classList.remove('hidden');

            document.querySelectorAll('.sidebar-item').forEach(item => item.classList.remove('sidebar-active'));
            document.getElementById(`nav-${id}`).classList.add('sidebar-active');
        }

        function renderLibrary() {
            const grid = document.getElementById('library-grid');
            grid.innerHTML = docs.map(doc => `
                <div class="tech-card p-6 bg-slate-900/40 rounded-sm cursor-pointer group">
                    <div class="flex justify-between items-start mb-4">
                        <span class="text-2xl">${doc.icon}</span>
                        <span class="text-[8px] mono text-slate-500 uppercase tracking-widest">${doc.phase}</span>
                    </div>
                    <h5 class="text-xs font-black uppercase text-slate-300 group-hover:text-cyan-400 transition">${doc.id}</h5>
                    <p class="text-[11px] font-bold text-white mt-1">${doc.title}</p>
                    <div class="mt-4 flex items-center justify-between opacity-0 group-hover:opacity-100 transition">
                        <span class="text-[8px] text-cyan-500 font-bold uppercase">Access_Document</span>
                        <span class="text-xs text-cyan-500">➔</span>
                    </div>
                </div>
            `).join('');
        }

        // --- CHARTS ---
        function initCharts() {
            const ctx = document.getElementById('labChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['0', '10', '20', '30', '40', '50', '60'],
                    datasets: [
                        {
                            label: 'Standard Growth (%)',
                            data: [0, 15, 35, 55, 70, 85, 95],
                            borderColor: '#1e293b',
                            borderDash: [5, 5],
                            tension: 0.4
                        },
                        {
                            label: 'OQ-03 Optimized Growth (%)',
                            data: [0, 20, 45, 75, 92, 98, 100],
                            borderColor: '#06b6d4',
                            backgroundColor: 'rgba(6, 182, 212, 0.1)',
                            fill: true,
                            tension: 0.4,
                            borderWidth: 3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: '#64748b', font: { size: 10 } } }
                    },
                    scales: {
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b', font: { size: 8 } } },
                        x: { grid: { display: false }, ticks: { color: '#64748b', font: { size: 8 } } }
                    }
                }
            });
        }

        // Initialize
        window.onload = () => {
            renderLibrary();
            initCharts();
        };
    </script>
</body>
</html>