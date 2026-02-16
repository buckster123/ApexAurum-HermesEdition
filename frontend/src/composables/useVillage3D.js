/**
 * useVillage3D - Perspective 3D Village Scene
 *
 * Full 3D perspective view of the Village with zone buildings, agent avatars,
 * particle effects, speech bubbles, and dive-in camera. Progressive enhancement
 * loads GLB models over primitive fallbacks.
 *
 * Uses PerspectiveCamera + OrbitControls (unlike useVillageIsometric which
 * uses OrthographicCamera). Agents walk between zones when tools execute,
 * with particle bursts on completion and canvas-texture speech bubbles.
 *
 * "The Village rendered in full perspective — where agents stride between
 * buildings and the camera follows the action"
 */

import { ref, shallowRef } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { useAgentModels } from '@/composables/useAgentModels'
import { useVillageModels } from '@/composables/useVillageModels'
import { useDraggableZones } from '@/composables/useDraggableZones'
import { useDistrictManager } from '@/composables/useDistrictManager'
import { useVillagePostProcessing } from '@/composables/useVillagePostProcessing'
import { useFPVMode } from '@/composables/useFPVMode'
import { useFPVInteraction } from '@/composables/useFPVInteraction'
import { useVillageDayNight } from '@/composables/useVillageDayNight'
import { useAgentAutonomy } from '@/composables/useAgentAutonomy'

// Polyfill for roundRect (not available in all browsers)
if (typeof CanvasRenderingContext2D !== 'undefined' && !CanvasRenderingContext2D.prototype.roundRect) {
  CanvasRenderingContext2D.prototype.roundRect = function (x, y, w, h, r) {
    if (w < 2 * r) r = w / 2
    if (h < 2 * r) r = h / 2
    this.moveTo(x + r, y)
    this.arcTo(x + w, y, x + w, y + h, r)
    this.arcTo(x + w, y + h, x, y + h, r)
    this.arcTo(x, y + h, x, y, r)
    this.arcTo(x, y, x + w, y, r)
    this.closePath()
    return this
  }
}

// =============================================================================
// CONSTANTS
// =============================================================================

export const AGENT_COLORS = {
  AZOTH: '#FFD700',
  VAJRA: '#4FC3F7',
  ELYSIAN: '#ff69b4',
  KETHER: '#9370db',
  default: '#888888',
}

export const VILLAGE_LAYOUT = {
  village_square: { pos: [0, 0, 0], label: 'Village Square', color: '#2d3436', modelId: 'market' },
  dj_booth: { pos: [-12, 0, -5], label: 'DJ Booth', color: '#6c5ce7', modelId: 'tavern' },
  memory_garden: { pos: [5, 0, -14], label: 'Memory Garden', color: '#00b894', modelId: 'garden' },
  file_shed: { pos: [14, 0, -3], label: 'File Shed', color: '#fdcb6e', modelId: 'library' },
  workshop: { pos: [1, 0, 14], label: 'Workshop', color: '#e17055', modelId: 'workshop' },
  bridge_portal: { pos: [13, 0, -12], label: 'Bridge Portal', color: '#a29bfe', modelId: 'temple' },
  library: { pos: [-14, 0, -11], label: 'Library', color: '#74b9ff', modelId: 'observatory' },
  watchtower: { pos: [-11, 0, 12], label: 'Watchtower', color: '#fd79a8', modelId: 'forge' },
  // --- Outer Ring Zones (Phase 1A) ---
  arena: { pos: [-24, 0, 0], label: 'Arena', color: '#d63031', modelId: 'arena' },
  bazaar: { pos: [24, 0, 0], label: 'Grand Bazaar', color: '#e8a838', modelId: 'bazaar' },
  apothecary: { pos: [0, 0, -24], label: 'Apothecary', color: '#00cec9', modelId: 'apothecary' },
  nexus_tower: { pos: [0, 0, 24], label: 'Nexus Tower', color: '#6c5ce7', modelId: 'nexus_tower' },
  mines: { pos: [-20, 0, -20], label: 'Crystal Mines', color: '#b2bec3', modelId: 'mines' },
  sanctum: { pos: [20, 0, 20], label: 'Inner Sanctum', color: '#ffeaa7', modelId: 'sanctum' },
}

const AGENT_IDS = ['AZOTH', 'VAJRA', 'ELYSIAN', 'KETHER']

const ORBIT_POSITION = new THREE.Vector3(35, 25, 35)
const ORBIT_TARGET = new THREE.Vector3(0, 0, 0)

// Mobile detection — skip shadows, reduce effects
const isMobile =
  /Android|iPhone|iPad/i.test(navigator.userAgent) ||
  (navigator.maxTouchPoints > 0 && !window.matchMedia?.('(pointer: fine)')?.matches)

// =============================================================================
// PARTICLE SYSTEM
// =============================================================================

class ParticleSystem {
  constructor(scene) {
    this.scene = scene
    this.bursts = []
  }

  emit(position, colorHex, count = 20) {
    const particles = []
    const group = new THREE.Group()

    const color = new THREE.Color(colorHex)
    const geometry = new THREE.SphereGeometry(0.1, 6, 6)

    for (let i = 0; i < count; i++) {
      const material = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 1,
      })
      const mesh = new THREE.Mesh(geometry, material)
      mesh.position.copy(position)

      // Random burst velocity
      const theta = Math.random() * Math.PI * 2
      const phi = Math.random() * Math.PI * 0.8
      const speed = 2 + Math.random() * 4
      const velocity = new THREE.Vector3(
        Math.cos(theta) * Math.sin(phi) * speed,
        Math.abs(Math.cos(phi)) * speed + 2,
        Math.sin(theta) * Math.sin(phi) * speed,
      )

      group.add(mesh)
      particles.push({ mesh, velocity, age: 0 })
    }

    this.scene.add(group)
    this.bursts.push({ group, particles, age: 0, maxAge: 1.5, geometry })
  }

  rain(position, colorHex, count = 60) {
    const particles = []
    const group = new THREE.Group()
    const color = new THREE.Color(colorHex)
    const geometry = new THREE.SphereGeometry(0.08, 6, 6)

    for (let i = 0; i < count; i++) {
      const material = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 1,
      })
      const mesh = new THREE.Mesh(geometry, material)

      // Scatter above position at varying heights for staggered fall
      mesh.position.set(
        position.x + (Math.random() - 0.5) * 5,
        position.y + Math.random() * 6,
        position.z + (Math.random() - 0.5) * 5,
      )

      // Gentle downward drift + slight lateral wander
      const velocity = new THREE.Vector3(
        (Math.random() - 0.5) * 0.8,
        -(0.5 + Math.random() * 1.5),
        (Math.random() - 0.5) * 0.8,
      )

      group.add(mesh)
      particles.push({ mesh, velocity, age: 0 })
    }

    this.scene.add(group)
    this.bursts.push({ group, particles, age: 0, maxAge: 3.5, geometry })
  }

  update(dt) {
    for (let i = this.bursts.length - 1; i >= 0; i--) {
      const burst = this.bursts[i]
      burst.age += dt

      if (burst.age >= burst.maxAge) {
        this._disposeBurst(burst)
        this.bursts.splice(i, 1)
        continue
      }

      const progress = burst.age / burst.maxAge

      for (const p of burst.particles) {
        p.age += dt
        // Apply velocity with gravity
        p.mesh.position.x += p.velocity.x * dt
        p.mesh.position.y += p.velocity.y * dt
        p.mesh.position.z += p.velocity.z * dt
        p.velocity.y -= 9.8 * dt // gravity
        // Fade out
        p.mesh.material.opacity = Math.max(0, 1 - progress)
      }
    }
  }

  _disposeBurst(burst) {
    this.scene.remove(burst.group)
    burst.geometry.dispose()
    for (const p of burst.particles) {
      p.mesh.material.dispose()
    }
  }

  dispose() {
    for (const burst of this.bursts) {
      this._disposeBurst(burst)
    }
    this.bursts = []
  }
}

// =============================================================================
// SPEECH BUBBLE
// =============================================================================

class SpeechBubble {
  constructor(scene, position, message, type = 'info') {
    this.scene = scene
    this.message = message
    this.type = type
    this.age = 0
    this.maxAge = type === 'approval' ? 30 : type === 'success' ? 10 : 5
    this.agentId = null

    this._createSprite(position)
  }

  _createSprite(position) {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    canvas.width = 256
    canvas.height = 96

    const bgColors = {
      info: 'rgba(40, 40, 60, 0.9)',
      success: 'rgba(30, 60, 40, 0.9)',
      approval: 'rgba(255, 200, 0, 0.95)',
      error: 'rgba(255, 60, 60, 0.9)',
      input: 'rgba(100, 100, 255, 0.9)',
    }
    const borderColors = {
      info: '#667788',
      success: '#66bb6a',
      approval: '#ffaa00',
      error: '#ff3333',
      input: '#4488ff',
    }
    const textColors = {
      info: '#ffffff',
      success: '#a5d6a7',
      approval: '#000000',
      error: '#ffffff',
      input: '#ffffff',
    }

    // Background rounded rect
    ctx.fillStyle = bgColors[this.type] || bgColors.info
    ctx.strokeStyle = borderColors[this.type] || borderColors.info
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.roundRect(8, 6, 240, 64, 10)
    ctx.fill()
    ctx.stroke()

    // Pointer triangle
    ctx.fillStyle = bgColors[this.type] || bgColors.info
    ctx.beginPath()
    ctx.moveTo(118, 70)
    ctx.lineTo(128, 90)
    ctx.lineTo(138, 70)
    ctx.fill()

    // Text (wrapped)
    ctx.fillStyle = textColors[this.type] || textColors.info
    ctx.font = 'bold 14px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    const words = this.message.split(' ')
    let line = ''
    let y = 28
    const lineHeight = 18
    const maxWidth = 215

    for (const word of words) {
      const testLine = line + word + ' '
      if (ctx.measureText(testLine).width > maxWidth && line !== '') {
        ctx.fillText(line.trim(), 128, y)
        line = word + ' '
        y += lineHeight
      } else {
        line = testLine
      }
    }
    ctx.fillText(line.trim(), 128, y)

    const texture = new THREE.CanvasTexture(canvas)
    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false,
    })

    this.sprite = new THREE.Sprite(material)
    this.sprite.scale.set(6, 2.25, 1)
    this.sprite.position.set(position.x, position.y + 3, position.z)
    this.sprite.userData = { type: 'bubble', bubbleType: this.type }
    this.scene.add(this.sprite)
  }

  update(dt, agentPosition) {
    this.age += dt

    // Follow agent
    if (agentPosition) {
      this.sprite.position.x = agentPosition.x
      this.sprite.position.y = agentPosition.y + 3
      this.sprite.position.z = agentPosition.z
    }

    // Gentle bob
    this.sprite.position.y += Math.sin(this.age * 3) * 0.01

    // Fade out near end (approval stays solid)
    if (this.type !== 'approval' && this.age > this.maxAge - 1) {
      this.sprite.material.opacity = Math.max(0, this.maxAge - this.age)
    }

    return this.age < this.maxAge
  }

  dismiss() {
    this.age = this.maxAge
  }

  dispose() {
    this.scene.remove(this.sprite)
    if (this.sprite.material.map) this.sprite.material.map.dispose()
    this.sprite.material.dispose()
  }
}

// =============================================================================
// FIREFLY AMBIENT PARTICLES
// =============================================================================

class FireflySystem {
  constructor(scene, count) {
    this.count = count
    this.phases = []
    this.speeds = []
    this.basePositions = []

    const positions = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const r = 5 + Math.random() * 25
      const theta = Math.random() * Math.PI * 2
      const y = 1 + Math.random() * 8
      const x = Math.cos(theta) * r
      const z = Math.sin(theta) * r

      positions[i * 3] = x
      positions[i * 3 + 1] = y
      positions[i * 3 + 2] = z

      this.basePositions.push(new THREE.Vector3(x, y, z))
      this.phases.push(Math.random() * Math.PI * 2)
      this.speeds.push(0.3 + Math.random() * 0.7)
    }

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    const material = new THREE.PointsMaterial({
      color: 0xffd700,
      size: 0.3,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })

