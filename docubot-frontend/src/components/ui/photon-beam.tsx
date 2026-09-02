"use client"

import { useEffect, useRef } from "react"
import * as THREE from "three"
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js"
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js"
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js"

interface Signal {
  mesh: THREE.Line
  laneIndex: number
  speed: number
  progress: number
  history: THREE.Vector3[]
  assignedColor: THREE.Color
}

interface Params {
  colorBg: string
  colorLine: string
  colorSignal: string
  useColor2: boolean
  colorSignal2: string
  useColor3: boolean
  colorSignal3: string
  lineCount: number
  globalRotation: number
  positionX: number
  positionY: number
  spreadHeight: number
  spreadDepth: number
  curveLength: number
  straightLength: number
  curvePower: number
  waveSpeed: number
  waveHeight: number
  lineOpacity: number
  signalCount: number
  speedGlobal: number
  trailLength: number
  bloomStrength: number
  bloomRadius: number
}

interface PhotonBeamProps {
  colorBg?: string
  colorLine?: string
  colorSignal?: string
  useColor2?: boolean
  colorSignal2?: string
  useColor3?: boolean
  colorSignal3?: string
  lineCount?: number
  spreadHeight?: number
  spreadDepth?: number
  curveLength?: number
  straightLength?: number
  curvePower?: number
  waveSpeed?: number
  waveHeight?: number
  lineOpacity?: number
  signalCount?: number
  speedGlobal?: number
  trailLength?: number
  bloomStrength?: number
  bloomRadius?: number
}

const CONSTANTS = {
  segmentCount: 150,
}

