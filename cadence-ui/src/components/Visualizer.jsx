import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { LineSegments2 } from 'three/examples/jsm/lines/LineSegments2.js'
import { LineSegmentsGeometry } from 'three/examples/jsm/lines/LineSegmentsGeometry.js'
import { LineMaterial } from 'three/examples/jsm/lines/LineMaterial.js'
import { useCadenceStore } from '../store'
import { getAnalyser } from '../audio/player'

const SECTION_COLORS = {
  intro: 0x7c3aed,
  verse: 0x06d6a0,
  chorus: 0xffd166,
  drop: 0xff4d6d,
  bridge: 0x3aa0ff,
  climax: 0xff4d6d,
  outro: 0x7c3aed,
}

export default function Visualizer() {
  const mountRef = useRef(null)
  const stateRef = useRef({})
  const { rsong, activeSection, currentTimeMs, isPlaying } = useCadenceStore()

  const kickTimes = useMemo(() => {
    const drums = rsong?.tracks?.find((t) => (t.instrument_id || t.id) === 'drums')
    if (!drums) return []
    return drums.events
      .filter((e) => e.type !== 'rest' && (e.pitch === 36 || e.pitch === 35))
      .map((e) => e.t)
  }, [rsong])

  useEffect(() => {
    const mount = mountRef.current
    const shared = stateRef.current
    if (!mount) return

    const centerY = 2.15

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(mount.clientWidth, mount.clientHeight)
    renderer.setClearColor(0x06070d, 1)
    mount.appendChild(renderer.domElement)

    const scene = new THREE.Scene()
    scene.fog = new THREE.FogExp2(0x06070d, 0.038)
    const camera = new THREE.PerspectiveCamera(50, mount.clientWidth / mount.clientHeight, 0.1, 120)
    camera.position.set(0, 5.7, 14)
    camera.lookAt(0, centerY, 0)

    const hemi = new THREE.HemisphereLight(0x7c3aed, 0x06070d, 1.1)
    scene.add(hemi)
    const point = new THREE.PointLight(0xff4d6d, 4, 40)
    point.position.set(0, 6, 4)
    scene.add(point)

    const icoGeometry = new THREE.IcosahedronGeometry(2.4, 0)
    const ico = new THREE.Mesh(
      icoGeometry,
      new THREE.MeshPhysicalMaterial({
        color: 0x7c3aed,
        transparent: true,
        opacity: 0.35,
        roughness: 0.18,
        metalness: 0.2,
        transmission: 0.5,
        thickness: 0.6,
        flatShading: true,
        depthWrite: true,
      })
    )
    ico.position.y = centerY
    scene.add(ico)

    const edgesGeometry = new THREE.EdgesGeometry(icoGeometry, 1)
    const fatEdgesGeometry = new LineSegmentsGeometry()
    fatEdgesGeometry.setPositions(edgesGeometry.attributes.position.array)
    const fatEdgesMaterial = new LineMaterial({
      color: 0xffffff,
      linewidth: 3.2,
      transparent: true,
      opacity: 0.95,
      depthTest: true,
      depthWrite: false,
      worldUnits: false,
    })
    fatEdgesMaterial.resolution.set(mount.clientWidth, mount.clientHeight)
    const icoEdges = new LineSegments2(fatEdgesGeometry, fatEdgesMaterial)
    ico.add(icoEdges)

    const coreSphere = new THREE.Mesh(
      new THREE.SphereGeometry(1.12, 32, 32),
      new THREE.MeshStandardMaterial({
        color: 0x06d6a0,
        emissive: 0x06d6a0,
        emissiveIntensity: 0.5,
        roughness: 0.3,
        metalness: 0.2,
      })
    )
    coreSphere.position.y = centerY
    scene.add(coreSphere)

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(30, 30, 60, 60),
      new THREE.MeshStandardMaterial({
        color: 0x0f1320,
        wireframe: true,
        transparent: true,
        opacity: 0.28,
      })
    )
    floor.rotation.x = -Math.PI / 2
    floor.position.y = centerY - 4.2
    scene.add(floor)

    const ripplePool = Array.from({ length: 8 }, () => {
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(0.6, 0.75, 48),
        new THREE.MeshBasicMaterial({
          color: 0xff4d6d,
          transparent: true,
          opacity: 0,
          side: THREE.DoubleSide,
        })
      )
      ring.rotation.x = -Math.PI / 2
      ring.position.y = centerY - 4.15
      scene.add(ring)
      return { mesh: ring, active: false, life: 0 }
    })

    const starGeo = new THREE.BufferGeometry()
    const starCount = 420
    const starPos = new Float32Array(starCount * 3)
    const starDrift = new Float32Array(starCount * 3)
    for (let i = 0; i < starCount; i++) {
      starPos[i * 3] = (Math.random() - 0.5) * 34
      starPos[i * 3 + 1] = Math.random() * 14
      starPos[i * 3 + 2] = (Math.random() - 0.5) * 34
      starDrift[i * 3] = Math.random() * 6.28
      starDrift[i * 3 + 1] = Math.random() * 6.28
      starDrift[i * 3 + 2] = Math.random() * 6.28
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3))
    const starBase = starPos.slice()
    const stars = new THREE.Points(
      starGeo,
      new THREE.PointsMaterial({
        size: 0.075,
        color: 0x7c3aed,
        transparent: true,
        opacity: 0.7,
      })
    )
    scene.add(stars)

    function onResize() {
      if (!mount) return
      camera.aspect = mount.clientWidth / mount.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(mount.clientWidth, mount.clientHeight)
      fatEdgesMaterial.resolution.set(mount.clientWidth, mount.clientHeight)
    }
    window.addEventListener('resize', onResize)

    const clock = new THREE.Clock()
    const floorPositions = floor.geometry.attributes.position
    const basePositions = floorPositions.array.slice()
    let smoothBounceEnergy = 0.12
    let smoothPulse = 0
    let smoothSphereScale = 1
    let smoothSphereYOffset = 0
    let smoothEmissive = 0.7

    function spawnRipple() {
      const slot = ripplePool.find((r) => !r.active)
      if (!slot) return
      slot.active = true
      slot.life = 0
      slot.mesh.scale.set(1, 1, 1)
      slot.mesh.material.opacity = 0.45
    }

    function animate() {
      stateRef.current.frame = requestAnimationFrame(animate)
      const time = clock.getElapsedTime()
      const analyser = getAnalyser()
      const fft = analyser ? analyser.getValue() : null
      const playing = useCadenceStore.getState().isPlaying

      let bassEnergy = 0.12
      let highEnergy = 0.1
      let midEnergy = 0.1
      if (fft && playing) {
        const bassBins = fft.slice(2, 18)
        const midBins = fft.slice(18, 40)
        const highBins = fft.slice(35, 120)
        bassEnergy = Math.max(0, Math.min(1, bassBins.reduce((s, v) => s + (v + 90), 0) / (bassBins.length * 90)))
        midEnergy = Math.max(0, Math.min(1, midBins.reduce((s, v) => s + (v + 90), 0) / (midBins.length * 90)))
        highEnergy = Math.max(0, Math.min(1, highBins.reduce((s, v) => s + (v + 90), 0) / (highBins.length * 90)))
      }

      const sectionColor = new THREE.Color(
        SECTION_COLORS[useCadenceStore.getState().activeSection] || 0x7c3aed
      )
      const energy = (bassEnergy * 0.5) + (midEnergy * 0.3) + (highEnergy * 0.2)
      const hueShift = Math.sin(time * (0.8 + midEnergy * 1.2) + energy * 4.5) * 0.08
      const dynamicColor = sectionColor.clone()
      const hsl = {}
      dynamicColor.getHSL(hsl)
      dynamicColor.setHSL(
        (hsl.h + hueShift + 1) % 1,
        Math.min(1, hsl.s + highEnergy * 0.2),
        Math.min(0.7, hsl.l + energy * 0.12)
      )

      ico.material.color.lerp(dynamicColor, 0.16)
      icoEdges.material.color.lerp(dynamicColor.clone().offsetHSL(0.03, 0.18, 0.2), 0.2)
      icoEdges.material.opacity = 0.56 + energy * 0.36
      coreSphere.material.emissive.lerp(dynamicColor, 0.12)
      stars.material.color.lerp(dynamicColor, 0.09)
      floor.material.color.lerp(dynamicColor.clone().offsetHSL(0, -0.18, -0.34), 0.09)
      point.color.lerp(dynamicColor, 0.12)

      ico.rotation.x += 0.01 + highEnergy * 0.018
      ico.rotation.y += 0.014 + bassEnergy * 0.024
      ico.rotation.z += 0.004 + midEnergy * 0.012
      ico.scale.setScalar(1 + bassEnergy * 0.22)

      const bpm = useCadenceStore.getState().rsong?.header?.bpm || 120
      const bpmNorm = THREE.MathUtils.clamp(bpm / 120, 0.65, 1.9)
      const speedFactor = 0.9 * Math.pow(bpmNorm, 1.25)
      const ampFactor = 0.85 + (bpmNorm - 0.65) * 0.45
      const bpmPhase = time * speedFactor
      const starPosArray = stars.geometry.attributes.position.array
      for (let i = 0; i < starCount; i++) {
        const ix = i * 3
        const baseX = starBase[ix]
        const baseY = starBase[ix + 1]
        const baseZ = starBase[ix + 2]
        const phaseX = starDrift[ix]
        const phaseY = starDrift[ix + 1]
        const phaseZ = starDrift[ix + 2]

        // Particle drift depends only on BPM (no FFT energy coupling).
        starPosArray[ix] = baseX + Math.sin(bpmPhase + phaseX) * (0.24 * ampFactor)
        starPosArray[ix + 1] = baseY + Math.cos(bpmPhase + phaseY) * (0.13 * ampFactor)
        starPosArray[ix + 2] = baseZ + Math.sin(bpmPhase + phaseZ) * (0.2 * ampFactor)
      }
      stars.geometry.attributes.position.needsUpdate = true

      const bounceEnergy = Math.min(1, bassEnergy * 0.62 + midEnergy * 0.52 + highEnergy * 0.3)
      const pulse = Math.abs(Math.sin(time * (5.8 + bounceEnergy * 5.2)))
      smoothBounceEnergy = THREE.MathUtils.lerp(smoothBounceEnergy, bounceEnergy, 0.12)
      smoothPulse = THREE.MathUtils.lerp(smoothPulse, pulse, 0.1)

      const targetScale = 0.76 + smoothBounceEnergy * 0.9 + smoothPulse * 0.22
      const targetYOffset = smoothBounceEnergy * 0.34 + smoothPulse * 0.1
      const targetEmissive = 0.44 + highEnergy * 1.0 + smoothPulse * 0.25

      smoothSphereScale = THREE.MathUtils.lerp(smoothSphereScale, targetScale, 0.18)
      smoothSphereYOffset = THREE.MathUtils.lerp(smoothSphereYOffset, targetYOffset, 0.16)
      smoothEmissive = THREE.MathUtils.lerp(smoothEmissive, targetEmissive, 0.14)

      coreSphere.scale.setScalar(smoothSphereScale)
      coreSphere.position.y = centerY + smoothSphereYOffset
      coreSphere.material.emissiveIntensity = smoothEmissive

      for (let i = 0; i < floorPositions.count; i++) {
        const ix = i * 3
        const x = basePositions[ix]
        const z = basePositions[ix + 2]
        floorPositions.array[ix + 1] =
          Math.sin((x + time * 2.7) * 0.45) * 0.08 * (0.3 + bassEnergy) +
          Math.cos((z + time * 2.2) * 0.5) * 0.07 * (0.3 + highEnergy)
      }
      floorPositions.needsUpdate = true

      for (const ripple of ripplePool) {
        if (!ripple.active) continue
        ripple.mesh.material.color.lerp(dynamicColor, 0.2)
        ripple.life += 0.03
        ripple.mesh.scale.setScalar(1 + ripple.life * 3.3)
        ripple.mesh.material.opacity = Math.max(0, 0.45 - ripple.life * 0.45)
        if (ripple.life >= 1) {
          ripple.active = false
          ripple.mesh.material.opacity = 0
        }
      }

      camera.position.x = Math.sin(time * 0.22) * 1.8
      camera.position.y = 5.7 + Math.cos(time * 0.16) * 0.32
      camera.lookAt(0, centerY, 0)

      renderer.render(scene, camera)
    }

    shared.spawnRipple = spawnRipple
    animate()

    return () => {
      cancelAnimationFrame(shared.frame)
      window.removeEventListener('resize', onResize)
      renderer.dispose()
      if (mount.contains(renderer.domElement)) {
        mount.removeChild(renderer.domElement)
      }
    }
  }, [])

  useEffect(() => {
    if (!isPlaying) return
    const tolerance = 80
    const isKick = kickTimes.some((t) => Math.abs(t - currentTimeMs) <= tolerance)
    if (isKick && stateRef.current.spawnRipple) {
      stateRef.current.spawnRipple()
    }
  }, [currentTimeMs, isPlaying, kickTimes])

  useEffect(() => {
    stateRef.current.section = activeSection
  }, [activeSection])

  return <div ref={mountRef} className="visualizer-mount" />
}