    this.points = new THREE.Points(geometry, material)
    scene.add(this.points)
  }

  update(time) {
    const positions = this.points.geometry.attributes.position.array

    for (let i = 0; i < this.count; i++) {
      const base = this.basePositions[i]
      const phase = this.phases[i]
      const speed = this.speeds[i]

      // Gentle sine-wave drift
      positions[i * 3] = base.x + Math.sin(time * speed + phase) * 1.5
      positions[i * 3 + 1] = base.y + Math.sin(time * speed * 0.7 + phase * 2) * 0.5
      positions[i * 3 + 2] = base.z + Math.cos(time * speed * 0.8 + phase) * 1.5
    }

    this.points.geometry.attributes.position.needsUpdate = true

    // Pulse overall opacity (modulated by day/night multiplier)
    this.points.material.opacity = (0.4 + Math.sin(time * 0.5) * 0.2) * (this._opacityMultiplier ?? 1.0)
  }

  setOpacityMultiplier(m) {
    this._opacityMultiplier = m
  }

  dispose() {
    this.points.geometry.dispose()
    this.points.material.dispose()
  }
}

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useVillage3D(containerRef, options = {}) {
  const { onAgentClick, onZoneClick, onPedestalClick, onPortalClick, onDistrictChange, onWebGLError } = options

  // --- Reactive state (exposed) ---
  const selectedAgent = shallowRef(null)
  const hoveredObject = shallowRef(null)
  const activeZone = ref(null)
  const cameraMode = ref('orbit') // 'orbit' | 'focus-zone' | 'focus-agent'
  const focusTarget = ref(null)
  const selectedSceneAgents = ref([]) // Agent IDs selected via scene click (gold ring)

  // --- Three.js objects (shallowRef to avoid Proxy conflicts) ---
  const sceneRef = shallowRef(null)
  const cameraRef = shallowRef(null)
  const rendererRef = shallowRef(null)
  const controlsRef = shallowRef(null)

  // --- Internal state ---
  let clock = null
  let animationFrameId = null
  const isInitialized = ref(false)
  const webglError = ref(null)
  let elapsedTime = 0

  // Agent map (agentId -> agent object)
  const agents = new Map()

  // Visitor agents from other villages (Phase 5 — ghost shader)
  const visitors = new Map()
  const visitorWanderTimers = []

  // Zone groups, meshes for raycasting, glow rings
  const zoneGroups = new Map()
  const zonePlaceholders = new Map()
  const zoneGlowRings = new Map()
  const zoneLabelSprites = new Map()
  const zoneMeshes = []

  // Systems
  let particleSystem = null
  let fireflySystem = null
  const speechBubbles = []

  // Camera transitions
  let cameraTransition = null

  // Raycasting
  const raycaster = new THREE.Raycaster()
  const mouse = new THREE.Vector2()

  // Pending timeouts for cleanup
  const pendingTimeouts = []

  // Environment GLB objects (fountain, trees, bushes, etc.) for cleanup
  const environmentObjects = []

  // InstancedMesh objects for batched vegetation (Phase 0A performance)
  const instancedMeshes = []

  // External model loaders (singleton caches)
  const agentModels = useAgentModels()
  const villageModels = useVillageModels()

  // District manager (4x4 grid, camera tracking)
  const districtManager = useDistrictManager()

  // FPV mode + post-processing (Phase 9)
  const postProcessing = useVillagePostProcessing()
  const fpvMode = useFPVMode()
  const fpvInteraction = useFPVInteraction()
  const dayNight = useVillageDayNight()
  const agentAutonomy = useAgentAutonomy()

  // Layout persistence
  const { loadLayout, saveLayout, resetLayout: resetDraggableLayout, hasCustomLayout } =
    useDraggableZones('village-layout-perspective', VILLAGE_LAYOUT)

  // Store default positions for reset
  const defaultPositions = {}
  for (const [name, config] of Object.entries(VILLAGE_LAYOUT)) {
    defaultPositions[name] = [...config.pos]
  }

  // =========================================================================
  // INIT
  // =========================================================================

  function init() {
    if (!containerRef.value) return false

    const width = containerRef.value.clientWidth
    const height = containerRef.value.clientHeight
    if (width === 0 || height === 0) {
      console.warn('[Village3D] Container has zero dimensions, skipping init')
      return false
    }

    // WebGL availability check
    try {
      const testCanvas = document.createElement('canvas')
      const gl = testCanvas.getContext('webgl') || testCanvas.getContext('experimental-webgl')
      if (!gl) throw new Error('WebGL not supported')
    } catch (e) {
      console.error('[Village3D] WebGL not available:', e.message)
      webglError.value = 'WebGL is not available on this device.'
      onWebGLError?.('WebGL not supported')
      return false
    }

    // --- Scene ---
    const scene = new THREE.Scene()
    scene.fog = new THREE.FogExp2(0x0a0a14, 0.008)

    // --- Sky dome (gradient background) ---
    const { skyDome, stars } = _createSkyDome(scene)
    sceneRef.value = scene

    // --- Camera ---
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 800)
    camera.position.copy(ORBIT_POSITION)
    camera.lookAt(ORBIT_TARGET)
    cameraRef.value = camera

    // --- Renderer ---
    let renderer
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    } catch (e) {
      console.error('[Village3D] Failed to create WebGL renderer:', e.message)
      webglError.value = 'Failed to create 3D renderer.'
      onWebGLError?.(e.message)
      return false
    }
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.0

    if (!isMobile) {
      renderer.shadowMap.enabled = true
      renderer.shadowMap.type = THREE.PCFSoftShadowMap
    }

    containerRef.value.appendChild(renderer.domElement)
    rendererRef.value = renderer

    // --- Controls ---
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.minDistance = 12
    controls.maxDistance = 120
    controls.maxPolarAngle = Math.PI * 0.42
    controls.autoRotate = false
    controls.enablePan = true
    controls.screenSpacePanning = false // Pan along ground plane, not screen
    controls.panSpeed = 1.2
    controlsRef.value = controls

    // --- Lighting ---
    const { dirLight, ambient, hemi, zoneLights } = _setupLighting(scene)

    // --- Ground ---
    _createGround(scene)

    // --- Dirt paths ---
    _createPaths(scene)

    // --- District boundaries (Phase 2) ---
    _createDistrictBoundaries(scene)

    // --- Zone buildings ---
    _createZones(scene)

    // --- Agents ---
    _createAgents(scene)

    // --- Firefly ambient ---
    const fireflyCount = isMobile ? 20 : 50
    fireflySystem = new FireflySystem(scene, fireflyCount)

    // --- Particle system ---
    particleSystem = new ParticleSystem(scene)

    // --- Grand Prize Pedestal (H4) ---
    _createPedestal(scene)

    // --- Day/Night Cycle (Phase 12) ---
    dayNight.init({ dirLight, ambient, hemi, zoneLights, skyDome, stars, fog: scene.fog, renderer })

    // --- Agent Autonomy (Phase 15) ---
    agentAutonomy.init(agents, showBubble, VILLAGE_LAYOUT)

    // --- Apply saved layout if present ---
    const savedLayout = loadLayout()
    if (savedLayout?.zones) {
      for (const [name, savedPos] of Object.entries(savedLayout.zones)) {
        const group = zoneGroups.get(name)
        if (group && savedPos.pos) {
          group.position.set(savedPos.pos[0], 0, savedPos.pos[2])
          VILLAGE_LAYOUT[name].pos = [...savedPos.pos]
        }
      }
    }

    // --- Events ---
    renderer.domElement.addEventListener('click', _handleClick)
    renderer.domElement.addEventListener('dblclick', _handleDblClick)
    renderer.domElement.addEventListener('mousemove', _handleMouseMove)
    renderer.domElement.style.cursor = 'default'
    window.addEventListener('resize', _handleResize)

    // --- Clock ---
    clock = new THREE.Clock()

    // --- FPV + Post-Processing (Phase 9) ---
    postProcessing.init(renderer, scene, camera)
    fpvMode.init(renderer, camera)

    // --- FPV Interaction (Phase 10) ---
    fpvInteraction.init(camera, renderer, agents, fpvMode)
    fpvMode.setInteractionCallback(() => fpvInteraction.beginInteraction())

    isInitialized.value = true

    // --- Start render loop ---
    _animate()

    // --- Progressive enhancement: load GLBs ---
    _loadGLBModels()

    // --- Environment assets (fountain, trees, etc.) ---
    _loadEnvironmentAssets(scene)

    return true
  }

  // =========================================================================
  // LIGHTING
  // =========================================================================

  function _setupLighting(scene) {
    // Main warm directional light (sun/moon)
    const dirLight = new THREE.DirectionalLight(0xffe4b5, 1.5)
    dirLight.position.set(20, 30, 15)

    if (!isMobile) {
      dirLight.castShadow = true
      dirLight.shadow.mapSize.width = 1024
      dirLight.shadow.mapSize.height = 1024
      dirLight.shadow.camera.near = 0.5
      dirLight.shadow.camera.far = 150
      dirLight.shadow.camera.left = -50
      dirLight.shadow.camera.right = 50
      dirLight.shadow.camera.top = 50
      dirLight.shadow.camera.bottom = -50
    }

    scene.add(dirLight)

    // Ambient — deep night tint
    const ambient = new THREE.AmbientLight(0x1a1a3e, 0.5)
    scene.add(ambient)

    // Hemisphere — sky/ground colour bleed
    const hemi = new THREE.HemisphereLight(0x1a1a3e, 0x2d1f00, 0.4)
    scene.add(hemi)

    // Per-zone warm PointLights (lantern glow)
    const zoneLights = []
    if (!isMobile) {
      for (const [, config] of Object.entries(VILLAGE_LAYOUT)) {
        const light = new THREE.PointLight(0xffd090, 0.4, 10, 2)
        light.position.set(config.pos[0], 3, config.pos[2])
        scene.add(light)
        zoneLights.push(light)
      }
    }

    return { dirLight, ambient, hemi, zoneLights }
  }

  // =========================================================================
  // SKY DOME
  // =========================================================================

  function _createSkyDome(scene) {
    // Gradient sky using a large inverted sphere with vertex colors
    const skyGeo = new THREE.SphereGeometry(200, 32, 16)
    const skyColors = []
    const posAttr = skyGeo.getAttribute('position')

    for (let i = 0; i < posAttr.count; i++) {
      const y = posAttr.getY(i)
      const normalizedY = (y + 200) / 400 // 0 at bottom, 1 at top

      // Gradient: dark horizon → deep purple midway → black at zenith
      const horizonColor = new THREE.Color(0x0a0a14)
      const midColor = new THREE.Color(0x120822)
      const zenithColor = new THREE.Color(0x020208)

      let color
      if (normalizedY < 0.55) {
        color = horizonColor.clone().lerp(midColor, normalizedY / 0.55)
      } else {
        color = midColor.clone().lerp(zenithColor, (normalizedY - 0.55) / 0.45)
      }
      skyColors.push(color.r, color.g, color.b)
    }

    skyGeo.setAttribute('color', new THREE.Float32BufferAttribute(skyColors, 3))

    const skyMat = new THREE.MeshBasicMaterial({
      vertexColors: true,
      side: THREE.BackSide,
      fog: false,
    })

    const skyDome = new THREE.Mesh(skyGeo, skyMat)
    scene.add(skyDome)

    // Star particles in upper hemisphere (desktop only)
    if (!isMobile) {
      const starCount = 150
      const starGeo = new THREE.BufferGeometry()
      const starPositions = []
      const starSizes = []

      for (let i = 0; i < starCount; i++) {
        // Random position on upper hemisphere of large sphere
        const theta = Math.random() * Math.PI * 2
        const phi = Math.random() * Math.PI * 0.45 // Upper ~45%
        const r = 180 + Math.random() * 15

        starPositions.push(
          r * Math.sin(phi) * Math.cos(theta),
          r * Math.cos(phi) + 20, // Offset upward
          r * Math.sin(phi) * Math.sin(theta),
        )
        starSizes.push(0.5 + Math.random() * 1.5)
      }

      starGeo.setAttribute('position', new THREE.Float32BufferAttribute(starPositions, 3))
      starGeo.setAttribute('size', new THREE.Float32BufferAttribute(starSizes, 1))

      const starMat = new THREE.PointsMaterial({
        color: 0xffffff,
        size: 0.8,
        transparent: true,
        opacity: 0.6,
        fog: false,
        sizeAttenuation: true,
      })

      const stars = new THREE.Points(starGeo, starMat)
      scene.add(stars)
      return { skyDome, stars }
    }

    return { skyDome, stars: null }
  }

  // =========================================================================
  // GROUND
  // =========================================================================

  function _createGround(scene) {
    // Inner ring (0-20): bright grass
    const innerGeo = new THREE.PlaneGeometry(80, 80, 16, 16)
    innerGeo.rotateX(-Math.PI / 2)
    const innerMat = new THREE.MeshStandardMaterial({
      color: 0x1a2a15,
      roughness: 0.95,
      metalness: 0,
    })
    const innerGround = new THREE.Mesh(innerGeo, innerMat)
    innerGround.receiveShadow = true
    innerGround.userData = { type: 'ground' }
    scene.add(innerGround)

    // Outer ring (40-80): darker wilderness extending to 160x160
    const outerGeo = new THREE.PlaneGeometry(160, 160, 8, 8)
    outerGeo.rotateX(-Math.PI / 2)
    const outerMat = new THREE.MeshStandardMaterial({
      color: 0x111e0e,
      roughness: 1.0,
      metalness: 0,
    })
    const outerGround = new THREE.Mesh(outerGeo, outerMat)
    outerGround.position.y = -0.01 // Slightly below inner to avoid z-fighting
    outerGround.receiveShadow = true
    outerGround.userData = { type: 'ground' }
    scene.add(outerGround)

    // Subtle darker patches across the full area
    const patchGeo = new THREE.PlaneGeometry(4, 4)
    patchGeo.rotateX(-Math.PI / 2)
    const patchMat = new THREE.MeshStandardMaterial({
      color: 0x152010,
      roughness: 1.0,
      metalness: 0,
      transparent: true,
      opacity: 0.4,
    })

    for (let i = 0; i < 40; i++) {
      const patch = new THREE.Mesh(patchGeo, patchMat)
      patch.position.set(
        (Math.random() - 0.5) * 140,
        0.01,
        (Math.random() - 0.5) * 140,
      )
      patch.rotation.y = Math.random() * Math.PI
      patch.scale.setScalar(0.5 + Math.random() * 2.0)
      patch.receiveShadow = true
      scene.add(patch)
    }
  }

  // =========================================================================
  // DIRT PATHS
  // =========================================================================

  function _createPaths(scene) {
    const centerPos = VILLAGE_LAYOUT.village_square.pos
    const pathMat = new THREE.MeshBasicMaterial({ color: 0x3d2b1f })

    // Helper: draw a single path segment between two points
    function _drawPathSegment(x1, z1, x2, z2, width = 0.6) {
      const dx = x2 - x1
      const dz = z2 - z1
      const distance = Math.sqrt(dx * dx + dz * dz)
      if (distance < 0.1) return
      const midX = (x1 + x2) / 2
      const midZ = (z1 + z2) / 2
      const angle = Math.atan2(dz, dx)
      const pathGeo = new THREE.BoxGeometry(distance, 0.04, width)
      const path = new THREE.Mesh(pathGeo, pathMat)
      path.position.set(midX, 0.02, midZ)
      path.rotation.y = -angle
      scene.add(path)
    }

    // Inner ring zones: direct spoke paths from village_square
    const outerZones = new Set(['arena', 'bazaar', 'apothecary', 'nexus_tower', 'mines', 'sanctum'])
    for (const [name, config] of Object.entries(VILLAGE_LAYOUT)) {
      if (name === 'village_square') continue
      if (outerZones.has(name)) continue // Outer zones get branch paths below

      _drawPathSegment(centerPos[0], centerPos[2], config.pos[0], config.pos[2])
    }

    // Outer ring zones: path from nearest inner zone (branch path)
    const innerZoneNames = Object.keys(VILLAGE_LAYOUT).filter(n => !outerZones.has(n))
    for (const outerName of outerZones) {
      const outerPos = VILLAGE_LAYOUT[outerName].pos
      // Find nearest inner zone
      let nearestDist = Infinity
      let nearestPos = centerPos
      for (const innerName of innerZoneNames) {
        const iPos = VILLAGE_LAYOUT[innerName].pos
        const d = Math.hypot(outerPos[0] - iPos[0], outerPos[2] - iPos[2])
        if (d < nearestDist) {
          nearestDist = d
          nearestPos = iPos
        }
      }
      _drawPathSegment(nearestPos[0], nearestPos[2], outerPos[0], outerPos[2], 0.5)
    }

    // Ring road connecting outer zones (thin path)
    const outerRing = ['arena', 'mines', 'apothecary', 'bazaar', 'sanctum', 'nexus_tower']
    for (let i = 0; i < outerRing.length; i++) {
      const a = VILLAGE_LAYOUT[outerRing[i]].pos
      const b = VILLAGE_LAYOUT[outerRing[(i + 1) % outerRing.length]].pos
      _drawPathSegment(a[0], a[2], b[0], b[2], 0.35)
    }
  }

  // =========================================================================
  // DISTRICT BOUNDARIES (Phase 2 — subtle ground markers)
  // =========================================================================

  const districtBoundaryObjects = []

  function _createDistrictBoundaries(scene) {
    const gridLines = districtManager.getGridLines()
    const dashLen = 1.2
    const gapLen = 2.4
    const lineWidth = 0.15
    const lineHeight = 0.03

    const lineMat = new THREE.MeshBasicMaterial({
      color: 0x4a4a3a,
      transparent: true,
      opacity: 0.25,
    })

    for (const { x1, z1, x2, z2 } of gridLines) {
      const dx = x2 - x1
      const dz = z2 - z1
      const totalLen = Math.sqrt(dx * dx + dz * dz)
      const angle = Math.atan2(dz, dx)
      const step = dashLen + gapLen

      for (let d = 0; d < totalLen; d += step) {
        const segLen = Math.min(dashLen, totalLen - d)
        if (segLen < 0.2) break

        const cx = x1 + (d + segLen / 2) / totalLen * dx
        const cz = z1 + (d + segLen / 2) / totalLen * dz

        const dashGeo = new THREE.BoxGeometry(segLen, lineHeight, lineWidth)
        const dash = new THREE.Mesh(dashGeo, lineMat)
        dash.position.set(cx, 0.02, cz)
        dash.rotation.y = -angle
        scene.add(dash)
        districtBoundaryObjects.push(dash)
      }
    }

    // Corner markers at grid intersections (glowing dots)
    const markerGeo = new THREE.CircleGeometry(0.4, 8)
    markerGeo.rotateX(-Math.PI / 2)
    const markerMat = new THREE.MeshBasicMaterial({
      color: 0x8a8a6a,
      transparent: true,
      opacity: 0.3,
    })

    for (let col = 1; col < districtManager.GRID_COLS; col++) {
      for (let row = 1; row < districtManager.GRID_ROWS; row++) {
        const x = col * districtManager.DISTRICT_SIZE - districtManager.WORLD_HALF
        const z = row * districtManager.DISTRICT_SIZE - districtManager.WORLD_HALF
        const marker = new THREE.Mesh(markerGeo, markerMat)
        marker.position.set(x, 0.03, z)
        scene.add(marker)
        districtBoundaryObjects.push(marker)
      }
    }
  }

  // =========================================================================
  // ZONE BUILDINGS
  // =========================================================================

  function _createZones(scene) {
    for (const [name, config] of Object.entries(VILLAGE_LAYOUT)) {
      const group = new THREE.Group()
      group.position.set(config.pos[0], 0, config.pos[2])
      group.userData = { type: 'zone', name }

      // --- Placeholder box ---
      const boxGeo = new THREE.BoxGeometry(3, 3, 3)
      const boxMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(config.color),
        emissive: new THREE.Color(config.color),
        emissiveIntensity: 0.15,
        transparent: true,
        opacity: 0.75,
        roughness: 0.7,
        metalness: 0.1,
      })
      const box = new THREE.Mesh(boxGeo, boxMat)
      box.position.y = 1.5
      box.castShadow = !isMobile
      group.add(box)
      zonePlaceholders.set(name, box)

      // --- Zone label sprite ---
      const labelSprite = _createZoneLabelSprite(config.label, config.color)
      labelSprite.position.y = 5
      group.add(labelSprite)
      zoneLabelSprites.set(name, labelSprite)

      // --- Glow ring at ground ---
      const ringGeo = new THREE.TorusGeometry(2.5, 0.06, 8, 32)
      const ringMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(config.color),
        transparent: true,
        opacity: 0.3,
      })
      const ring = new THREE.Mesh(ringGeo, ringMat)
      ring.rotation.x = -Math.PI / 2
      ring.position.y = 0.05
      group.add(ring)
      zoneGlowRings.set(name, ring)

      // Enable frustum culling on all children (Three.js skips Group by default)
      group.traverse((c) => { c.frustumCulled = true })

      scene.add(group)
      zoneGroups.set(name, group)
      zoneMeshes.push(group)
    }
  }

  function _createZoneLabelSprite(text, dotColor, level = 0) {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    canvas.width = 160
    canvas.height = 48

    // Background
    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)'
    ctx.beginPath()
    ctx.roundRect(4, 4, 152, 40, 6)
    ctx.fill()

    // Colored dot
    ctx.fillStyle = dotColor
    ctx.beginPath()
    ctx.arc(16, 24, 4, 0, Math.PI * 2)
    ctx.fill()

    // Text
    ctx.fillStyle = '#ffffff'
    ctx.font = 'bold 13px sans-serif'
    ctx.textAlign = 'left'
    ctx.textBaseline = 'middle'
    ctx.fillText(text, 24, 24)

    // Level stars (gold dots)
    if (level > 0) {
      const textWidth = ctx.measureText(text).width
      const starStart = 24 + textWidth + 6
      ctx.fillStyle = '#FFD700'
      for (let i = 0; i < Math.min(level, 5); i++) {
        ctx.beginPath()
        ctx.arc(starStart + i * 10, 24, 3, 0, Math.PI * 2)
        ctx.fill()
      }
    }

    const texture = new THREE.CanvasTexture(canvas)
    const material = new THREE.SpriteMaterial({ map: texture, transparent: true })
    const sprite = new THREE.Sprite(material)
    sprite.scale.set(5, 1.5, 1)
    return sprite
  }

  // =========================================================================
  // AGENTS
  // =========================================================================

  function _createAgents(scene) {
    const squarePos = VILLAGE_LAYOUT.village_square.pos

    for (const id of AGENT_IDS) {
      const colorHex = AGENT_COLORS[id] || AGENT_COLORS.default
      const color = new THREE.Color(colorHex)

      const group = new THREE.Group()
      group.userData = { type: 'agent', id }

      // --- Sphere placeholder (IcosahedronGeometry detail 2 for smooth look) ---
      const sphereGeo = new THREE.IcosahedronGeometry(0.6, 2)
      const sphereMat = new THREE.MeshStandardMaterial({
        color,
        emissive: color,
        emissiveIntensity: 0.5,
        roughness: 0.3,
        metalness: 0.4,
      })
      const sphere = new THREE.Mesh(sphereGeo, sphereMat)
      sphere.position.y = 0.8
      sphere.castShadow = !isMobile
      group.add(sphere)

      // --- Glow ring at feet (visible when working) ---
      const glowGeo = new THREE.TorusGeometry(0.8, 0.05, 8, 24)
      const glowMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0,
      })
      const glowRing = new THREE.Mesh(glowGeo, glowMat)
      glowRing.rotation.x = -Math.PI / 2
      glowRing.position.y = 0.05
      group.add(glowRing)

      // --- Selection ring (visible when scene-selected, gold, larger) ---
      const selGeo = new THREE.TorusGeometry(1.1, 0.06, 8, 32)
      const selMat = new THREE.MeshBasicMaterial({
        color: 0xffd700,
        transparent: true,
        opacity: 0,
      })
      const selectionRing = new THREE.Mesh(selGeo, selMat)
      selectionRing.rotation.x = -Math.PI / 2
      selectionRing.position.y = 0.03
      group.add(selectionRing)

      // --- Name label ---
      const nameSprite = _createAgentNameSprite(id)
      nameSprite.position.y = 2.2
      group.add(nameSprite)

      // Offset agents slightly so they don't stack at village_square
      const offsetAngle = (AGENT_IDS.indexOf(id) / AGENT_IDS.length) * Math.PI * 2
      const offsetR = 2
      group.position.set(
        squarePos[0] + Math.cos(offsetAngle) * offsetR,
        0,
        squarePos[2] + Math.sin(offsetAngle) * offsetR,
      )

      scene.add(group)

      const agent = {
        id,
        group,
        mesh: sphere,
        glowRing,
        selectionRing,
        nameSprite,
        position: group.position,
        targetPosition: null,
        state: 'idle', // 'idle' | 'walking' | 'working'
        currentZone: 'village_square',
        targetZone: null,
        currentTool: null,
        walkSpeed: 8,
        workPulse: 0,
        colorHex,
        color,
        glbSwapped: false,
        idleGlowBase: 0,
      }

      agents.set(id, agent)
    }
  }

  function _createAgentNameSprite(name, level = 0) {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    canvas.width = 160
    canvas.height = 32

    ctx.shadowColor = '#000000'
    ctx.shadowBlur = 4

    // Agent name
    ctx.fillStyle = '#ffffff'
    ctx.font = 'bold 18px monospace'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    const nameX = level > 0 ? 64 : 80
    ctx.fillText(name, nameX, 16)

    // Level badge
    if (level > 0) {
      ctx.shadowBlur = 0
      const badgeX = nameX + ctx.measureText(name).width / 2 + 8
      ctx.fillStyle = 'rgba(255, 215, 0, 0.8)'
      ctx.beginPath()
      ctx.roundRect(badgeX, 4, 30, 22, 4)
      ctx.fill()
      ctx.fillStyle = '#000000'
      ctx.font = 'bold 12px monospace'
      ctx.textAlign = 'center'
      ctx.fillText(`${level}`, badgeX + 15, 16)
    }

    const texture = new THREE.CanvasTexture(canvas)
    const material = new THREE.SpriteMaterial({ map: texture, transparent: true })
    const sprite = new THREE.Sprite(material)
    sprite.scale.set(4.5, 0.9, 1)
    return sprite
  }

  // =========================================================================
  // GAMIFICATION VISUAL METHODS (E5)
  // =========================================================================

  function updateAgentNameplate(agentId, level) {
    const agent = agents.get(agentId)
    if (!agent) return
    // Remove old nameSprite
    if (agent.nameSprite) {
      agent.group.remove(agent.nameSprite)
      agent.nameSprite.material.map?.dispose()
      agent.nameSprite.material.dispose()
    }
    // Create new one with level badge
    const sprite = _createAgentNameSprite(agentId, level)
    sprite.position.y = agent.glbSwapped ? 3.0 : 2.2
    agent.group.add(sprite)
    agent.nameSprite = sprite
  }

  function updateZoneLabel(zoneName, level) {
    const group = zoneGroups.get(zoneName)
    const oldSprite = zoneLabelSprites.get(zoneName)
    if (!group) return
    // Remove old label
    if (oldSprite) {
      group.remove(oldSprite)
      oldSprite.material.map?.dispose()
      oldSprite.material.dispose()
    }
    // Create new label with level stars
    const config = VILLAGE_LAYOUT[zoneName]
    if (!config) return
    const sprite = _createZoneLabelSprite(config.label, config.color, level)
    sprite.position.y = 5
    group.add(sprite)
    zoneLabelSprites.set(zoneName, sprite)
  }

  function setAgentIdleGlow(agentId, level) {
    const agent = agents.get(agentId)
    if (!agent) return
    // Level 3+: subtle ambient glow when idle
    agent.idleGlowBase = level >= 3 ? 0.05 * (level - 2) : 0
  }

  function emitAchievementBurst(position) {
    if (!particleSystem) return
    // Gold burst, double the normal count
    particleSystem.emit(position, 0xffd700, 40)
  }

  // =========================================================================
  // G5: AGENT LOCK/UNLOCK VISUALS (Quest Engine)
  // =========================================================================

  const agentLockedState = new Map()

  function _createMysteryNameSprite() {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    canvas.width = 160
    canvas.height = 32

    ctx.shadowColor = '#000000'
    ctx.shadowBlur = 4

    ctx.fillStyle = 'rgba(255, 255, 255, 0.35)'
    ctx.font = 'bold 22px monospace'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('?', 80, 16)

    const texture = new THREE.CanvasTexture(canvas)
    const material = new THREE.SpriteMaterial({ map: texture, transparent: true })
    const sprite = new THREE.Sprite(material)
    sprite.scale.set(4.5, 0.9, 1)
    return sprite
  }

  function setAgentLocked(agentId, locked) {
    const agent = agents.get(agentId)
    if (!agent) return

    agentLockedState.set(agentId, locked)

    if (locked) {
      // Desaturate mesh — dark grey, low emissive
      if (agent.mesh?.material) {
        agent.mesh.material._origColor = agent.mesh.material.color?.clone()
        agent.mesh.material._origEmissive = agent.mesh.material.emissive?.clone()
        agent.mesh.material._origEmissiveIntensity = agent.mesh.material.emissiveIntensity
        agent.mesh.material.color.set(0x333333)
        agent.mesh.material.emissive.set(0x111111)
        agent.mesh.material.emissiveIntensity = 0.1
      }
      // Also desaturate GLB children
      agent.group.traverse((child) => {
        if (child.isMesh && child !== agent.mesh && child !== agent.glowRing && child !== agent.selectionRing && child.material) {
          child.material._origColor = child.material.color?.clone()
          child.material._origEmissive = child.material.emissive?.clone()
          child.material._origEmissiveIntensity = child.material.emissiveIntensity
          child.material.color?.set(0x333333)
          if (child.material.emissive) {
            child.material.emissive.set(0x111111)
            child.material.emissiveIntensity = 0.1
          }
        }
      })

      // Hide glow ring
      agent.glowRing.material.opacity = 0
      agent.glowRing.visible = false

      // Replace nameplate with "?" mystery sprite
      if (agent.nameSprite) {
        agent.group.remove(agent.nameSprite)
        agent.nameSprite.material.map?.dispose()
        agent.nameSprite.material.dispose()
      }
      const mystery = _createMysteryNameSprite()
      mystery.position.y = agent.glbSwapped ? 3.0 : 2.2
      agent.group.add(mystery)
      agent.nameSprite = mystery
      agent.nameSprite.userData.mystery = true
    } else {
      // Restore original colors
      if (agent.mesh?.material) {
        if (agent.mesh.material._origColor) {
          agent.mesh.material.color.copy(agent.mesh.material._origColor)
        }
        if (agent.mesh.material._origEmissive) {
          agent.mesh.material.emissive.copy(agent.mesh.material._origEmissive)
        }
        if (agent.mesh.material._origEmissiveIntensity !== undefined) {
          agent.mesh.material.emissiveIntensity = agent.mesh.material._origEmissiveIntensity
        }
      }
      // Restore GLB children
      agent.group.traverse((child) => {
        if (child.isMesh && child !== agent.mesh && child !== agent.glowRing && child !== agent.selectionRing && child.material) {
          if (child.material._origColor) child.material.color?.copy(child.material._origColor)
          if (child.material._origEmissive) child.material.emissive?.copy(child.material._origEmissive)
          if (child.material._origEmissiveIntensity !== undefined) {
            child.material.emissiveIntensity = child.material._origEmissiveIntensity
          }
        }
      })

      // Restore glow ring
      agent.glowRing.visible = true
      agent.glowRing.material.opacity = agent.idleGlowBase || 0

      // Restore proper nameplate (with level if gamification active)
      if (agent.nameSprite?.userData?.mystery) {
        agent.group.remove(agent.nameSprite)
        agent.nameSprite.material.map?.dispose()
        agent.nameSprite.material.dispose()
        const sprite = _createAgentNameSprite(agentId, 0)
        sprite.position.y = agent.glbSwapped ? 3.0 : 2.2
        agent.group.add(sprite)
        agent.nameSprite = sprite
      }
    }
  }

  function isAgentLocked(agentId) {
    return agentLockedState.get(agentId) || false
  }

  // =========================================================================
  // G1: ZONE LOCK/UNLOCK VISUALS (Quest Engine)
  // =========================================================================

  const zonePadlockSprites = new Map()
  const zoneLockedState = new Map()

  function _createPadlockSprite() {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    canvas.width = 64
    canvas.height = 64

    // Padlock body
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)'
    ctx.beginPath()
    ctx.roundRect(16, 28, 32, 28, 4)
    ctx.fill()
    ctx.strokeStyle = '#FFD700'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.roundRect(16, 28, 32, 28, 4)
    ctx.stroke()

    // Shackle
    ctx.strokeStyle = '#FFD700'
    ctx.lineWidth = 3
    ctx.beginPath()
    ctx.arc(32, 28, 12, Math.PI, 0)
    ctx.stroke()

    // Keyhole
    ctx.fillStyle = '#FFD700'
    ctx.beginPath()
    ctx.arc(32, 40, 3, 0, Math.PI * 2)
    ctx.fill()
    ctx.fillRect(31, 42, 2, 6)

    const texture = new THREE.CanvasTexture(canvas)
    const mat = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false })
    const sprite = new THREE.Sprite(mat)
    sprite.scale.set(1.2, 1.2, 1)
    return sprite
  }

  function setZoneLocked(zoneName, locked) {
    const group = zoneGroups.get(zoneName)
    if (!group) return

    zoneLockedState.set(zoneName, locked)

    // Adjust building placeholder material
    const placeholder = zonePlaceholders.get(zoneName)
    if (placeholder && placeholder.material) {
      if (locked) {
        placeholder.material.opacity = 0.25
        placeholder.material.emissiveIntensity = 0.03
      } else {
        placeholder.material.opacity = 0.75
        placeholder.material.emissiveIntensity = 0.15
      }
    }

    // Adjust GLB model materials if loaded
    group.traverse((child) => {
      if (child.isMesh && child !== placeholder) {
        if (child.material) {
          const mat = child.material
          if (locked) {
            mat._origEmissiveIntensity = mat.emissiveIntensity
            mat._origOpacity = mat.opacity
            mat.emissiveIntensity = 0.02
            if (mat.transparent) mat.opacity = Math.min(mat.opacity, 0.3)
          } else if (mat._origEmissiveIntensity !== undefined) {
            mat.emissiveIntensity = mat._origEmissiveIntensity
            if (mat.transparent) mat.opacity = mat._origOpacity || 0.75
          }
        }
      }
    })

    // Glow ring
    const ring = zoneGlowRings.get(zoneName)
    if (ring) {
      ring.material.opacity = locked ? 0.08 : 0.3
    }

    // Label sprite dim
    const label = zoneLabelSprites.get(zoneName)
    if (label) {
      label.material.opacity = locked ? 0.3 : 1.0
    }

    // Padlock sprite
    if (locked) {
      if (!zonePadlockSprites.has(zoneName)) {
        const padlock = _createPadlockSprite()
        padlock.position.y = 4.2
        group.add(padlock)
        zonePadlockSprites.set(zoneName, padlock)
      }
    } else {
      const existing = zonePadlockSprites.get(zoneName)
      if (existing) {
        group.remove(existing)
        existing.material.map?.dispose()
        existing.material.dispose()
        zonePadlockSprites.delete(zoneName)
      }
    }
  }

  // =========================================================================
  // G3: UNLOCK CEREMONIES — The Dopamine Moment
  // =========================================================================

  let ceremonyQueue = []
  let ceremonyActive = false
  let ceremonyCurrent = null
  let ceremonyId = 0

  function playUnlockCeremony(zoneName, onUnlock) {
    ceremonyQueue.push({ zoneName, onUnlock })
    if (!ceremonyActive) _runNextCeremony()
  }

  function skipCeremony() {
    if (!ceremonyActive || !ceremonyCurrent) return
    _skipCurrentCeremony()
  }

  function _skipCurrentCeremony() {
    if (!ceremonyCurrent) return
    const { zoneName, savedPos, savedTarget, onUnlock } = ceremonyCurrent
    ceremonyId++ // Invalidate all pending ceremony callbacks
    setZoneLocked(zoneName, false)
    onUnlock?.()
    _startCameraTransition(savedPos, savedTarget, 0.5)
    const tid = setTimeout(() => {
      ceremonyActive = false
      ceremonyCurrent = null
      _runNextCeremony()
    }, 600)
    pendingTimeouts.push(tid)
  }

  function _runNextCeremony() {
    if (ceremonyQueue.length === 0) {
      ceremonyActive = false
      ceremonyCurrent = null
      return
    }

    ceremonyActive = true
    const myId = ++ceremonyId
    const { zoneName, onUnlock } = ceremonyQueue.shift()
    const zone = VILLAGE_LAYOUT[zoneName]

    if (!zone) {
      onUnlock?.()
      _runNextCeremony()
      return
    }

    // Save current camera state
    const savedPos = cameraRef.value?.position.clone() || ORBIT_POSITION.clone()
    const savedTarget = controlsRef.value?.target.clone() || ORBIT_TARGET.clone()
    ceremonyCurrent = { zoneName, savedPos, savedTarget, onUnlock }

    // Phase 1: Pan camera to zone (1.5s)
    const zoneTarget = new THREE.Vector3(zone.pos[0], 2, zone.pos[2])
    const cameraPos = zoneTarget.clone().add(new THREE.Vector3(6, 5, 6))
    _startCameraTransition(cameraPos, zoneTarget, 1.5)

    const tid1 = setTimeout(() => {
      if (myId !== ceremonyId) return // Stale — ceremony was skipped

      // Phase 2: Unlock effects
      // Padlock shatter animation
      const padlock = zonePadlockSprites.get(zoneName)
      if (padlock) {
        padlock.userData = { shattering: true, shatterStart: performance.now() }
      }

      // Brighten building
      setZoneLocked(zoneName, false)

      // Gold particle rain
      if (particleSystem) {
        const rainPos = new THREE.Vector3(zone.pos[0], 8, zone.pos[2])
        particleSystem.rain(rainPos, 0xffd700, 60)
      }

      // Zone unlock bubble (positioned at zone, not following any agent)
      if (sceneRef.value) {
        const bubblePos = new THREE.Vector3(zone.pos[0], 4, zone.pos[2])
        const bubble = new SpeechBubble(sceneRef.value, bubblePos, `${zone.label} Unlocked!`, 'success')
        bubble.agentId = '__ceremony__'
        bubble.maxAge = 5
        speechBubbles.push(bubble)
      }

      // Fire the unlock callback (caller plays fanfare sound)
      onUnlock?.()

      // Phase 3: Hold for admiration, then pan back
      const tid2 = setTimeout(() => {
        if (myId !== ceremonyId) return
        _startCameraTransition(savedPos, savedTarget, 1.0)

        const tid3 = setTimeout(() => {
          if (myId !== ceremonyId) return
          ceremonyActive = false
          ceremonyCurrent = null
          _runNextCeremony()
        }, 1200)
        pendingTimeouts.push(tid3)
      }, 3000)
      pendingTimeouts.push(tid2)
    }, 1700)
    pendingTimeouts.push(tid1)
  }

  // =========================================================================
  // H4: GRAND PRIZE PEDESTAL — The Village Shrine
  // =========================================================================

  let pedestalGroup = null
  let pedestalStage = null
  let pedestalStageElements = null  // Current stage-specific meshes
  let pedestalLight = null
  let pedestalOrbitParticles = null

  const PEDESTAL_POS = new THREE.Vector3(3, 0, -3) // Near fountain, Village Square

  function _createPedestal(scene) {
    pedestalGroup = new THREE.Group()
    pedestalGroup.position.copy(PEDESTAL_POS)
    pedestalGroup.userData = { type: 'pedestal' }

    // Stone base cylinder
    const baseGeo = new THREE.CylinderGeometry(0.8, 1.0, 1.2, 8)
    const baseMat = new THREE.MeshStandardMaterial({
      color: 0x555566,
      roughness: 0.9,
      metalness: 0.1,
    })
    const base = new THREE.Mesh(baseGeo, baseMat)
    base.position.y = 0.6
    base.castShadow = !isMobile
    pedestalGroup.add(base)

    // Top platform
    const topGeo = new THREE.CylinderGeometry(0.9, 0.8, 0.15, 8)
    const topMat = new THREE.MeshStandardMaterial({
      color: 0x666677,
      roughness: 0.8,
      metalness: 0.15,
    })
    const top = new THREE.Mesh(topGeo, topMat)
    top.position.y = 1.275
    top.castShadow = !isMobile
    pedestalGroup.add(top)

    // Faint white glow (default seeker state)
    pedestalLight = new THREE.PointLight(0xffffff, 0.3, 5)
    pedestalLight.position.y = 2.5
    pedestalGroup.add(pedestalLight)

    scene.add(pedestalGroup)

    // Default to seeker state
    evolvePedestal('seeker')
  }

  function evolvePedestal(stage) {
    if (!pedestalGroup) return
    if (stage === pedestalStage) return
    pedestalStage = stage

    // Remove old stage elements
    if (pedestalStageElements) {
      for (const el of pedestalStageElements) {
        pedestalGroup.remove(el)
        el.traverse((child) => {
          if (child.geometry) child.geometry.dispose()
          if (child.material) child.material.dispose()
        })
      }
    }
    pedestalStageElements = []

    // Remove old orbit particles
    if (pedestalOrbitParticles) {
      pedestalGroup.remove(pedestalOrbitParticles)
      pedestalOrbitParticles.geometry.dispose()
      pedestalOrbitParticles.material.dispose()
      pedestalOrbitParticles = null
    }

    if (stage === 'seeker' || !stage) {
      // Faint white glow, no crystal
      pedestalLight.color.set(0xffffff)
      pedestalLight.intensity = 0.3

    } else if (stage === 'adept') {
      // Blue crystal shard
      const crystalGeo = new THREE.OctahedronGeometry(0.35, 0)
      const crystalMat = new THREE.MeshStandardMaterial({
        color: 0x60a5fa,
        emissive: 0x60a5fa,
        emissiveIntensity: 0.6,
        transparent: true,
        opacity: 0.85,
        roughness: 0.1,
        metalness: 0.5,
      })
      const crystal = new THREE.Mesh(crystalGeo, crystalMat)
      crystal.position.y = 1.8
      crystal.castShadow = !isMobile
      pedestalGroup.add(crystal)
      pedestalStageElements.push(crystal)

      pedestalLight.color.set(0x60a5fa)
      pedestalLight.intensity = 0.6

    } else if (stage === 'opus') {
      // Purple octahedron, larger
      const octoGeo = new THREE.OctahedronGeometry(0.5, 1)
      const octoMat = new THREE.MeshStandardMaterial({
        color: 0xa78bfa,
        emissive: 0xa78bfa,
        emissiveIntensity: 0.7,
        transparent: true,
        opacity: 0.9,
        roughness: 0.05,
        metalness: 0.6,
      })
      const octo = new THREE.Mesh(octoGeo, octoMat)
      octo.position.y = 2.0
      octo.castShadow = !isMobile
      pedestalGroup.add(octo)
      pedestalStageElements.push(octo)

      // Orbiting particles
      _createOrbitParticles(0xa78bfa, 8)

      pedestalLight.color.set(0xa78bfa)
      pedestalLight.intensity = 0.8

    } else if (stage === 'azothic') {
      // Golden dodecahedron shrine
      const dodecGeo = new THREE.DodecahedronGeometry(0.55, 0)
      const dodecMat = new THREE.MeshStandardMaterial({
        color: 0xffd700,
        emissive: 0xffd700,
        emissiveIntensity: 0.8,
        roughness: 0.05,
        metalness: 0.8,
      })
      const dodec = new THREE.Mesh(dodecGeo, dodecMat)
      dodec.position.y = 2.2
      dodec.castShadow = !isMobile
      pedestalGroup.add(dodec)
      pedestalStageElements.push(dodec)

      // Orbiting particles (gold, more)
      _createOrbitParticles(0xffd700, 16)

      // "SensorHead Awaits" text sprite
      const textSprite = _createPedestalTextSprite('SensorHead Awaits')
      textSprite.position.y = 3.5
      pedestalGroup.add(textSprite)
      pedestalStageElements.push(textSprite)

      pedestalLight.color.set(0xffd700)
      pedestalLight.intensity = 1.2
    }
  }

  function _createOrbitParticles(colorHex, count) {
    const positions = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2
      positions[i * 3] = Math.cos(angle) * 1.2
      positions[i * 3 + 1] = 2.0 + Math.sin(angle * 2) * 0.3
      positions[i * 3 + 2] = Math.sin(angle) * 1.2
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    const mat = new THREE.PointsMaterial({
      color: colorHex,
      size: 0.15,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })

    pedestalOrbitParticles = new THREE.Points(geo, mat)
    pedestalGroup.add(pedestalOrbitParticles)
  }

  function _createPedestalTextSprite(text) {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    canvas.width = 256
    canvas.height = 48

    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)'
    ctx.beginPath()
    ctx.roundRect(8, 6, 240, 36, 8)
    ctx.fill()

    ctx.fillStyle = '#FFD700'
    ctx.font = 'bold 16px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(text, 128, 24)

    const texture = new THREE.CanvasTexture(canvas)
    const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false })
    const sprite = new THREE.Sprite(material)
    sprite.scale.set(4, 0.75, 1)
    return sprite
  }

  function _updatePedestal(dt, time) {
    if (!pedestalGroup) return

    // Rotate stage elements
    if (pedestalStageElements) {
      for (const el of pedestalStageElements) {
        if (el.isMesh) {
          el.rotation.y += dt * 0.8
          // Gentle bob
          el.position.y = el.position.y + Math.sin(time * 2) * 0.002
        }
      }
    }

    // Orbit particles rotation
    if (pedestalOrbitParticles) {
      pedestalOrbitParticles.rotation.y += dt * 1.2
      pedestalOrbitParticles.material.opacity = 0.5 + Math.sin(time * 3) * 0.3
    }

    // Light pulse
    if (pedestalLight && pedestalStage && pedestalStage !== 'seeker') {
      const basePulse = pedestalStage === 'azothic' ? 1.0 : pedestalStage === 'opus' ? 0.7 : 0.5
      pedestalLight.intensity = basePulse + Math.sin(time * 2) * 0.2
    }
  }

  // =========================================================================
  // GLB PROGRESSIVE ENHANCEMENT
  // =========================================================================

  function _loadGLBModels() {
    // Load zone buildings (non-blocking)
    villageModels.preloadAll().then(() => {
      if (!isInitialized.value) return
      const scene = sceneRef.value
      if (!scene) return

      for (const [name, config] of Object.entries(VILLAGE_LAYOUT)) {
        const modelId = config.modelId
        if (!modelId || !villageModels.isLoaded(modelId)) continue

        const clone = villageModels.getZoneClone(modelId, 4)
        if (!clone) continue

        // Remove placeholder box, add GLB clone
        const group = zoneGroups.get(name)
        const placeholder = zonePlaceholders.get(name)
        if (group && placeholder) {
          group.remove(placeholder)
          placeholder.geometry.dispose()
          placeholder.material.dispose()
          zonePlaceholders.delete(name)

          // Enable shadows on all child meshes
          clone.traverse((child) => {
            if (child.isMesh) {
              child.castShadow = !isMobile
              child.receiveShadow = true
            }
          })

          group.add(clone)
        }
      }
    })

    // Load agent avatars (non-blocking)
    agentModels.preloadAll().then(() => {
      if (!isInitialized.value) return
      const scene = sceneRef.value
      if (!scene) return

      for (const agent of agents.values()) {
        if (agent.glbSwapped) continue
        if (!agentModels.isLoaded(agent.id)) continue

        const clone = agentModels.getAgentClone(agent.id, 2.5)
        if (!clone) continue

        // Remove sphere, add GLB
        const oldMesh = agent.mesh
        agent.group.remove(oldMesh)
        oldMesh.geometry.dispose()
        oldMesh.material.dispose()

        clone.position.y = 0
        clone.traverse((child) => {
          if (child.isMesh) {
            child.castShadow = !isMobile
          }
        })

        agent.group.add(clone)
        agent.mesh = clone
        agent.glbSwapped = true
      }
    })
  }

  // =========================================================================
  // ENVIRONMENT ASSETS (fountain, trees, bushes, ferns, lanterns, fire pit)
  // =========================================================================

  function _loadEnvironmentAssets(scene) {
    const gltfLoader = new GLTFLoader()

    // --- Asset definitions ---
    const ENVIRONMENT_ASSETS = {
      fountain: '/models/village3d/fountain.glb',
      fire_pit: '/models/village3d/fire_pit.glb',
      fern: '/models/village3d/fern.glb',
      tree_round: '/models/village3d/tree_round.glb',
      tree_conifer: '/models/village3d/tree_conifer.glb',
      bush: '/models/village3d/bush.glb',
      lantern: '/models/village3d/lantern.glb',
      portal_arch: '/models/village3d/portal_arch.glb',
    }

    // --- Tree positions: inner ring (avoiding zone buildings) ---
    const treePositionsBase = [
      [-8, 0, -14], [8, 0, -18], [-18, 0, -6], [18, 0, -8],
      [-18, 0, 5], [18, 0, 5], [-6, 0, 18], [8, 0, 18],
      [-16, 0, 16], [16, 0, 16], [20, 0, -16], [-20, 0, -16],
    ]
    const treePositionsDesktop = [
      [0, 0, -20], [-20, 0, 0], [20, 0, 0], [0, 0, 20],
    ]
    // Middle ring (20-40): denser forest
    const treePositionsMiddle = [
      [-30, 0, -10], [-28, 0, 12], [30, 0, -8], [28, 0, 14],
      [-10, 0, -30], [12, 0, -28], [-10, 0, 30], [14, 0, 28],
      [-26, 0, -22], [26, 0, -22], [-26, 0, 22], [26, 0, 22],
      [-34, 0, 0], [34, 0, 0], [0, 0, -34], [0, 0, 34],
      [-22, 0, -30], [22, 0, -30], [-22, 0, 30], [22, 0, 30],
      [-32, 0, -18], [32, 0, 18], [-18, 0, 32], [18, 0, -32],
    ]
    // Outer ring (40-60): sparse wilderness
    const treePositionsOuter = [
      [-45, 0, -15], [45, 0, -15], [-45, 0, 15], [45, 0, 15],
      [-15, 0, -45], [15, 0, -45], [-15, 0, 45], [15, 0, 45],
    ]
    const treePositions = isMobile
      ? treePositionsBase.slice(0, 8)
      : [...treePositionsBase, ...treePositionsDesktop, ...treePositionsMiddle, ...treePositionsOuter]

    // --- Bush positions: near zone buildings + middle ring ---
    const bushPositions = [
      [-10, 0, -7], [7, 0, -12], [16, 0, -5], [3, 0, 12],
      [-13, 0, -9], [11, 0, -14], [-9, 0, 10], [-13, 0, 14],
    ]
    const bushPositionsMiddle = [
      [-26, 0, -2], [26, 0, 2], [-2, 0, -26], [2, 0, 26],
      [-22, 0, -18], [22, 0, -18], [-18, 0, 22], [18, 0, 22],
      [-30, 0, 8], [30, 0, -8], [8, 0, 30], [-8, 0, -30],
      [-24, 0, 6], [24, 0, -6], [6, 0, -24], [-6, 0, 24],
    ]
    const bushPositionsFull = isMobile
      ? bushPositions.slice(0, 6)
      : [...bushPositions, [15, 0, -10], [5, 0, 16], [-16, 0, 2], [-5, 0, -16], ...bushPositionsMiddle]

    // --- Fern positions: along paths + near Memory Garden + middle ring ---
    const fernPositions = [
      [3, 0, -10], [7, 0, -16], [-2, 0, -8], [9, 0, -11],
      [1, 0, -5], [-4, 0, -12],
    ]
    const fernPositionsMiddle = [
      [-22, 0, -12], [22, 0, 12], [-12, 0, 22], [12, 0, -22],
      [-28, 0, 4], [28, 0, -4], [4, 0, 28], [-4, 0, -28],
    ]
    const fernPositionsFull = isMobile
      ? fernPositions.slice(0, 4)
      : [...fernPositions, [-7, 0, -10], [2, 0, -17], [6, 0, -8], [-1, 0, -14], ...fernPositionsMiddle]

    // --- Lantern positions (along main paths + outer ring road) ---
    const lanternPositions = [
      [-6, 0, -2], [7, 0, -7], [0, 0, 7], [6, 0, 3],
    ]
    const lanternPositionsOuter = [
      [-12, 0, 0], [12, 0, 0], [0, 0, -12], [0, 0, 12],
      [-20, 0, -10], [20, 0, -10], [-10, 0, 20], [10, 0, 20],
    ]
    const lanternPositionsFull = isMobile
      ? lanternPositions
      : [...lanternPositions, [-7, 0, 6], [10, 0, -6], ...lanternPositionsOuter]

    // Model cache for cloning (avoids loading each file multiple times)
    const modelCache = new Map()

    /**
     * Load a single GLB, cache it, then return a clone.
     */
    function _loadAsset(assetKey) {
      if (modelCache.has(assetKey)) {
        return Promise.resolve(modelCache.get(assetKey).scene.clone())
      }

      return new Promise((resolve) => {
        gltfLoader.load(
          ENVIRONMENT_ASSETS[assetKey],
          (gltf) => {
            modelCache.set(assetKey, gltf)
            resolve(gltf.scene.clone())
          },
          undefined,
          (err) => {
            console.warn(`[Village3D] Failed to load environment asset: ${assetKey}`, err)
            resolve(null)
          },
        )
      })
    }

    /**
     * Configure shadow properties on all meshes in a model.
     */
    function _applyShadows(model) {
      model.traverse((child) => {
        if (child.isMesh) {
          child.castShadow = !isMobile
          child.receiveShadow = true
        }
      })
    }

    /**
     * Place a loaded clone into the scene at a given position/scale/rotation.
     */
    function _placeAsset(clone, x, y, z, scale, rotationY) {
      if (!clone) return
      clone.position.set(x, y, z)
      if (typeof scale === 'number') {
        clone.scale.setScalar(scale)
      }
      if (typeof rotationY === 'number') {
        clone.rotation.y = rotationY
      }
      _applyShadows(clone)
      scene.add(clone)
      environmentObjects.push(clone)
    }

    // --- Load and place all assets (non-blocking) ---
    async function _placeAllAssets() {
      if (!isInitialized.value) return

      // 1. Fountain at village square center
      const fountain = await _loadAsset('fountain')
      if (!isInitialized.value) return
      _placeAsset(fountain, 0, 0, 0, 1.5, 0)

      // 2. Fire pit offset from village square
      const firePit = await _loadAsset('fire_pit')
      if (!isInitialized.value) return
      _placeAsset(firePit, 3, 0, 2, 0.8, Math.PI * 0.25)

      // 2b. Portal arch at bridge_portal zone
      const portalArch = await _loadAsset('portal_arch')
      if (!isInitialized.value) return
      if (portalArch) {
        const bp = VILLAGE_LAYOUT.bridge_portal.pos
        _placeAsset(portalArch, bp[0], 0, bp[2], 3, Math.PI * 0.15)
      }

      // --- Helper: create InstancedMesh(es) from a GLB template ---
      // Handles multi-mesh GLBs (e.g. tree trunk + crown as separate meshes)
      function _createInstancedVegetation(template, positions, baseScale, scaleRange, offsetRange) {
        if (!template) return
        template.updateMatrixWorld(true)

        // Collect ALL meshes in the GLB (trunk, crown, leaves, etc.)
        const meshes = []
        template.traverse((child) => {
          if (child.isMesh && child.geometry) meshes.push(child)
        })
        if (meshes.length === 0) return

        // Pre-generate instance transforms (shared across all meshes in this GLB)
        const count = positions.length
        const dummy = new THREE.Object3D()
        const instanceMatrices = []
        for (let i = 0; i < count; i++) {
          const [px, py, pz] = positions[i]
          const ox = (Math.random() - 0.5) * offsetRange
          const oz = (Math.random() - 0.5) * offsetRange
          const s = baseScale + Math.random() * scaleRange
          dummy.position.set(px + ox, py, pz + oz)
          dummy.rotation.set(0, Math.random() * Math.PI * 2, 0)
          dummy.scale.setScalar(s)
          dummy.updateMatrix()
          instanceMatrices.push(dummy.matrix.clone())
        }

        // Create one InstancedMesh per GLB mesh part (trunk, crown, etc.)
        const combined = new THREE.Matrix4()
        for (const srcMesh of meshes) {
          const mat = srcMesh.material.clone()
          const instanced = new THREE.InstancedMesh(srcMesh.geometry, mat, count)
          instanced.castShadow = !isMobile
          instanced.receiveShadow = true

          const meshLocal = srcMesh.matrixWorld.clone()
          for (let i = 0; i < count; i++) {
            combined.multiplyMatrices(instanceMatrices[i], meshLocal)
            instanced.setMatrixAt(i, combined)
          }
          instanced.instanceMatrix.needsUpdate = true

          scene.add(instanced)
          instancedMeshes.push(instanced)
        }
      }

      // 3. Trees - two InstancedMesh (round + conifer), split positions evenly
      const treeRound = await _loadAsset('tree_round')
      const treeConifer = await _loadAsset('tree_conifer')
      if (!isInitialized.value) return

      const roundPositions = treePositions.filter((_, i) => i % 2 === 0)
      const coniferPositions = treePositions.filter((_, i) => i % 2 !== 0)
      _createInstancedVegetation(treeRound, roundPositions, 2.0, 1.0, 2)
      _createInstancedVegetation(treeConifer, coniferPositions, 2.0, 1.0, 2)

      // 4. Bushes - single InstancedMesh
      const bushTemplate = await _loadAsset('bush')
      if (!isInitialized.value) return
      _createInstancedVegetation(bushTemplate, bushPositionsFull, 1.0, 0.5, 1)

      // 5. Ferns - single InstancedMesh
      const fernTemplate = await _loadAsset('fern')
      if (!isInitialized.value) return
      _createInstancedVegetation(fernTemplate, fernPositionsFull, 0.5, 0.5, 0.5)

      // 6. Lanterns
      const lanternTemplate = await _loadAsset('lantern')
      if (!isInitialized.value) return

      for (let i = 0; i < lanternPositionsFull.length; i++) {
        const [lx, ly, lz] = lanternPositionsFull[i]
        if (!lanternTemplate) break
        const clone = lanternTemplate.clone()
        _placeAsset(clone, lx, ly, lz, 1.5, 0)
      }
    }

    _placeAllAssets().catch((err) => {
      console.warn('[Village3D] Environment asset loading error:', err)
    })
  }

  // =========================================================================
  // ANIMATION LOOP
  // =========================================================================

  function _animate() {
    if (!isInitialized.value) return

    animationFrameId = requestAnimationFrame(_animate)

    const dt = Math.min(clock.getDelta(), 0.1)
    elapsedTime += dt

    const scene = sceneRef.value
    const camera = cameraRef.value
    const renderer = rendererRef.value
    const controls = controlsRef.value

    if (!scene || !camera || !renderer || !controls) return

    // --- Update camera transition (orbit mode only) ---
    if (cameraTransition && !fpvMode.isFPV.value) {
      const elapsed = performance.now() - cameraTransition.startTime
      const t = Math.min(1, elapsed / cameraTransition.duration)
      const eased = 1 - Math.pow(1 - t, 3) // easeOutCubic

      camera.position.lerpVectors(cameraTransition.fromPos, cameraTransition.toPos, eased)
      controls.target.lerpVectors(cameraTransition.fromTarget, cameraTransition.toTarget, eased)

      if (t >= 1) cameraTransition = null
    }

    // --- Focus-agent mode: follow agent smoothly ---
    if (cameraMode.value === 'focus-agent' && focusTarget.value) {
      const agent = agents.get(focusTarget.value)
      if (agent) {
        const target = agent.position.clone()
        target.y = 2
        controls.target.lerp(target, 0.05)
      }
    }

    // --- Update agents ---
    for (const agent of agents.values()) {
      _updateAgent(agent, dt, elapsedTime)
    }

    // --- Update visitors (same walking logic, ghost pulse) ---
    for (const visitor of visitors.values()) {
      _updateAgent(visitor, dt, elapsedTime)
      // Ghost pulse effect
      if (visitor.mesh.material) {
        visitor.mesh.material.opacity = 0.35 + Math.sin(elapsedTime * 2 + visitor.color.r * 10) * 0.15
      }
      if (visitor.glowRing) {
        visitor.glowRing.material.opacity = 0.2 + Math.sin(elapsedTime * 3) * 0.1
      }
    }

    // --- Update zone glow rings ---
    for (const [name, ring] of zoneGlowRings.entries()) {
      if (name === activeZone.value) {
        ring.material.opacity = 0.5 + Math.sin(elapsedTime * 3) * 0.2
        ring.rotation.z = elapsedTime * 0.5
      } else {
        ring.material.opacity = 0.3
      }
    }

    // --- Update shattering padlocks (G3) ---
    for (const [zoneName, padlock] of zonePadlockSprites.entries()) {
      if (padlock.userData?.shattering) {
        const elapsed = (performance.now() - padlock.userData.shatterStart) / 1000
        const t = Math.min(1, elapsed / 0.5)
        padlock.scale.setScalar(1.2 * (1 - t))
        padlock.material.opacity = 1 - t
        if (t >= 1) {
          const group = zoneGroups.get(zoneName)
          if (group) group.remove(padlock)
          padlock.material.map?.dispose()
          padlock.material.dispose()
          zonePadlockSprites.delete(zoneName)
        }
      }
    }

    // --- Update particles ---
    if (particleSystem) particleSystem.update(dt)

    // --- Update speech bubbles ---
    for (let i = speechBubbles.length - 1; i >= 0; i--) {
      const bubble = speechBubbles[i]
      const agent = agents.get(bubble.agentId)
      const agentPos = agent ? agent.group.position : null
      if (!bubble.update(dt, agentPos)) {
        bubble.dispose()
        speechBubbles.splice(i, 1)
      }
    }

    // --- Update fireflies ---
    if (fireflySystem) fireflySystem.update(elapsedTime)

    // --- Update day/night cycle (Phase 12) ---
    const dayNightResult = dayNight.update(dt)
    if (fireflySystem && dayNightResult.fireflyMultiplier !== undefined) {
      fireflySystem.setOpacityMultiplier(dayNightResult.fireflyMultiplier)
    }

    // --- Update pedestal (H4) ---
    _updatePedestal(dt, elapsedTime)

    // --- Render ---
    if (fpvMode.isFPV.value) {
      // FPV mode: PointerLockControls handles camera rotation, we handle movement
      fpvMode.update(dt)
      // Phase 10: Proximity detection + streaming bubble + soft-lock
      fpvInteraction.updateProximity()
      fpvInteraction.updateBubbleScreenPos()
      fpvInteraction.applySoftLock(dt)
    } else {
      // Orbit mode: standard OrbitControls
      controls.update()
      // Clamp pan target to map bounds (160x160 → +-70 with margin)
      const t = controls.target
      const panLimit = 65
      t.x = Math.max(-panLimit, Math.min(panLimit, t.x))
      t.z = Math.max(-panLimit, Math.min(panLimit, t.z))

      // --- Update district tracking (Phase 2) ---
      const districtResult = districtManager.update(t.x, t.z)
      if (districtResult.changed) {
        onDistrictChange?.(districtResult.district, districtResult.name, districtResult.theme)
      }
    }

    // Render with post-processing when active (FPV agent vision), else direct
    if (postProcessing.isActive.value) {
      postProcessing.render(dt)
    } else {
      renderer.render(scene, camera)
    }
  }

  // =========================================================================
  // AGENT UPDATE
  // =========================================================================

  function _updateAgent(agent, dt, time) {
    if (agent.state === 'walking' && agent.targetPosition) {
      // Move toward target
      const current = agent.group.position
      const target = agent.targetPosition
      const dx = target.x - current.x
      const dz = target.z - current.z
      const dist = Math.sqrt(dx * dx + dz * dz)

      if (dist > 0.3) {
        const step = agent.walkSpeed * dt
        const moveRatio = Math.min(step / dist, 1)
        current.x += dx * moveRatio
        current.z += dz * moveRatio

        // Face direction of movement (rotate mesh group)
        const angle = Math.atan2(dx, dz)
        agent.group.rotation.y = angle
      } else {
        // Arrived at destination
        current.x = target.x
        current.z = target.z

        if (agent.currentTool && agent.targetZone !== 'village_square') {
          agent.state = 'working'
        } else {
          agent.state = 'idle'
          agent.targetPosition = null
          agent.targetZone = null
        }
      }
    }

    if (agent.state === 'working') {
      agent.workPulse += dt
      // Pulse glow ring
      agent.glowRing.material.opacity = Math.sin(agent.workPulse * 4) * 0.3 + 0.5

      // Pulse mesh emissive (if still using sphere)
      if (agent.mesh.material && agent.mesh.material.emissiveIntensity !== undefined) {
        agent.mesh.material.emissiveIntensity = 0.4 + Math.sin(agent.workPulse * 4) * 0.3
      }
    } else {
      // Hide glow ring when not working (unless leveled agent has idle glow)
      agent.glowRing.material.opacity = agent.idleGlowBase || 0
    }

    if (agent.state === 'idle') {
      // Bob the main mesh subtly
      if (agent.mesh) {
        const baseY = agent.glbSwapped ? 0 : 0.8
        agent.mesh.position.y = baseY + Math.sin(time * 1.5 + agents.size) * 0.05
      }
    }

    // Selection ring (independent of work state)
    if (agent.selectionRing) {
      const isSelected = selectedSceneAgents.value.includes(agent.id)
      if (isSelected) {
        agent.selectionRing.material.opacity = 0.6 + Math.sin(time * 2.5) * 0.3
        agent.selectionRing.rotation.z = time * 0.8
      } else {
        agent.selectionRing.material.opacity = 0
      }
    }

    // Update name sprite position to be above agent
    if (agent.nameSprite) {
      const spriteY = agent.glbSwapped ? 3.0 : 2.2
      agent.nameSprite.position.y = spriteY
    }
  }

  // =========================================================================
  // TOOL EVENT HANDLERS
  // =========================================================================

  function handleToolStart(agentId, toolName, zoneName) {
    agentAutonomy.pauseAgent(agentId)
    const agent = _ensureAgent(agentId)
    if (!agent) return

    agent.targetZone = zoneName
    agent.currentTool = toolName
    agent.state = 'walking'
    agent.workPulse = 0

    const zone = VILLAGE_LAYOUT[zoneName]
    if (zone) {
      agent.targetPosition = new THREE.Vector3(zone.pos[0], 0, zone.pos[2])
    }

    activeZone.value = zoneName

    // Brighten zone glow ring
    const ring = zoneGlowRings.get(zoneName)
    if (ring) {
      ring.material.opacity = 0.7
    }
  }

  function handleToolComplete(agentId, toolName, zoneName, success = true) {
    const agent = agents.get(agentId)
    if (!agent) return

    // Particle burst at agent position
    const burstPos = agent.group.position.clone()
    burstPos.y = 1.5
    if (particleSystem) {
      const burstColor = success ? 0x66bb6a : 0xef5350
      const burstCount = success ? 20 : 15
      particleSystem.emit(burstPos, burstColor, burstCount)
    }

    // Walk back to village square
    agent.state = 'walking'
    agent.targetZone = 'village_square'
    agent.currentTool = null
    const square = VILLAGE_LAYOUT.village_square
    agent.targetPosition = new THREE.Vector3(square.pos[0], 0, square.pos[2])

    // Clear active zone after a short delay
    const tid = setTimeout(() => {
      activeZone.value = null
    }, 500)
    pendingTimeouts.push(tid)

    agentAutonomy.resumeAgent(agentId)
  }

  function handleToolError(agentId, toolName, zoneName) {
    handleToolComplete(agentId, toolName, zoneName, false)
  }

  function _ensureAgent(agentId) {
    if (agents.has(agentId)) return agents.get(agentId)

    // Create agent on-the-fly if one arrives via WebSocket that wasn't pre-created
    const scene = sceneRef.value
    if (!scene) return null

    const colorHex = AGENT_COLORS[agentId] || AGENT_COLORS.default
    const color = new THREE.Color(colorHex)

    const group = new THREE.Group()
    group.userData = { type: 'agent', id: agentId }

    const sphereGeo = new THREE.IcosahedronGeometry(0.6, 2)
    const sphereMat = new THREE.MeshStandardMaterial({
      color,
      emissive: color,
      emissiveIntensity: 0.5,
      roughness: 0.3,
      metalness: 0.4,
    })
    const sphere = new THREE.Mesh(sphereGeo, sphereMat)
    sphere.position.y = 0.8
    sphere.castShadow = !isMobile
    group.add(sphere)

    const glowGeo = new THREE.TorusGeometry(0.8, 0.05, 8, 24)
    const glowMat = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: 0,
    })
    const glowRing = new THREE.Mesh(glowGeo, glowMat)
    glowRing.rotation.x = -Math.PI / 2
    glowRing.position.y = 0.05
    group.add(glowRing)

    const selGeo = new THREE.TorusGeometry(1.1, 0.06, 8, 32)
    const selMat = new THREE.MeshBasicMaterial({
      color: 0xffd700,
      transparent: true,
      opacity: 0,
    })
    const selectionRing = new THREE.Mesh(selGeo, selMat)
    selectionRing.rotation.x = -Math.PI / 2
    selectionRing.position.y = 0.03
    group.add(selectionRing)

    const nameSprite = _createAgentNameSprite(agentId)
    nameSprite.position.y = 2.2
    group.add(nameSprite)

    const squarePos = VILLAGE_LAYOUT.village_square.pos
    group.position.set(squarePos[0], 0, squarePos[2])
    scene.add(group)

    const agent = {
      id: agentId,
      group,
      mesh: sphere,
      glowRing,
      selectionRing,
      nameSprite,
      position: group.position,
      targetPosition: null,
      state: 'idle',
      currentZone: 'village_square',
      targetZone: null,
      currentTool: null,
      walkSpeed: 8,
      workPulse: 0,
      colorHex,
      color,
      glbSwapped: false,
      idleGlowBase: 0,
    }

    agents.set(agentId, agent)

    // Try to swap in GLB if models are loaded
    if (agentModels.isLoaded(agentId)) {
      const clone = agentModels.getAgentClone(agentId, 2.5)
      if (clone) {
        group.remove(sphere)
        sphere.geometry.dispose()
        sphere.material.dispose()
        clone.position.y = 0
        clone.traverse((child) => {
          if (child.isMesh) child.castShadow = !isMobile
        })
        group.add(clone)
        agent.mesh = clone
        agent.glbSwapped = true
      }
    }

    return agent
  }

  // =========================================================================
  // SPEECH BUBBLES
  // =========================================================================

  function showBubble(agentId, message, type = 'info', duration) {
    const agent = agents.get(agentId)
    if (!agent) return null

    // Remove existing bubble for this agent
    _dismissBubble(agentId)

    const bubble = new SpeechBubble(
      sceneRef.value,
      agent.group.position,
      message,
      type,
    )
    bubble.agentId = agentId
    if (duration) bubble.maxAge = duration
    speechBubbles.push(bubble)

    return bubble
  }

  function _dismissBubble(agentId) {
    const idx = speechBubbles.findIndex((b) => b.agentId === agentId)
    if (idx !== -1) {
      speechBubbles[idx].dismiss()
    }
  }

  // =========================================================================
  // CAMERA
  // =========================================================================

  function _startCameraTransition(toPos, toTarget, durationSec) {
    const camera = cameraRef.value
    const controls = controlsRef.value
    if (!camera || !controls) return

    cameraTransition = {
      fromPos: camera.position.clone(),
      fromTarget: controls.target.clone(),
      toPos,
      toTarget,
      startTime: performance.now(),
      duration: durationSec * 1000,
    }
  }

  function focusOnZone(zoneName) {
    const zone = VILLAGE_LAYOUT[zoneName]
    if (!zone) return

    const target = new THREE.Vector3(zone.pos[0], 2, zone.pos[2])
    const offset = new THREE.Vector3(6, 5, 6)
    _startCameraTransition(target.clone().add(offset), target, 0.8)
    cameraMode.value = 'focus-zone'
    focusTarget.value = zoneName
  }

  function focusOnAgent(agentId) {
    const agent = agents.get(agentId)
    if (!agent) return

    const target = agent.group.position.clone()
    target.y = 2
    const offset = new THREE.Vector3(5, 4, 5)
    _startCameraTransition(target.clone().add(offset), target, 0.8)

    cameraMode.value = 'focus-agent'
    focusTarget.value = agentId
  }

  function returnToOverview() {
    _startCameraTransition(ORBIT_POSITION.clone(), ORBIT_TARGET.clone(), 0.8)
    cameraMode.value = 'orbit'
    focusTarget.value = null
  }

  // =========================================================================
  // INTERACTION (Click / Hover)
  // =========================================================================

  function _updateMouse(event) {
    const renderer = rendererRef.value
    if (!renderer) return
    const rect = renderer.domElement.getBoundingClientRect()
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
  }

  function _getIntersections() {
    const camera = cameraRef.value
    if (!camera) return []

    raycaster.setFromCamera(mouse, camera)

    const targets = []
    // Agent groups
    for (const agent of agents.values()) {
      targets.push(agent.group)
    }
    // Zone groups
    for (const group of zoneGroups.values()) {
      targets.push(group)
    }
    // Pedestal (H4)
    if (pedestalGroup) targets.push(pedestalGroup)

    return raycaster.intersectObjects(targets, true)
  }

  function _findUserData(intersections) {
    if (intersections.length === 0) return null

    let hit = intersections[0].object
    // Walk up parent chain to find an object with userData.type
    while (hit && !hit.userData?.type) {
      hit = hit.parent
    }
    return hit?.userData || null
  }

  function _handleClick(event) {
    // G3: Skip ceremony on click
    if (ceremonyActive) {
      _skipCurrentCeremony()
      return
    }

    _updateMouse(event)
    const intersections = _getIntersections()
    const userData = _findUserData(intersections)

    if (!userData) {
      selectedAgent.value = null
      return
    }

    if (userData.type === 'agent') {
      selectedAgent.value = userData.id

      // Toggle scene selection (gold ring)
      const idx = selectedSceneAgents.value.indexOf(userData.id)
      if (idx > -1) {
        selectedSceneAgents.value.splice(idx, 1)
      } else {
        selectedSceneAgents.value.push(userData.id)
      }

      onAgentClick?.(userData.id, agents.get(userData.id))
    } else if (userData.type === 'pedestal') {
      onPedestalClick?.()
    } else if (userData.type === 'zone') {
      // Portal arch intercept — bridge_portal opens portal panel
      if (userData.name === 'bridge_portal' && onPortalClick) {
        onPortalClick()
      } else {
        onZoneClick?.(userData.name, VILLAGE_LAYOUT[userData.name]?.label)
      }
    }
  }

  function _handleDblClick(event) {
    _updateMouse(event)
    const intersections = _getIntersections()
    const userData = _findUserData(intersections)

    if (!userData) {
      // Double-click on empty space -> return to overview
      returnToOverview()
      return
    }

    if (userData.type === 'agent') {
      focusOnAgent(userData.id)
    } else if (userData.type === 'zone') {
      focusOnZone(userData.name)
    }
  }

  function _handleMouseMove(event) {
    _updateMouse(event)
    const intersections = _getIntersections()
    const userData = _findUserData(intersections)
    const renderer = rendererRef.value

    if (userData && (userData.type === 'agent' || userData.type === 'zone')) {
      hoveredObject.value = userData
      if (renderer) renderer.domElement.style.cursor = 'pointer'
    } else {
      hoveredObject.value = null
      if (renderer) renderer.domElement.style.cursor = 'default'
    }
  }

  // =========================================================================
  // RESIZE
  // =========================================================================

  function _handleResize() {
    if (!containerRef.value) return
    const camera = cameraRef.value
    const renderer = rendererRef.value
    if (!camera || !renderer) return

    const width = containerRef.value.clientWidth
    const height = containerRef.value.clientHeight
    if (width === 0 || height === 0) return

    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
    postProcessing.resize(width, height)
  }

  // =========================================================================
  // LAYOUT PERSISTENCE
  // =========================================================================

  function resetLayout() {
    resetDraggableLayout()
    for (const [name, defPos] of Object.entries(defaultPositions)) {
      VILLAGE_LAYOUT[name].pos = [...defPos]
      const group = zoneGroups.get(name)
      if (group) {
        group.position.set(defPos[0], 0, defPos[2])
      }
    }
  }

  // =========================================================================
  // DISPOSE
  // =========================================================================

  function dispose() {
    isInitialized.value = false

    // Dispose FPV + post-processing (Phase 9) + interaction (Phase 10)
    fpvInteraction.dispose()
    fpvMode.dispose()
    postProcessing.dispose()
    agentAutonomy.dispose()
    dayNight.dispose()

    // Cancel animation
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId)
      animationFrameId = null
    }

    // Cancel pending timeouts
    for (const tid of pendingTimeouts) {
      clearTimeout(tid)
    }
    pendingTimeouts.length = 0

    // Remove event listeners
    const renderer = rendererRef.value
    if (renderer?.domElement) {
      renderer.domElement.removeEventListener('click', _handleClick)
      renderer.domElement.removeEventListener('dblclick', _handleDblClick)
      renderer.domElement.removeEventListener('mousemove', _handleMouseMove)
    }
    window.removeEventListener('resize', _handleResize)

    // Dispose speech bubbles
    for (const bubble of speechBubbles) {
      bubble.dispose()
    }
    speechBubbles.length = 0

    // Dispose particles
    if (particleSystem) {
      particleSystem.dispose()
      particleSystem = null
    }

    // Dispose fireflies
    if (fireflySystem) {
      fireflySystem.dispose()
      fireflySystem = null
    }

    // Dispose pedestal (H4)
    if (pedestalGroup) {
      sceneRef.value?.remove(pedestalGroup)
      pedestalGroup.traverse((child) => {
        if (child.geometry) child.geometry.dispose()
        if (child.material) {
          if (child.material.map) child.material.map.dispose()
          child.material.dispose()
        }
      })
      pedestalGroup = null
      pedestalStageElements = null
      pedestalOrbitParticles = null
      pedestalLight = null
      pedestalStage = null
    }

    // Dispose district boundary objects (Phase 2)
    for (const obj of districtBoundaryObjects) {
      sceneRef.value?.remove(obj)
      if (obj.geometry) obj.geometry.dispose()
      if (obj.material) obj.material.dispose()
    }
    districtBoundaryObjects.length = 0

    // Dispose environment assets (fountain, trees, bushes, etc.)
    for (const obj of environmentObjects) {
      sceneRef.value?.remove(obj)
      obj.traverse((child) => {
        if (child.geometry) child.geometry.dispose()
        if (child.material) {
          if (child.material.map) child.material.map.dispose()
          if (Array.isArray(child.material)) {
            child.material.forEach((m) => {
              if (m.map) m.map.dispose()
              m.dispose()
            })
          } else {
            child.material.dispose()
          }
        }
      })
    }
    environmentObjects.length = 0

    // Dispose instanced vegetation meshes (Phase 0A)
    for (const im of instancedMeshes) {
      sceneRef.value?.remove(im)
      im.geometry.dispose()
      if (Array.isArray(im.material)) {
        im.material.forEach((m) => m.dispose())
      } else {
        im.material.dispose()
      }
    }
    instancedMeshes.length = 0

    // Dispose agents
    for (const agent of agents.values()) {
      if (agent.group) {
        sceneRef.value?.remove(agent.group)
      }
      agent.group.traverse((obj) => {
        if (obj.geometry) obj.geometry.dispose()
        if (obj.material) {
          if (obj.material.map) obj.material.map.dispose()
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => {
              if (m.map) m.map.dispose()
              m.dispose()
            })
          } else {
            obj.material.dispose()
          }
        }
      })
    }
    agents.clear()

    // Dispose visitors
    for (const visitor of visitors.values()) {
      sceneRef.value?.remove(visitor.group)
      visitor.group.traverse((child) => {
        if (child.geometry) child.geometry.dispose()
        if (child.material) {
          if (Array.isArray(child.material)) child.material.forEach(m => m.dispose())
          else child.material.dispose()
        }
      })
    }
    visitors.clear()
    for (const tid of visitorWanderTimers) clearTimeout(tid)
    visitorWanderTimers.length = 0

    // Dispose zone groups
    for (const group of zoneGroups.values()) {
      sceneRef.value?.remove(group)
      group.traverse((obj) => {
        if (obj.geometry) obj.geometry.dispose()
        if (obj.material) {
          if (obj.material.map) obj.material.map.dispose()
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => {
              if (m.map) m.map.dispose()
              m.dispose()
            })
          } else {
            obj.material.dispose()
          }
        }
      })
    }
    zoneGroups.clear()
    zonePlaceholders.clear()
    zoneGlowRings.clear()
    zoneLabelSprites.clear()
    zonePadlockSprites.clear()
    zoneLockedState.clear()
    agentLockedState.clear()
    zoneMeshes.length = 0
    ceremonyQueue.length = 0
    ceremonyActive = false
    ceremonyCurrent = null
    ceremonyId = 0

    // Dispose the rest of the scene
    const scene = sceneRef.value
    if (scene) {
      scene.traverse((obj) => {
        if (obj.geometry) obj.geometry.dispose()
        if (obj.material) {
          if (obj.material.map) obj.material.map.dispose()
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => {
              if (m.map) m.map.dispose()
              m.dispose()
            })
          } else {
            obj.material.dispose()
          }
        }
      })
    }

    // Dispose controls
    const controls = controlsRef.value
    if (controls) {
      controls.dispose()
      controlsRef.value = null
    }

    // Dispose renderer
    if (renderer) {
      renderer.dispose()
      if (containerRef.value && renderer.domElement?.parentNode === containerRef.value) {
        containerRef.value.removeChild(renderer.domElement)
      }
      rendererRef.value = null
    }

    sceneRef.value = null
    cameraRef.value = null
    cameraTransition = null
    clock = null
    elapsedTime = 0
  }

  // =========================================================================
  // VISITOR SYSTEM (Phase 5 — Ghost agents from other villages)
  // =========================================================================

  function addVisitor(visitorId, ownerName, agentId, agentColor) {
    if (visitors.has(visitorId)) return
    const scene = sceneRef.value
    if (!scene) return

    const color = new THREE.Color(agentColor || '#a29bfe')

    const group = new THREE.Group()
    group.userData = { type: 'visitor', id: visitorId, ownerName, agentId }

    // Ghost sphere (semi-transparent, emissive tint)
    const sphereGeo = new THREE.IcosahedronGeometry(0.6, 2)
    const sphereMat = new THREE.MeshStandardMaterial({
      color,
      emissive: color,
      emissiveIntensity: 0.8,
      roughness: 0.2,
      metalness: 0.3,
      transparent: true,
      opacity: 0.5,
    })
    const sphere = new THREE.Mesh(sphereGeo, sphereMat)
    sphere.position.y = 0.8
    group.add(sphere)

    // Ghost glow ring (always visible)
    const glowGeo = new THREE.TorusGeometry(0.9, 0.04, 8, 24)
    const glowMat = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: 0.3,
    })
    const glowRing = new THREE.Mesh(glowGeo, glowMat)
    glowRing.rotation.x = -Math.PI / 2
    glowRing.position.y = 0.05
    group.add(glowRing)

    // Visitor badge sprite
    const badge = _createVisitorBadge(ownerName, agentId, agentColor)
    badge.position.y = 2.4
    group.add(badge)

    // Start at bridge_portal (where portals are)
    const portalPos = VILLAGE_LAYOUT.bridge_portal.pos
    group.position.set(portalPos[0], 0, portalPos[2])
    scene.add(group)

    const visitor = {
      id: visitorId,
      group,
      mesh: sphere,
      glowRing,
      nameSprite: badge,
      position: group.position,
      targetPosition: null,
      state: 'idle',
      currentZone: 'bridge_portal',
      targetZone: null,
      currentTool: null,
      walkSpeed: 4, // Gentler speed than local agents
      workPulse: 0,
      colorHex: agentColor || '#a29bfe',
      color,
      glbSwapped: false,
      idleGlowBase: 0,
    }

    visitors.set(visitorId, visitor)

    // Start auto-wander
    _startVisitorWander(visitorId)

    return visitor
  }

  function removeVisitor(visitorId) {
    const visitor = visitors.get(visitorId)
    if (!visitor) return

    const scene = sceneRef.value
    if (scene) scene.remove(visitor.group)

    // Dispose geometry/materials
    visitor.group.traverse((child) => {
      if (child.geometry) child.geometry.dispose()
      if (child.material) {
        if (Array.isArray(child.material)) child.material.forEach(m => m.dispose())
        else child.material.dispose()
      }
    })

    visitors.delete(visitorId)
  }

  function _createVisitorBadge(ownerName, agentId, colorHex) {
    const canvas = document.createElement('canvas')
    canvas.width = 256
    canvas.height = 64
    const ctx = canvas.getContext('2d')

    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)'
    ctx.roundRect(0, 0, 256, 64, 8)
    ctx.fill()

    ctx.fillStyle = colorHex || '#a29bfe'
    ctx.font = 'bold 18px monospace'
    ctx.textAlign = 'center'
    ctx.fillText(`${agentId || 'Agent'}`, 128, 24)

    ctx.fillStyle = '#aaaaaa'
    ctx.font = '14px monospace'
    ctx.fillText(`${ownerName || 'Visitor'}`, 128, 48)

    const texture = new THREE.CanvasTexture(canvas)
    const mat = new THREE.SpriteMaterial({ map: texture, transparent: true, opacity: 0.85 })
    const sprite = new THREE.Sprite(mat)
    sprite.scale.set(3, 0.75, 1)
    return sprite
  }

  function _startVisitorWander(visitorId) {
    const wander = () => {
      const visitor = visitors.get(visitorId)
      if (!visitor) return

      // Pick a random zone
      const zoneNames = Object.keys(VILLAGE_LAYOUT)
      const targetZone = zoneNames[Math.floor(Math.random() * zoneNames.length)]
      const zone = VILLAGE_LAYOUT[targetZone]

      visitor.state = 'walking'
      visitor.targetZone = targetZone
      visitor.targetPosition = new THREE.Vector3(zone.pos[0], 0, zone.pos[2])

      // Schedule next wander (15-30s)
      const delay = 15000 + Math.random() * 15000
      const tid = setTimeout(wander, delay)
      visitorWanderTimers.push(tid)
    }

    // First wander after 3-8s
    const initialDelay = 3000 + Math.random() * 5000
    const tid = setTimeout(wander, initialDelay)
    visitorWanderTimers.push(tid)
  }

  // =========================================================================
  // FPV MODE (Phase 9)
  // =========================================================================

  function enterFPV(agentId) {
    const agent = agents.get(agentId)
    if (!agent) return

    const position = agent.group.position.clone()
    fpvMode.enterFPV(position, agentId, controlsRef.value)
    postProcessing.activateProfile(agentId)

    // Clear orbit-mode UI state
    cameraMode.value = 'fpv'
    focusTarget.value = null
    cameraTransition = null
  }

  function exitFPV() {
    fpvInteraction.cancelChat()
    fpvMode.exitFPV()
    postProcessing.deactivateProfile()
    cameraMode.value = 'orbit'
  }

  // =========================================================================
  // RETURN
  // =========================================================================

  return {
    // Lifecycle
    init,
    dispose,

    // Tool event handlers
    handleToolStart,
    handleToolComplete,
    handleToolError,

    // Speech bubbles
    showBubble,

    // Agent map (for external inspection)
    agents,

    // Reactive state
    isInitialized,
    webglError,
    selectedAgent,
    selectedSceneAgents,
    hoveredObject,
    activeZone,

    // Camera
    cameraMode,
    focusTarget,
    focusOnZone,
    focusOnAgent,
    returnToOverview,

    // Layout
    hasCustomLayout,
    resetLayout,

    // Gamification (E5)
    updateAgentNameplate,
    updateZoneLabel,
    setAgentIdleGlow,
    emitAchievementBurst,

    // Quest Engine (G1)
    setZoneLocked,

    // Agent Unlock Progression (G5)
    setAgentLocked,
    isAgentLocked,

    // Unlock Ceremonies (G3)
    playUnlockCeremony,
    skipCeremony,

    // Grand Prize Pedestal (H4)
    evolvePedestal,

    // Visitor System (Phase 5)
    addVisitor,
    removeVisitor,
    visitors,

    // District System (Phase 2)
    districtManager,

    // FPV Mode (Phase 9)
    enterFPV,
    exitFPV,
    isFPV: fpvMode.isFPV,
    fpvAgent: fpvMode.currentAgent,
    postProcessing,

    // FPV Interaction (Phase 10)
    fpvInteraction,

    // Day/Night Cycle (Phase 12)
    dayNight,

    // Agent Autonomy (Phase 15)
    agentAutonomy,

    // Internal refs (for advanced use / debugging)
    scene: sceneRef,
    camera: cameraRef,
    renderer: rendererRef,
    controls: controlsRef,

    // Start animation (call after init)
    startAnimation() {
      if (isInitialized.value && !animationFrameId) {
        _animate()
      }
    },
  }
}
