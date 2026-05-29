import { useRef, useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { useCadenceStore } from '../store'
import { getAnalyser } from '../audio/player'

// ── Paleta por sección ────────────────────────────────────────
const SECTION_COLORS = {
  intro:      { primary: 0x7c3aed, secondary: 0x4c1d95 },
  'build-up': { primary: 0xff4d6d, secondary: 0x7c3aed },
  verse:      { primary: 0x06d6a0, secondary: 0x0a9e77 },
  chorus:     { primary: 0xffd166, secondary: 0xff4d6d },
  drop:       { primary: 0xff4d6d, secondary: 0xff0040 },
  breakdown:  { primary: 0x2a2a3f, secondary: 0x11111a },
  bridge:     { primary: 0x06d6a0, secondary: 0x7c3aed },
  climax:     { primary: 0xff4d6d, secondary: 0xffd166 },
  'pre-chorus': { primary: 0xffd166, secondary: 0xff4d6d },
  outro:      { primary: 0x7c3aed, secondary: 0x2a2a3f },
}

const DEFAULT_COLORS = { primary: 0x7c3aed, secondary: 0x4c1d95 }

function hexToVec3(hex) {
  const r = ((hex >> 16) & 255) / 255
  const g = ((hex >> 8)  & 255) / 255
  const b = (hex & 255)         / 255
  return new THREE.Vector3(r, g, b)
}

// ── Geometría de barras (una por bin de frecuencia) ───────────
const BAR_COUNT  = 48
const BAR_WIDTH  = 0.18
const BAR_GAP    = 0.10
const BAR_MAX_H  = 6.0
const TOTAL_W    = BAR_COUNT * (BAR_WIDTH + BAR_GAP)

export default function Visualizer() {
  const mountRef = useRef(null)
  const stateRef = useRef({
    bars: [],
    particles: null,
    particlePositions: null,
    gridLines: [],
    beatRing: null,
    beatRingScale: 1,
    currentColors: { ...DEFAULT_COLORS },
    targetColors:  { ...DEFAULT_COLORS },
    lastSection: null,
    frameId: null,
  })

  const { isPlaying, activeSection, currentTimeMs, rsong } =
    useCadenceStore()

  // Detectar beats del track de drums para el ring flash
  const beatTimestamps = useMemo(() => {
    if (!rsong) return []
    const drums = rsong.tracks.find(t => t.id === 'drums')
    if (!drums) return []
    return drums.events
      .filter(e => e.pitch === 36)   // solo kick
      .map(e => e.t)
  }, [rsong])

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return

    // ── Renderer ──────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(mount.clientWidth, mount.clientHeight)
    renderer.setClearColor(0x0a0a0f, 1)
    mount.appendChild(renderer.domElement)

    // ── Scene & Camera ────────────────────────────────────────
    const scene  = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(
      55, mount.clientWidth / mount.clientHeight, 0.1, 200
    )
    camera.position.set(0, 3, 14)
    camera.lookAt(0, 1, 0)

    // ── Fog ───────────────────────────────────────────────────
    scene.fog = new THREE.FogExp2(0x0a0a0f, 0.045)

    // ── Barras de frecuencia ──────────────────────────────────
    const bars = []
    for (let i = 0; i < BAR_COUNT; i++) {
      const geo  = new THREE.BoxGeometry(BAR_WIDTH, 1, BAR_WIDTH)
      const mat  = new THREE.MeshBasicMaterial({ color: 0x7c3aed })
      const mesh = new THREE.Mesh(geo, mat)
      const x    = -TOTAL_W / 2 + i * (BAR_WIDTH + BAR_GAP) + BAR_WIDTH / 2
      mesh.position.set(x, 0, 0)
      scene.add(mesh)
      bars.push(mesh)
    }
    stateRef.current.bars = bars

    // ── Grid synthwave ────────────────────────────────────────
    const gridGroup = new THREE.Group()
    const gridMat   = new THREE.LineBasicMaterial({
      color: 0x2a2a3f, transparent: true, opacity: 0.6
    })
    // Líneas horizontales
    for (let z = 0; z >= -60; z -= 3) {
      const geo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-20, -0.5, z),
        new THREE.Vector3( 20, -0.5, z),
      ])
      gridGroup.add(new THREE.Line(geo, gridMat))
    }
    // Líneas verticales
    for (let x = -20; x <= 20; x += 3) {
      const geo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(x, -0.5,   0),
        new THREE.Vector3(x, -0.5, -60),
      ])
      gridGroup.add(new THREE.Line(geo, gridMat))
    }
    scene.add(gridGroup)
    stateRef.current.gridLines = gridGroup

    // ── Beat ring (flash en cada kick) ────────────────────────
    const ringGeo  = new THREE.RingGeometry(3.5, 3.7, 64)
    const ringMat  = new THREE.MeshBasicMaterial({
      color: 0xff4d6d, side: THREE.DoubleSide,
      transparent: true, opacity: 0,
    })
    const ring = new THREE.Mesh(ringGeo, ringMat)
    ring.rotation.x = -Math.PI / 2
    ring.position.y = -0.4
    scene.add(ring)
    stateRef.current.beatRing = ring

    // ── Partículas flotantes ──────────────────────────────────
    const pCount = 200
    const pPos   = new Float32Array(pCount * 3)
    const pVel   = new Float32Array(pCount * 3)
    for (let i = 0; i < pCount; i++) {
      pPos[i * 3]     = (Math.random() - 0.5) * 30
      pPos[i * 3 + 1] = Math.random() * 8
      pPos[i * 3 + 2] = (Math.random() - 0.5) * 20
      pVel[i * 3]     = (Math.random() - 0.5) * 0.008
      pVel[i * 3 + 1] = Math.random() * 0.006 + 0.002
      pVel[i * 3 + 2] = (Math.random() - 0.5) * 0.005
    }
    const pGeo = new THREE.BufferGeometry()
    pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3))
    const pMat = new THREE.PointsMaterial({
      color: 0x7c3aed, size: 0.06, transparent: true, opacity: 0.7
    })
    const particles = new THREE.Points(pGeo, pMat)
    scene.add(particles)
    stateRef.current.particles         = particles
    stateRef.current.particlePositions = pPos
    stateRef.current.particleVelocities = pVel

    // ── Resize ────────────────────────────────────────────────
    function onResize() {
      if (!mount) return
      camera.aspect = mount.clientWidth / mount.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(mount.clientWidth, mount.clientHeight)
    }
    window.addEventListener('resize', onResize)

    // ── Animate ───────────────────────────────────────────────
    let gridOffset = 0

    function animate() {
      stateRef.current.frameId = requestAnimationFrame(animate)
      const s = stateRef.current
      const time = performance.now() / 1000

      // Interpolar colores de sección
      const lerp = (a, b, t) => a + (b - a) * t
      s.currentColors.primary = Math.round(lerp(
        s.currentColors.primary, s.targetColors.primary, 0.04
      ))
      s.currentColors.secondary = Math.round(lerp(
        s.currentColors.secondary, s.targetColors.secondary, 0.04
      ))

      // FFT data
      const analyser = getAnalyser()
      let fftData = null
      if (analyser) {
        fftData = analyser.getValue()
      }

      // Actualizar barras
      for (let i = 0; i < BAR_COUNT; i++) {
        const bar = bars[i]
        let targetH

        if (fftData && useCadenceStore.getState().isPlaying) {
          // Mapear bins FFT a barras (escala logarítmica)
          const binIndex = Math.floor(
            Math.pow(i / BAR_COUNT, 1.5) * (fftData.length / 2)
          )
          const db = Math.max(-80, fftData[binIndex] ?? -80)
          targetH  = Math.max(0.05, ((db + 80) / 80) * BAR_MAX_H)
        } else {
          // Idle animation: onda sinusoidal suave
          targetH = 0.05 + Math.abs(Math.sin(time * 0.8 + i * 0.25)) * 0.4
        }

        // Smooth scaling
        bar.scale.y += (targetH - bar.scale.y) * 0.18
        bar.position.y = bar.scale.y / 2

        // Color
        const intensity = bar.scale.y / BAR_MAX_H
        const col = new THREE.Color(
          intensity > 0.6 ? s.currentColors.secondary : s.currentColors.primary
        )
        bar.material.color.lerp(col, 0.12)
      }

      // Grid scroll
      gridOffset = (gridOffset + 0.035) % 3
      gridGroup.position.z = gridOffset

      // Beat ring decay
      if (ring.material.opacity > 0) {
        ring.material.opacity *= 0.88
        ring.scale.x += 0.03
        ring.scale.y += 0.03
      }

      // Partículas
      const pPos = s.particlePositions
      const pVel = s.particleVelocities
      for (let i = 0; i < pCount; i++) {
        pPos[i * 3]     += pVel[i * 3]
        pPos[i * 3 + 1] += pVel[i * 3 + 1]
        pPos[i * 3 + 2] += pVel[i * 3 + 2]
        // Reset si salen del área
        if (pPos[i * 3 + 1] > 10) {
          pPos[i * 3 + 1] = -0.5
          pPos[i * 3]     = (Math.random() - 0.5) * 30
        }
      }
      particles.geometry.attributes.position.needsUpdate = true
      particles.material.color.set(s.currentColors.primary)

      // Cámara: ligero movimiento orgánico
      camera.position.x = Math.sin(time * 0.12) * 1.5
      camera.position.y = 3 + Math.sin(time * 0.07) * 0.4
      camera.lookAt(0, 1, 0)

      renderer.render(scene, camera)
    }

    animate()

    return () => {
      cancelAnimationFrame(stateRef.current.frameId)
      window.removeEventListener('resize', onResize)
      renderer.dispose()
      if (mount.contains(renderer.domElement)) {
        mount.removeChild(renderer.domElement)
      }
    }
  }, [])   // mount una sola vez

  // ── Reaccionar a cambios de sección ──────────────────────────
  useEffect(() => {
    if (!activeSection) return
    const colors = SECTION_COLORS[activeSection] ?? DEFAULT_COLORS
    stateRef.current.targetColors = { ...colors }
  }, [activeSection])

  // ── Flash en cada kick ────────────────────────────────────────
  useEffect(() => {
    if (!isPlaying) return
    const ring = stateRef.current.beatRing
    if (!ring) return

    // Buscar el kick más cercano al tiempo actual
    const tolerance = 80  // ms
    const isKick = beatTimestamps.some(
      t => Math.abs(t - currentTimeMs) < tolerance
    )
    if (isKick) {
      ring.material.opacity = 0.7
      ring.scale.set(1, 1, 1)
    }
  }, [currentTimeMs, isPlaying, beatTimestamps])

  return (
    <div
      ref={mountRef}
      style={{ width: '100%', height: '100%', position: 'absolute',
               inset: 0, zIndex: 0 }}
    />
  )
}
