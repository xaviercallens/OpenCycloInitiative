import { useState, useEffect } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, EffectComposer, Bloom } from '@react-three/drei'
import { VortexParticleSystem } from './VortexParticleSystem'

export default function App() {
  const [telemetry, setTelemetry] = useState({
    rpm: 3400,
    density: 6.84,
    ph: 6.80,
    klA: 135,
    shear: 1240
  })

  // Simulated live updates just to keep it engaging
  useEffect(() => {
    const interval = setInterval(() => {
      setTelemetry(prev => ({
        ...prev,
        rpm: Math.round(3400 + (Math.random() - 0.5) * 50),
        density: +(6.84 + (Math.random() - 0.5) * 0.05).toFixed(2),
        klA: Math.round(135 + (Math.random() - 0.5) * 5),
      }))
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      {/* 3D Hologram Canvas */}
      <Canvas camera={{ position: [0, 5, 20], fov: 45 }}>
        <color attach="background" args={['#03050A']} />
        <ambientLight intensity={0.5} />
        <VortexParticleSystem particleCount={100000} rpm={telemetry.rpm} />
        <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.5} />
      </Canvas>

      {/* 2D HTML/CSS Glassmorphism HUD Overlay */}
      <div className="hud-layer">
        <header className="hud-header">
          <div className="hud-title">C.Y.C.L.O.S. v1.1 <br /><span style={{ fontSize: 12, color: '#fff' }}>REACT FIBER PROTOTYPE</span></div>
          <div style={{ color: 'var(--cyan)', fontFamily: 'Fira Code', fontSize: 14 }}>
            NODE: CONTES-α // UPLINK SECURED
          </div>
        </header>

        <main className="hud-panels">
          <section className="panel">
            <h2 className="panel-title">HOLOGRAPHIC TELEMETRY</h2>
            <div className="stat-row">
              <span>VORTEX RPM</span>
              <span className="val-cyan">{telemetry.rpm}</span>
            </div>
            <div className="stat-row">
              <span>BIOMASS DENSITY</span>
              <span className="val-emerald">{telemetry.density} g/L</span>
            </div>
            <div className="stat-row">
              <span>pH LEVEL</span>
              <span className="val-cyan">{telemetry.ph}</span>
            </div>
            <div className="stat-row">
              <span>kLa (MASS TRANSFER)</span>
              <span className="val-cyan">{telemetry.klA} h⁻¹</span>
            </div>
            <div className="stat-row">
              <span>PEAK SHEAR (G_max)</span>
              <span className="val-emerald">{telemetry.shear} s⁻¹</span>
            </div>
          </section>

          <section className="panel" style={{ alignSelf: 'flex-end', height: '180px' }}>
            <h2 className="panel-title">SYSTEM STATUS</h2>
            <div className="stat-row" style={{ color: 'var(--emerald)' }}>
               > ALL BIOPHYSICAL CONSTRAINTS NOMINAL
            </div>
            <div className="stat-row">
               > REACT 19 3D ENGINE ONLINE
            </div>
            <div className="stat-row">
               > GLSL INSTANCED PARTICLES: 100K
            </div>
          </section>
        </main>
      </div>

      <div className="crt-overlay"></div>
    </div>
  )
}
