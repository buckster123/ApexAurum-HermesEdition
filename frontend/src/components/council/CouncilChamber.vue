<script setup>
/**
 * CouncilChamber — 3D Deliberation Scene
 *
 * Circular stone table, four agent avatars seated around it,
 * ambient candlelight. Speaking agent glows brighter.
 * Static camera (no orbit controls) — pure spectacle.
 *
 * "The Council convenes. Four minds, one flame."
 */

import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { useAgentModels } from '@/composables/useAgentModels'

const props = defineProps({
  activeAgent: {
    type: String,
    default: null, // agent ID currently speaking
  },
  round: {
    type: Number,
    default: 0,
  },
})

const containerRef = ref(null)

const AGENTS = [
  { id: 'AZOTH', color: 0xd4af37, angle: 0 },
  { id: 'ELYSIAN', color: 0xe8b4ff, angle: Math.PI / 2 },
  { id: 'VAJRA', color: 0x4fc3f7, angle: Math.PI },
  { id: 'KETHER', color: 0xab47bc, angle: Math.PI * 1.5 },
]

let renderer = null
let scene = null
let camera = null
let animId = null
let clock = null
let resizeObserver = null

let table = null
let agentMeshes = {} // id -> mesh
let candles = []
let roundFlashTime = 0 // timestamp of last round flash

const agentModels = useAgentModels()

function initScene() {
  if (!containerRef.value) return false

  try {
    const canvas = document.createElement('canvas')
    if (!canvas.getContext('webgl') && !canvas.getContext('experimental-webgl')) return false
  } catch { return false }

  const el = containerRef.value
  const w = el.clientWidth
  const h = el.clientHeight
  if (w === 0 || h === 0) return false

  try {
    scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0a0810)
    scene.fog = new THREE.FogExp2(0x0a0810, 0.06)

    // Fixed overhead angle, slightly tilted
    camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 100)
    camera.position.set(0, 5, 6)
    camera.lookAt(0, 0, 0)

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    renderer.setSize(w, h)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    el.appendChild(renderer.domElement)

    // Very dim ambient
    const ambient = new THREE.AmbientLight(0x1a1020, 0.3)
    scene.add(ambient)

    clock = new THREE.Clock()

    buildFloor()
    buildTable()
    buildCandles()
    buildAgents()

    resizeObserver = new ResizeObserver(() => handleResize())
    resizeObserver.observe(el)

    return true
  } catch {
    return false
  }
}

function buildFloor() {
  const geo = new THREE.CircleGeometry(5, 32)
  const mat = new THREE.MeshStandardMaterial({
    color: 0x1a1515,
    metalness: 0.1,
    roughness: 0.9,
  })
  const floor = new THREE.Mesh(geo, mat)
  floor.rotation.x = -Math.PI / 2
  floor.position.y = -0.5
  scene.add(floor)
}

function buildTable() {
  // Circular stone table
  const topGeo = new THREE.CylinderGeometry(1.8, 1.8, 0.15, 24)
  const topMat = new THREE.MeshStandardMaterial({
    color: 0x3a3030,
    metalness: 0.2,
    roughness: 0.7,
    emissive: 0x0a0500,
    emissiveIntensity: 0.1,
  })
  table = new THREE.Mesh(topGeo, topMat)
  table.position.y = 0
  scene.add(table)

  // Table pedestal
  const pedGeo = new THREE.CylinderGeometry(0.4, 0.6, 0.5, 8)
  const ped = new THREE.Mesh(pedGeo, topMat)
  ped.position.y = -0.3
  scene.add(ped)

  // Gold rim on table
  const rimGeo = new THREE.TorusGeometry(1.8, 0.03, 8, 48)
  const rimMat = new THREE.MeshStandardMaterial({
    color: 0xd4af37,
    emissive: 0xffd700,
    emissiveIntensity: 0.2,
    metalness: 0.9,
    roughness: 0.1,
  })
  const rim = new THREE.Mesh(rimGeo, rimMat)
  rim.position.y = 0.08
  rim.rotation.x = Math.PI / 2
  scene.add(rim)

  // Center symbol — small glowing Au disc
  const symbolGeo = new THREE.CircleGeometry(0.3, 16)
  const symbolMat = new THREE.MeshBasicMaterial({
    color: 0xffd700,
    transparent: true,
    opacity: 0.3,
    side: THREE.DoubleSide,
  })
  const symbol = new THREE.Mesh(symbolGeo, symbolMat)
  symbol.position.y = 0.09
  symbol.rotation.x = -Math.PI / 2
  scene.add(symbol)
}

function buildCandles() {
  candles = []

  // 4 candelabras between agent positions
  for (let i = 0; i < 4; i++) {
    const angle = (i / 4) * Math.PI * 2 + Math.PI / 4
    const r = 2.8

    // Candle stick
    const stickGeo = new THREE.CylinderGeometry(0.04, 0.06, 0.8, 6)
    const stickMat = new THREE.MeshStandardMaterial({
      color: 0x8a7960,
      metalness: 0.5,
      roughness: 0.4,
    })
    const stick = new THREE.Mesh(stickGeo, stickMat)
    stick.position.set(Math.cos(angle) * r, 0.1, Math.sin(angle) * r)
    scene.add(stick)

    // Flame — small emissive sphere
    const flameGeo = new THREE.SphereGeometry(0.06, 8, 8)
    const flameMat = new THREE.MeshBasicMaterial({
      color: 0xffaa33,
      transparent: true,
      opacity: 0.9,
    })
    const flame = new THREE.Mesh(flameGeo, flameMat)
    flame.position.set(Math.cos(angle) * r, 0.55, Math.sin(angle) * r)
    scene.add(flame)

    // Warm point light at each candle
    const light = new THREE.PointLight(0xff9922, 0.4, 5)
    light.position.set(Math.cos(angle) * r, 0.6, Math.sin(angle) * r)
    scene.add(light)

    candles.push({ flame, light })
  }
}

