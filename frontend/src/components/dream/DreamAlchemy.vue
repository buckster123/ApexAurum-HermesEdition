<script setup>
/**
 * DreamAlchemy — 3D Dream Phase Pipeline
 *
 * Six glowing alchemical orbs connected by energy conduits.
 * Active phase pulses and energy flows forward through the pipeline.
 * Agent avatars float in the background void.
 *
 * "The Athanor dreams in six phases. Each a transmutation."
 */

import { ref, shallowRef, watch, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { useAgentModels } from '@/composables/useAgentModels'

const props = defineProps({
  activePhase: {
    type: Number,
    default: -1, // -1 = idle (no phase active)
  },
  isRunning: {
    type: Boolean,
    default: false,
  },
})

const containerRef = ref(null)
const webglFailed = ref(false)

// Phase definitions matching DreamView
const PHASES = [
  { key: 'sws_replay', name: 'Aqua Regia', color: '#4FC3F7' },
  { key: 'pattern_extract', name: 'Viriditas', color: '#66BB6A' },
  { key: 'schema_form', name: 'Chrysopoeia', color: '#FFD700' },
  { key: 'emotional_reprocess', name: 'Rubedo', color: '#EF5350' },
  { key: 'pruning', name: 'Nigredo', color: '#9E9E9E' },
  { key: 'rem_recombine', name: 'Conjunctio', color: '#AB47BC' },
]

const AGENT_IDS = ['AZOTH', 'ELYSIAN', 'VAJRA', 'KETHER']

// Three.js state
let renderer = null
let scene = null
let camera = null
let animId = null
let clock = null
let orbs = []        // phase orb meshes
let wireframes = []  // wireframe overlays
let conduits = []    // energy tube meshes between orbs
let agentMeshes = [] // background floating agents
let resizeObserver = null

const agentModels = useAgentModels()

const ORB_SPACING = 6
const ORB_Y = 0
const isMobileDevice = typeof navigator !== 'undefined'
  && (/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
    || (navigator.maxTouchPoints > 0 && !window.matchMedia?.('(pointer: fine)')?.matches))

function initScene() {
  if (!containerRef.value) return false

  try {
    const canvas = document.createElement('canvas')
    if (!canvas.getContext('webgl') && !canvas.getContext('experimental-webgl')) { webglFailed.value = true; return false }
  } catch { webglFailed.value = true; return false }

  const el = containerRef.value
  const w = el.clientWidth
  const h = el.clientHeight
  if (w === 0 || h === 0) return false

  try {
    scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0a0612)
    scene.fog = new THREE.FogExp2(0x0a0612, 0.025)

    // Camera looks at center of the 6-orb pipeline
    const centerX = (PHASES.length - 1) * ORB_SPACING / 2
    camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 200)
    camera.position.set(centerX, 3, 22)
    camera.lookAt(centerX, ORB_Y, 0)

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    renderer.setSize(w, h)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    el.appendChild(renderer.domElement)

    // Lighting
    const ambient = new THREE.AmbientLight(0x1a1020, 0.4)
    scene.add(ambient)

    // Central warm light
    const warmLight = new THREE.PointLight(0xffd700, 0.6, 60)
    warmLight.position.set(centerX, 5, 5)
    scene.add(warmLight)

    // Subtle grid floor
    const gridHelper = new THREE.GridHelper(80, 30, 0x1a1a2e, 0x0f0f1a)
    gridHelper.position.y = -3
    scene.add(gridHelper)

    clock = new THREE.Clock()

    buildOrbs()
    buildConduits()
    buildAgents()

    // Resize handling
    resizeObserver = new ResizeObserver(() => handleResize())
    resizeObserver.observe(el)

    return true
  } catch {
    return false
  }
}

function buildOrbs() {
  orbs = []
  wireframes = []

  PHASES.forEach((phase, i) => {
    const x = i * ORB_SPACING
    const color = new THREE.Color(phase.color)

    // Solid icosahedron core
    const geo = new THREE.IcosahedronGeometry(1, 2)
    const mat = new THREE.MeshStandardMaterial({
      color: color,
      emissive: color,
      emissiveIntensity: 0.3,
      metalness: 0.4,
      roughness: 0.3,
      transparent: true,
      opacity: 0.85,
    })
    const orb = new THREE.Mesh(geo, mat)
    orb.position.set(x, ORB_Y, 0)
    scene.add(orb)
    orbs.push(orb)

    // Wireframe overlay (larger, rotating opposite)
    const wireGeo = new THREE.IcosahedronGeometry(1.3, 1)
    const wireMat = new THREE.MeshBasicMaterial({
      color: color,
      wireframe: true,
      transparent: true,
      opacity: 0.15,
    })
    const wire = new THREE.Mesh(wireGeo, wireMat)
    wire.position.set(x, ORB_Y, 0)
    scene.add(wire)
    wireframes.push(wire)

    // Point light at each orb
    const orbLight = new THREE.PointLight(color, 0.3, 8)
    orbLight.position.set(x, ORB_Y, 0)
    scene.add(orbLight)
  })
}

