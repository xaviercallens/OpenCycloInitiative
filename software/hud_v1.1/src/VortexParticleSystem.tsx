import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface VortexProps {
    particleCount?: number
    radius?: number
    height?: number
    rpm?: number
}

const vertexShader = `
uniform float time;
uniform float rpm;
attribute float size;
attribute float phase;
varying vec3 vColor;

void main() {
  // Rankine vortex math: inner core (rigid body), outer region (free vortex)
  float r = length(position.xz);
  float coreRadius = 2.0;

  // Angular velocity depending on radius
  float omega = r < coreRadius ? (rpm / 60.0) : (rpm / 60.0) * pow(coreRadius / r, 1.5);
  float angle = omega * time * 2.0 * 3.14159 + phase;

  vec3 pos = position;
  pos.x = r * cos(angle);
  pos.z = r * sin(angle);

  // Vertical spiraling
  pos.y += sin(time * 0.5 + phase) * 0.2;

  // Pass color based on distance and height
  float normalizedHeight = (pos.y + 5.0) / 10.0;
  vec3 cyan = vec3(0.0, 0.898, 1.0);
  vec3 emerald = vec3(0.0, 1.0, 0.4);
  vColor = mix(cyan, emerald, normalizedHeight);
  
  // Fade out edges
  float alpha = clamp(1.0 - r / 10.0, 0.0, 1.0);
  
  vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
  gl_Position = projectionMatrix * mvPosition;
  
  // Size attenuation
  gl_PointSize = size * (300.0 / -mvPosition.z) * alpha;
}
`

const fragmentShader = `
varying vec3 vColor;
void main() {
  vec2 xy = gl_PointCoord.xy - vec2(0.5);
  float ll = length(xy);
  if (ll > 0.5) discard;
  
  // Glow effect
  float alpha = (0.5 - ll) * 2.0;
  gl_FragColor = vec4(vColor * 1.5, alpha * 0.4);
}
`

export function VortexParticleSystem({ particleCount = 100000, radius = 5, height = 10, rpm = 3400 }: VortexProps) {
    const pointsRef = useRef<THREE.Points>(null!)
    const materialRef = useRef<THREE.ShaderMaterial>(null!)

    const particles = useMemo(() => {
        const geometry = new THREE.BufferGeometry()
        const positions = new Float32Array(particleCount * 3)
        const sizes = new Float32Array(particleCount)
        const phases = new Float32Array(particleCount)

        for (let i = 0; i < particleCount; i++) {
            // distribute mostly near the center but sprawling out
            const r = Math.pow(Math.random(), 2) * radius * 1.5
            const theta = Math.random() * 2 * Math.PI
            const y = (Math.random() - 0.5) * height

            positions[i * 3] = r * Math.cos(theta)
            positions[i * 3 + 1] = y
            positions[i * 3 + 2] = r * Math.sin(theta)

            sizes[i] = Math.random() * 2.0 + 0.5
            phases[i] = Math.random() * Math.PI * 2
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
        geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1))
        geometry.setAttribute('phase', new THREE.BufferAttribute(phases, 1))
        return geometry
    }, [particleCount, radius, height])

    const uniforms = useMemo(() => ({
        time: { value: 0 },
        rpm: { value: rpm }
    }), [])

    useFrame((state) => {
        if (materialRef.current) {
            materialRef.current.uniforms.time.value = state.clock.getElapsedTime()
            // Optional: tie rpm to live data or props
            materialRef.current.uniforms.rpm.value = rpm
        }
        if (pointsRef.current) {
            // Slow tilt to show 3D nature
            pointsRef.current.rotation.y = state.clock.getElapsedTime() * 0.05
        }
    })

    return (
        <points ref={pointsRef} geometry={particles}>
            <shaderMaterial
                ref={materialRef}
                vertexShader={vertexShader}
                fragmentShader={fragmentShader}
                uniforms={uniforms}
                transparent={true}
                depthWrite={false}
                blending={THREE.AdditiveBlending}
            />
        </points>
    )
}