export default function PhotonBeam(props: PhotonBeamProps = {}) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let frameId: number
    let cancelled = false
    let renderer: THREE.WebGLRenderer | null = null
    let composer: InstanceType<typeof EffectComposer> | null = null
    let handleResize: (() => void) | null = null
    let backgroundLines: THREE.Line[] = []
    let signals: Signal[] = []
    let observer: IntersectionObserver | null = null
    let stopLoopFn: (() => void) | null = null

    const init = (): void => {
      if (cancelled) return

      const width = container.clientWidth
      const height = container.clientHeight
      if (width === 0 || height === 0) {
        frameId = requestAnimationFrame(init)
        return
      }

      // --- CONFIGURATION ---
      const params: Params = {
        colorBg: props.colorBg ?? "#080808",
        colorLine: props.colorLine ?? "#005f6f",
        colorSignal: props.colorSignal ?? "#00d9ff",
        useColor2: props.useColor2 ?? false,
        colorSignal2: props.colorSignal2 ?? "#00ffff",
        useColor3: props.useColor3 ?? false,
        colorSignal3: props.colorSignal3 ?? "#00b8d4",
        lineCount: props.lineCount ?? 80,
        globalRotation: 0,
        positionX: 0,
        positionY: 0,
        spreadHeight: props.spreadHeight ?? 30.33,
        spreadDepth: props.spreadDepth ?? 0,
        curveLength: props.curveLength ?? 50,
        straightLength: props.straightLength ?? 100,
        curvePower: props.curvePower ?? 0.8265,
        waveSpeed: props.waveSpeed ?? 2.48,
        waveHeight: props.waveHeight ?? 0.145,
        lineOpacity: props.lineOpacity ?? 0.557,
        signalCount: props.signalCount ?? 94,
        speedGlobal: props.speedGlobal ?? 0.345,
        trailLength: props.trailLength ?? 3,
        bloomStrength: props.bloomStrength ?? 3.0,
        bloomRadius: props.bloomRadius ?? 0.5,
      }

      params.positionX = (params.curveLength - params.straightLength) / 2

      // --- SCENE SETUP ---
      const scene = new THREE.Scene()
      scene.background = params.colorBg === "transparent" ? null : new THREE.Color(params.colorBg)
      scene.fog = new THREE.FogExp2(params.colorBg === "transparent" ? "#000000" : params.colorBg, 0.002)

      const camera = new THREE.PerspectiveCamera(45, width / height, 1, 1000)
      camera.position.set(0, 0, 90)
      camera.lookAt(0, 0, 0)

      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: params.colorBg === "transparent" })
      if (params.colorBg === "transparent") {
        renderer.setClearColor(0x000000, 0)
      }
      renderer.setSize(width, height)
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
      container.appendChild(renderer.domElement)

      const contentGroup = new THREE.Group()
      contentGroup.position.set(params.positionX, params.positionY, 0)
      scene.add(contentGroup)

      // --- POST-PROCESSING ---
      const renderScene = new RenderPass(scene, camera)
      const bloomPass = new UnrealBloomPass(
        new THREE.Vector2(width, height),
        1.5,
        0.4,
        0.85
      )
      bloomPass.threshold = 0
      bloomPass.strength = params.bloomStrength
      bloomPass.radius = params.bloomRadius

      composer = new EffectComposer(renderer)
      composer.addPass(renderScene)
      if (params.colorBg !== "transparent") {
        composer.addPass(bloomPass)
      }

      // --- MATH & PATH CALCULATION ---
      const tempVec = new THREE.Vector3()
      const vectorPool: THREE.Vector3[] = []
      const getVector = (): THREE.Vector3 => {
        return vectorPool.pop() || new THREE.Vector3()
      }
      const releaseVector = (v: THREE.Vector3): void => {
        vectorPool.push(v)
      }

      function getPathPoint(
        t: number,
        lineIndex: number,
        time: number
      ): THREE.Vector3 {
        const totalLen = params.curveLength + params.straightLength
        const currentX = -params.curveLength + t * totalLen

        let y = 0
        let z = 0
        const spreadFactor = (lineIndex / params.lineCount - 0.5) * 2

        if (currentX < 0) {
          const ratio = (currentX + params.curveLength) / params.curveLength
          let shapeFactor = (Math.cos(ratio * Math.PI) + 1) / 2
          shapeFactor = Math.pow(shapeFactor, params.curvePower)

          y = spreadFactor * params.spreadHeight * shapeFactor
          z = spreadFactor * params.spreadDepth * shapeFactor

          const waveFactor = shapeFactor
          const wave =
            Math.sin(time * params.waveSpeed + currentX * 0.1 + lineIndex) *
            params.waveHeight *
            waveFactor
          y += wave
        }

        return new THREE.Vector3(currentX, y, z)
      }

      // --- OBJECTS MANAGEMENT ---
      backgroundLines = []
      signals = []

      const bgMaterial = new THREE.LineBasicMaterial({
        color: params.colorLine,
        transparent: true,
        opacity: params.lineOpacity,
        depthWrite: false,
      })

      const signalMaterial = new THREE.LineBasicMaterial({
        vertexColors: true,
        blending: params.colorBg === "transparent" ? THREE.NormalBlending : THREE.AdditiveBlending,
        depthWrite: false,
        depthTest: false,
        transparent: true,
      })

      const signalColorObj1 = new THREE.Color(params.colorSignal)
      const signalColorObj2 = new THREE.Color(params.colorSignal2)
      const signalColorObj3 = new THREE.Color(params.colorSignal3)

      function pickSignalColor(): THREE.Color {
        const choices: THREE.Color[] = [signalColorObj1]
        if (params.useColor2) choices.push(signalColorObj2)
        if (params.useColor3) choices.push(signalColorObj3)
        return choices[Math.floor(Math.random() * choices.length)]
      }

      function createSignal(): void {
        const maxTrail = 150
        const geometry = new THREE.BufferGeometry()
        const positions = new Float32Array(maxTrail * 3)
        const colors = new Float32Array(maxTrail * 3)

        geometry.setAttribute(
          "position",
          new THREE.BufferAttribute(positions, 3)
        )
        geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3))

        const mesh = new THREE.Line(geometry, signalMaterial)
        mesh.frustumCulled = false
        mesh.renderOrder = 1
        contentGroup.add(mesh)

        signals.push({
          mesh: mesh,
          laneIndex: Math.floor(Math.random() * params.lineCount),
          speed: 0.2 + Math.random() * 0.5,
          progress: Math.random(),
          history: [],
          assignedColor: pickSignalColor(),
        })
      }

      function rebuildSignals(): void {
        signals.forEach((s) => {
          contentGroup.remove(s.mesh)
          s.mesh.geometry.dispose()
          s.history.forEach(releaseVector)
        })
        signals = []
        for (let i = 0; i < params.signalCount; i++) {
          createSignal()
        }
      }

      function rebuildLines(): void {
        backgroundLines.forEach((l) => {
          contentGroup.remove(l)
          l.geometry.dispose()
        })
        backgroundLines = []

        for (let i = 0; i < params.lineCount; i++) {
          const geometry = new THREE.BufferGeometry()
          const positions = new Float32Array(CONSTANTS.segmentCount * 3)
          geometry.setAttribute(
            "position",
            new THREE.BufferAttribute(positions, 3)
          )

          const line = new THREE.Line(geometry, bgMaterial)
          line.userData = { id: i }
          line.renderOrder = 0
          contentGroup.add(line)
          backgroundLines.push(line)
        }
        rebuildSignals()
      }

      // Initial Build
      rebuildLines()

      // --- ANIMATION LOOP ---
      let startTime = 0
      let pausedTime = 0
      let lastPauseStart = 0
      let loopRunning = false

      const getElapsedTime = (): number => {
        if (!startTime) return 0
        return (performance.now() - startTime - pausedTime) * 0.001
      }

      function animate(): void {
        if (cancelled || !loopRunning) return
        frameId = requestAnimationFrame(animate)

        const time = getElapsedTime()

        // Update Lines
        backgroundLines.forEach((line) => {
          const positions = line.geometry.attributes.position
            .array as Float32Array
          const lineId = line.userData.id
          for (let j = 0; j < CONSTANTS.segmentCount; j++) {
            const t = j / (CONSTANTS.segmentCount - 1)
            const vec = getPathPoint(t, lineId, time)
            positions[j * 3] = vec.x
            positions[j * 3 + 1] = vec.y
            positions[j * 3 + 2] = vec.z
          }
          line.geometry.attributes.position.needsUpdate = true
        })

        // Update Signals
        signals.forEach((sig) => {
          sig.progress += sig.speed * 0.005 * params.speedGlobal

          if (sig.progress > 1.0) {
            sig.progress = 0
            sig.laneIndex = Math.floor(Math.random() * params.lineCount)
            sig.history.forEach(releaseVector)
            sig.history.length = 0
            sig.assignedColor = pickSignalColor()
          }

          const pos = getPathPoint(sig.progress, sig.laneIndex, time)
          const newV = getVector()
          newV.copy(pos)
          sig.history.push(newV)

          if (sig.history.length > params.trailLength + 1) {
            const removed = sig.history.shift()
            if (removed) releaseVector(removed)
          }

          const positions = sig.mesh.geometry.attributes.position
            .array as Float32Array
          const colors = sig.mesh.geometry.attributes.color
            .array as Float32Array

          const drawCount = Math.max(1, params.trailLength)
          const currentLen = sig.history.length

          for (let i = 0; i < drawCount; i++) {
            let index = currentLen - 1 - i
            if (index < 0) index = 0

            const p = sig.history[index] || tempVec

            positions[i * 3] = p.x
            positions[i * 3 + 1] = p.y
            positions[i * 3 + 2] = p.z

            let alpha = 1
            if (params.trailLength > 0) {
              alpha = Math.max(0, 1 - i / params.trailLength)
            }

            colors[i * 3] = sig.assignedColor.r * alpha
            colors[i * 3 + 1] = sig.assignedColor.g * alpha
            colors[i * 3 + 2] = sig.assignedColor.b * alpha
          }

          sig.mesh.geometry.setDrawRange(0, drawCount)
          sig.mesh.geometry.attributes.position.needsUpdate = true
          sig.mesh.geometry.attributes.color.needsUpdate = true
        })

        if (composer) composer.render()
      }

      // Resize Handler
      handleResize = (): void => {
        if (!container || cancelled || !renderer || !composer) return
        const w = container.clientWidth
        const h = container.clientHeight
        if (w === 0 || h === 0) return

        camera.aspect = w / h
        camera.updateProjectionMatrix()
        renderer.setSize(w, h)
        composer.setSize(w, h)
      }

      window.addEventListener("resize", handleResize)

      const startLoop = (): void => {
        if (loopRunning || cancelled) return
        loopRunning = true
        if (!startTime) {
          startTime = performance.now()
        } else if (lastPauseStart) {
          pausedTime += performance.now() - lastPauseStart
          lastPauseStart = 0
        }
        animate()
      }

      const stopLoop = (): void => {
        if (!loopRunning) return
        loopRunning = false
        lastPauseStart = performance.now()
        if (frameId) cancelAnimationFrame(frameId)
      }

      stopLoopFn = stopLoop

      observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            startLoop()
          } else {
            stopLoop()
          }
        },
        { threshold: 0.01 }
      )
      observer.observe(container)
    }

    frameId = requestAnimationFrame(init)

    return () => {
      cancelled = true
      if (stopLoopFn) stopLoopFn()
      if (observer) {
        observer.disconnect()
      }
      cancelAnimationFrame(frameId)
      if (handleResize) {
        window.removeEventListener("resize", handleResize)
      }
      if (container && renderer?.domElement) {
        try {
          container.removeChild(renderer.domElement)
        } catch {
          /* element may already be removed */
        }
        renderer.dispose()
      }
      composer?.dispose()
      backgroundLines.forEach((l) => l.geometry.dispose())
      signals.forEach((s) => s.mesh.geometry.dispose())
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div ref={containerRef} className={`h-full min-h-[200px] w-full ${props.colorBg === "transparent" ? "bg-transparent" : "bg-black"}`} />
  )
}

