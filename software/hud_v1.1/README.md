# 🤖 C.Y.C.L.O.S. HUD v1.1 (React + Three.js)

This directory contains the modernized, next-generation build of the OpenCyclo Heads-Up Display. It has been ported from vanilla HTML/Canvas to a robust frontend stack using React 19, Vite, and React Three Fiber.

## ✨ Upgraded Features
1. **3D React Fiber Engine**: Transitioned the generic 2D hologram into a full Three.js scene utilizing `@react-three/fiber` and `@react-three/drei`.
2. **GLSL Vortex Particle System**: Custom vertex and fragment shaders powering a 100,000-particle mathematical representation of the physical Rankine vortex, colored by vertical height parameters and animated with orbital speeds tied to live RPM telemetry.
3. **Componentized Glassmorphism**: Clean `App.tsx` overlay components encapsulating the neon-cyan UI and maintaining the CRT scanline aesthetic.

## 🚀 Running Locally
You must have Node.js installed on your machine to execute the new HUD framework:

```bash
cd software/hud_v1.1
npm install
npm run dev
```

Navigate to the localhost port provided (usually `http://localhost:5173`) to view the 3D Holographic interface.