function buildConduits() {
  conduits = []

  for (let i = 0; i < PHASES.length - 1; i++) {
    const x1 = i * ORB_SPACING + 1.4
    const x2 = (i + 1) * ORB_SPACING - 1.4

    // Create tube between orbs
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(x1, ORB_Y, 0),
      new THREE.Vector3((x1 + x2) / 2, ORB_Y + 0.3, 0),
      new THREE.Vector3(x2, ORB_Y, 0),
    ])

    const tubeGeo = new THREE.TubeGeometry(curve, 16, 0.06, 6, false)
    const fromColor = new THREE.Color(PHASES[i].color)
    const toColor = new THREE.Color(PHASES[i + 1].color)
    const midColor = fromColor.clone().lerp(toColor, 0.5)

    const tubeMat = new THREE.MeshBasicMaterial({
      color: midColor,
      transparent: true,
      opacity: 0.25,
    })

    const tube = new THREE.Mesh(tubeGeo, tubeMat)
    scene.add(tube)
    conduits.push(tube)
  }
}

function buildAgents() {
  agentMeshes = []
  // Skip decorative background agents on mobile — they float far above the pipeline
  if (isMobileDevice) return

  AGENT_IDS.forEach((agentId, i) => {
    let mesh

    if (agentModels.isLoaded(agentId)) {
      mesh = agentModels.getAgentClone(agentId, 1.5)
    }

    if (!mesh) {
      // Fallback: small colored sphere
      const colors = {
        AZOTH: 0xd4af37,
        ELYSIAN: 0xe8b4ff,
        VAJRA: 0x4fc3f7,
        KETHER: 0xab47bc,
      }
      const geo = new THREE.SphereGeometry(0.4, 12, 12)
      const mat = new THREE.MeshStandardMaterial({
        color: colors[agentId] || 0x888888,
        emissive: colors[agentId] || 0x888888,
        emissiveIntensity: 0.3,
        transparent: true,
        opacity: 0.6,
      })
      mesh = new THREE.Mesh(geo, mat)
    }

    // Position agents floating above the pipeline
    const centerX = (PHASES.length - 1) * ORB_SPACING / 2
    const angle = (i / AGENT_IDS.length) * Math.PI * 2
    const radius = 8
    mesh.position.set(
      centerX + Math.cos(angle) * radius,
      4 + Math.sin(angle * 2) * 1.5,
      -5 + Math.sin(angle) * 3
    )

    mesh.userData = { agentIndex: i, baseY: mesh.position.y }
    scene.add(mesh)
    agentMeshes.push(mesh)
  })
}

function animate() {
  animId = requestAnimationFrame(animate)
  if (!renderer || !scene || !camera) return

  const t = clock.getElapsedTime()

  // Animate orbs
  orbs.forEach((orb, i) => {
    const isActive = props.isRunning && i === props.activePhase
    const isPast = props.isRunning && i < props.activePhase

    // Target emissive intensity
    const targetIntensity = isActive ? 1.5 : (isPast ? 0.5 : 0.3)
    const currentIntensity = orb.material.emissiveIntensity
    orb.material.emissiveIntensity += (targetIntensity - currentIntensity) * 0.05

    // Active phase pulses scale
    if (isActive) {
      const pulse = 1.0 + Math.sin(t * 4) * 0.15
      orb.scale.setScalar(pulse)
    } else {
      orb.scale.lerp(new THREE.Vector3(1, 1, 1), 0.05)
    }

    // Idle gentle bob
    orb.position.y = ORB_Y + Math.sin(t * 0.8 + i * 0.7) * 0.15
  })

  // Animate wireframe overlays
  wireframes.forEach((wire, i) => {
    wire.rotation.y = t * 0.3 + i * 1.0
    wire.rotation.x = Math.sin(t * 0.2 + i) * 0.2
    wire.position.y = orbs[i].position.y

    const isActive = props.isRunning && i === props.activePhase
    wire.material.opacity = isActive ? 0.3 + Math.sin(t * 3) * 0.1 : 0.15
  })

  // Animate conduits
  conduits.forEach((tube, i) => {
    const isFlowing = props.isRunning && i < props.activePhase
    const isActive = props.isRunning && i === props.activePhase - 1

    const targetOpacity = isActive ? 0.6 : (isFlowing ? 0.4 : 0.2)
    tube.material.opacity += (targetOpacity - tube.material.opacity) * 0.05
  })

  // Animate background agents
  agentMeshes.forEach((mesh, i) => {
    const baseY = mesh.userData.baseY
    mesh.position.y = baseY + Math.sin(t * 0.5 + i * 1.5) * 0.5
    mesh.rotation.y = t * 0.2 + i * Math.PI / 2
  })

  renderer.render(scene, camera)
}