function buildAgents() {
  agentMeshes = {}

  AGENTS.forEach(agent => {
    let mesh
    const r = 2.3

    if (agentModels.isLoaded(agent.id)) {
      mesh = agentModels.getAgentClone(agent.id, 1.2)
    }

    if (!mesh) {
      // Fallback: colored sphere with inner glow
      const geo = new THREE.SphereGeometry(0.35, 12, 12)
      const mat = new THREE.MeshStandardMaterial({
        color: agent.color,
        emissive: agent.color,
        emissiveIntensity: 0.2,
        metalness: 0.3,
        roughness: 0.4,
        transparent: true,
        opacity: 0.8,
      })
      mesh = new THREE.Mesh(geo, mat)
    }

    mesh.position.set(
      Math.cos(agent.angle) * r,
      0.3,
      Math.sin(agent.angle) * r
    )
    // Face the center
    mesh.lookAt(0, 0.3, 0)

    mesh.userData = { agentId: agent.id, baseEmissive: 0.2, color: agent.color }
    scene.add(mesh)
    agentMeshes[agent.id] = mesh
  })
}

function setEmissive(mesh, intensity) {
  if (mesh.isMesh && mesh.material?.emissive) {
    mesh.material.emissiveIntensity = intensity
  }
  if (mesh.children) {
    mesh.traverse(child => {
      if (child.isMesh && child.material?.emissive) {
        child.material.emissiveIntensity = intensity
      }
    })
  }
}

function animate() {
  animId = requestAnimationFrame(animate)
  if (!renderer || !scene || !camera) return

  const t = clock.getElapsedTime()

  // Agent glow based on active speaker
  Object.entries(agentMeshes).forEach(([id, mesh]) => {
    const isSpeaking = props.activeAgent === id
    const targetIntensity = isSpeaking ? 1.5 : 0.2

    // Smooth lerp
    const current = mesh.userData._currentEmissive ?? 0.2
    const next = current + (targetIntensity - current) * (isSpeaking ? 0.08 : 0.03)
    mesh.userData._currentEmissive = next

    setEmissive(mesh, next)

    // Speaking agent subtle lean forward (scale pulse)
    if (isSpeaking) {
      const pulse = 1.0 + Math.sin(t * 3) * 0.05
      mesh.scale.setScalar(pulse)
    } else {
      mesh.scale.setScalar(1.0)
    }
  })

  // Round flash effect
  if (roundFlashTime > 0) {
    const elapsed = t - roundFlashTime
    if (elapsed < 0.8) {
      const flash = Math.max(0, 1 - elapsed / 0.8)
      Object.values(agentMeshes).forEach(mesh => {
        const base = mesh.userData._currentEmissive ?? 0.2
        setEmissive(mesh, base + flash * 0.8)
      })
    }
  }

  // Candle flicker
  candles.forEach((c, i) => {
    const flicker = 0.3 + Math.sin(t * 8 + i * 3) * 0.1 + Math.sin(t * 13 + i * 7) * 0.05
    c.light.intensity = flicker
    c.flame.material.opacity = 0.7 + Math.sin(t * 10 + i * 5) * 0.2
    c.flame.scale.setScalar(0.8 + Math.sin(t * 6 + i * 4) * 0.3)
  })

  renderer.render(scene, camera)
}

// Watch for round changes — trigger flash
watch(() => props.round, (newRound, oldRound) => {
  if (newRound > 0 && newRound !== oldRound && clock) {
    roundFlashTime = clock.getElapsedTime()
  }
})

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
  table = null
  agentMeshes = {}
  candles = []
}

onMounted(() => {
  agentModels.preloadAll().then(() => {
    if (scene) {
      Object.values(agentMeshes).forEach(m => scene.remove(m))
      buildAgents()
    }
  })

  if (initScene()) animate()
})

onUnmounted(() => {
  dispose()
  agentModels.disposeAll()
})
</script>

<template>
  <div
    ref="containerRef"
    class="council-chamber w-full relative overflow-hidden rounded-lg border border-apex-border"
    style="height: 200px"
  >
    <!-- Active speaker label -->
    <div
      v-if="activeAgent"
      class="absolute top-2 right-3 z-10 pointer-events-none"
    >
      <span class="text-[10px] px-2 py-0.5 rounded-full bg-black/60 backdrop-blur text-gold/80 border border-gold/20">
        {{ activeAgent }} speaks
      </span>
    </div>

    <!-- Round indicator -->
    <div
      v-if="round > 0"
      class="absolute top-2 left-3 z-10 pointer-events-none"
    >
      <span class="text-[10px] px-2 py-0.5 rounded-full bg-black/60 backdrop-blur text-gray-400 border border-apex-border">
        Round {{ round }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.council-chamber {
  background: radial-gradient(ellipse at center, #0a0810 0%, #080810 100%);
}
</style>