function handleResize() {
  if (!containerRef.value || !camera || !renderer) return
  const w = containerRef.value.clientWidth
  const h = containerRef.value.clientHeight
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
}

function dispose() {
  if (animId) cancelAnimationFrame(animId)
  if (resizeObserver) resizeObserver.disconnect()

  if (scene) {
    scene.traverse(obj => {
      if (obj.geometry) obj.geometry.dispose()
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose())
        else obj.material.dispose()
      }
    })
  }
  if (renderer) {
    renderer.dispose()
    if (containerRef.value && renderer.domElement) {
      containerRef.value.removeChild(renderer.domElement)
    }
  }

  renderer = null
  scene = null
  camera = null
  orbs = []
  wireframes = []
  conduits = []
  agentMeshes = []
}

// Watch for active phase changes — flash effect
watch(() => props.activePhase, (newPhase, oldPhase) => {
  if (newPhase >= 0 && newPhase < orbs.length && newPhase !== oldPhase) {
    // Brief flash on the new active orb
    const orb = orbs[newPhase]
    if (orb) {
      orb.material.emissiveIntensity = 2.5
    }
  }
})

onMounted(() => {
  // Preload agent models (non-blocking) — skip on mobile where agents are hidden
  if (!isMobileDevice) {
    agentModels.preloadAll().then(() => {
      if (scene) {
        agentMeshes.forEach(m => scene.remove(m))
        buildAgents()
      }
    })
  }

  if (initScene()) animate()
})

onUnmounted(() => {
  dispose()
  if (!isMobileDevice) agentModels.disposeAll()
})
</script>

<template>
  <div
    ref="containerRef"
    class="dream-alchemy w-full relative overflow-hidden rounded-lg border border-apex-border"
    style="height: 250px"
  >
    <!-- WebGL fallback: CSS phase dots -->
    <div v-if="webglFailed" class="absolute inset-0 flex items-center justify-center gap-3 bg-gradient-to-b from-[#0a0612] to-[#080810]">
      <div
        v-for="(phase, i) in PHASES"
        :key="phase.key"
        class="w-6 h-6 rounded-full transition-all duration-300"
        :class="{ 'scale-125': isRunning && i === activePhase }"
        :style="{
          backgroundColor: phase.color + (isRunning && i === activePhase ? '' : '60'),
          boxShadow: isRunning && i === activePhase ? '0 0 16px ' + phase.color : 'none',
        }"
      />
    </div>

    <!-- Phase label overlay -->
    <div
      v-if="isRunning && activePhase >= 0 && activePhase < PHASES.length"
      class="absolute top-3 left-1/2 -translate-x-1/2 z-10 pointer-events-none"
    >
      <span
        class="text-xs px-3 py-1 rounded-full bg-black/60 backdrop-blur border font-medium"
        :style="{
          borderColor: PHASES[activePhase].color + '60',
          color: PHASES[activePhase].color,
          textShadow: `0 0 8px ${PHASES[activePhase].color}`,
        }"
      >
        {{ PHASES[activePhase].name }}
      </span>
    </div>

    <!-- Idle hint -->
    <div
      v-if="!isRunning"
      class="absolute bottom-3 left-1/2 -translate-x-1/2 z-10 pointer-events-none"
    >
      <span class="text-[10px] text-gray-600 bg-black/40 px-3 py-1 rounded-full backdrop-blur">
        Awaiting dream cycle...
      </span>
    </div>
  </div>
</template>

<style scoped>
.dream-alchemy {
  background: radial-gradient(ellipse at center, #0a0612 0%, #080810 100%);
}
</style>
