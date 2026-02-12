<script setup>
/**
 * AthanorHero — Landing Page 3D Background
 *
 * A procedural Three.js scene: forge structure, glowing cauldron,
 * orbiting sacred geometry, floating agent avatars, rising gold particles.
 * Mouse parallax for depth. Text overlays on top with pointer-events: none.
 *
 * "The first thing they see. The Athanor, alive."
 */

import { ref, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { useAgentModels } from '@/composables/useAgentModels'

const containerRef = ref(null)
const webglFailed = ref(false)

const AGENT_IDS = ['AZOTH', 'ELYSIAN', 'VAJRA', 'KETHER']
const AGENT_COLORS = {
  AZOTH: 0xd4af37,
  ELYSIAN: 0xe8b4ff,
  VAJRA: 0x4fc3f7,
  KETHER: 0xab47bc,
}

let renderer = null
let scene = null
let camera = null
let animId = null
let clock = null
let resizeObserver = null

// Scene objects
let forgeGroup = null
let cauldron = null
let cauldronGlow = null
let symbolsGroup = null
let agentMeshes = []
let particles = null
let mouseX = 0
let mouseY = 0

const agentModels = useAgentModels()

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
    scene.background = new THREE.Color(0x0a0a0f)
    scene.fog = new THREE.FogExp2(0x0a0a0f, 0.035)

    camera = new THREE.PerspectiveCamera(55, w / h, 0.1, 200)
    camera.position.set(0, 3, 10)
    camera.lookAt(0, 0.5, 0)

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    renderer.setSize(w, h)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    el.appendChild(renderer.domElement)

    // Lighting
    const ambient = new THREE.AmbientLight(0x1a1020, 0.3)
    scene.add(ambient)

    // Warm point light above cauldron
    const cauldronLight = new THREE.PointLight(0xffd700, 1.5, 20)
    cauldronLight.position.set(0, 3, 0)
    scene.add(cauldronLight)

    // Subtle blue rim light
    const rimLight = new THREE.PointLight(0x4fc3f7, 0.4, 25)
    rimLight.position.set(-5, 2, 5)
    scene.add(rimLight)

    clock = new THREE.Clock()

    buildForge()
    buildCauldron()
    buildSacredGeometry()
    buildParticles()
    buildAgents()

    // Grid floor
    const grid = new THREE.GridHelper(40, 20, 0x1a1a2e, 0x0f0f1a)
    grid.position.y = -1.5
    scene.add(grid)

    // Mouse tracking for parallax
    el.addEventListener('mousemove', onMouseMove)

    resizeObserver = new ResizeObserver(() => handleResize())
    resizeObserver.observe(el)

    return true
  } catch {
    return false
  }
}

function buildForge() {
  forgeGroup = new THREE.Group()

  const forgeMat = new THREE.MeshStandardMaterial({
    color: 0x2a2020,
    metalness: 0.6,
    roughness: 0.7,
    emissive: 0x1a0a00,
    emissiveIntensity: 0.1,
  })

  // Base platform — octagonal shape approximated with cylinder
  const baseGeo = new THREE.CylinderGeometry(2.5, 2.8, 0.4, 8)
  const base = new THREE.Mesh(baseGeo, forgeMat)
  base.position.y = -1.3
  forgeGroup.add(base)

  // Four pillars around the cauldron
  const pillarGeo = new THREE.CylinderGeometry(0.12, 0.15, 2.5, 6)
  const pillarMat = new THREE.MeshStandardMaterial({
    color: 0x3a2820,
    metalness: 0.7,
    roughness: 0.5,
    emissive: 0xd4af37,
    emissiveIntensity: 0.05,
  })

  for (let i = 0; i < 4; i++) {
    const angle = (i / 4) * Math.PI * 2 + Math.PI / 4
    const pillar = new THREE.Mesh(pillarGeo, pillarMat)
    pillar.position.set(Math.cos(angle) * 1.8, 0, Math.sin(angle) * 1.8)
    forgeGroup.add(pillar)

    // Pillar cap — small sphere
    const capGeo = new THREE.SphereGeometry(0.18, 8, 8)
    const capMat = new THREE.MeshStandardMaterial({
      color: 0xd4af37,
      emissive: 0xffd700,
      emissiveIntensity: 0.4,
      metalness: 0.8,
      roughness: 0.2,
    })
    const cap = new THREE.Mesh(capGeo, capMat)
    cap.position.set(Math.cos(angle) * 1.8, 1.3, Math.sin(angle) * 1.8)
    forgeGroup.add(cap)
  }

  // Upper arch — torus connecting pillars
  const archGeo = new THREE.TorusGeometry(1.8, 0.06, 8, 32, Math.PI * 2)
  const archMat = new THREE.MeshStandardMaterial({
    color: 0xd4af37,
    emissive: 0xffd700,
    emissiveIntensity: 0.2,
    metalness: 0.8,
    roughness: 0.3,
  })
  const arch = new THREE.Mesh(archGeo, archMat)
  arch.position.y = 1.3
  arch.rotation.x = Math.PI / 2
  forgeGroup.add(arch)

  scene.add(forgeGroup)
}

function buildCauldron() {
  // Cauldron bowl — half sphere
  const bowlGeo = new THREE.SphereGeometry(0.9, 16, 16, 0, Math.PI * 2, 0, Math.PI / 2)
  const bowlMat = new THREE.MeshStandardMaterial({
    color: 0x1a1a1a,
    metalness: 0.8,
    roughness: 0.3,
    emissive: 0x0a0a0a,
    emissiveIntensity: 0.1,
    side: THREE.DoubleSide,
  })
  cauldron = new THREE.Mesh(bowlGeo, bowlMat)
  cauldron.position.y = -0.6
  cauldron.rotation.x = Math.PI
  scene.add(cauldron)

  // Glowing liquid inside
  const glowGeo = new THREE.CircleGeometry(0.8, 24)
  const glowMat = new THREE.MeshBasicMaterial({
    color: 0xffd700,
    transparent: true,
    opacity: 0.7,
    side: THREE.DoubleSide,
  })
  cauldronGlow = new THREE.Mesh(glowGeo, glowMat)
  cauldronGlow.position.y = -0.35
  cauldronGlow.rotation.x = -Math.PI / 2
  scene.add(cauldronGlow)

  // Cauldron glow point light
  const glowLight = new THREE.PointLight(0xffd700, 2.0, 6)
  glowLight.position.set(0, 0, 0)
  scene.add(glowLight)
}

function buildSacredGeometry() {
  symbolsGroup = new THREE.Group()

  // Three nested rotating polyhedra
  const shapes = [
    { Geo: THREE.IcosahedronGeometry, args: [0.5, 0], y: 2.5, speed: 0.4 },
    { Geo: THREE.OctahedronGeometry, args: [0.35, 0], y: 2.5, speed: -0.6 },
    { Geo: THREE.TetrahedronGeometry, args: [0.2, 0], y: 2.5, speed: 0.8 },
  ]

  shapes.forEach(s => {
    const geo = new s.Geo(...s.args)
    const mat = new THREE.MeshBasicMaterial({
      color: 0xffd700,
      wireframe: true,
      transparent: true,
      opacity: 0.25,
    })
    const mesh = new THREE.Mesh(geo, mat)
    mesh.position.y = s.y
    mesh.userData.speed = s.speed
    symbolsGroup.add(mesh)
  })

  scene.add(symbolsGroup)
}

const isMobileDevice = typeof navigator !== 'undefined'
  && (/Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
    || (navigator.maxTouchPoints > 0 && !window.matchMedia?.('(pointer: fine)')?.matches))

function buildParticles() {
  const count = isMobileDevice ? 60 : 150
  const positions = new Float32Array(count * 3)
  const sizes = new Float32Array(count)

  for (let i = 0; i < count; i++) {
    // Cylindrical distribution around the cauldron
    const angle = Math.random() * Math.PI * 2
    const r = 0.3 + Math.random() * 1.5
    positions[i * 3] = Math.cos(angle) * r
    positions[i * 3 + 1] = -0.5 + Math.random() * 5
    positions[i * 3 + 2] = Math.sin(angle) * r
    sizes[i] = 0.02 + Math.random() * 0.04
  }

  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1))

  const mat = new THREE.PointsMaterial({
    color: 0xffd700,
    size: 0.05,
    transparent: true,
    opacity: 0.6,
    sizeAttenuation: true,
  })

  particles = new THREE.Points(geo, mat)
  particles._basePositions = new Float32Array(positions)
  scene.add(particles)
}

function buildAgents() {
  agentMeshes = []
  // Skip decorative orbiting agents on mobile — they're small and distant
  if (isMobileDevice) return

  AGENT_IDS.forEach((agentId, i) => {
    let mesh

    if (agentModels.isLoaded(agentId)) {
      mesh = agentModels.getAgentClone(agentId, 1.2)
    }

    if (!mesh) {
      const geo = new THREE.SphereGeometry(0.3, 12, 12)
      const mat = new THREE.MeshStandardMaterial({
        color: AGENT_COLORS[agentId],
        emissive: AGENT_COLORS[agentId],
        emissiveIntensity: 0.4,
        transparent: true,
        opacity: 0.7,
      })
      mesh = new THREE.Mesh(geo, mat)
    }

    // Orbit around forge
    const angle = (i / AGENT_IDS.length) * Math.PI * 2
    mesh.position.set(
      Math.cos(angle) * 3.5,
      1 + Math.sin(angle * 2) * 0.5,
      Math.sin(angle) * 3.5
    )
    mesh.userData = { orbitAngle: angle, agentIndex: i }
    scene.add(mesh)
    agentMeshes.push(mesh)
  })
}

function onMouseMove(event) {
  if (!containerRef.value) return
  const rect = containerRef.value.getBoundingClientRect()
  mouseX = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouseY = -((event.clientY - rect.top) / rect.height) * 2 + 1
}

function animate() {
  animId = requestAnimationFrame(animate)
  if (!renderer || !scene || !camera) return

  const t = clock.getElapsedTime()

  // Mouse parallax on camera
  camera.position.x += (mouseX * 1.5 - camera.position.x) * 0.02
  camera.position.y += (3 + mouseY * 0.8 - camera.position.y) * 0.02
  camera.lookAt(0, 0.5, 0)

  // Cauldron glow pulse
  if (cauldronGlow) {
    cauldronGlow.material.opacity = 0.5 + Math.sin(t * 2) * 0.2
  }

  // Sacred geometry rotation
  if (symbolsGroup) {
    symbolsGroup.children.forEach(mesh => {
      mesh.rotation.y = t * mesh.userData.speed
      mesh.rotation.x = Math.sin(t * 0.3) * 0.3
    })
    // Whole group slow rotation
    symbolsGroup.rotation.y = t * 0.1
  }

  // Gold particles rise and reset
  if (particles) {
    const pos = particles.geometry.attributes.position.array
    const base = particles._basePositions
    const count = pos.length / 3

    for (let i = 0; i < count; i++) {
      const speed = 0.3 + (i % 5) * 0.1
      const yOffset = (t * speed + i * 0.1) % 5.5
      pos[i * 3] = base[i * 3] + Math.sin(t * 0.5 + i) * 0.1
      pos[i * 3 + 1] = -0.5 + yOffset
      pos[i * 3 + 2] = base[i * 3 + 2] + Math.cos(t * 0.5 + i) * 0.1
    }
    particles.geometry.attributes.position.needsUpdate = true
    particles.material.opacity = 0.4 + Math.sin(t) * 0.2
  }

  // Agent avatars orbit
  agentMeshes.forEach((mesh, i) => {
    const baseAngle = mesh.userData.orbitAngle
    const angle = baseAngle + t * 0.15
    const radius = 3.5
    mesh.position.x = Math.cos(angle) * radius
    mesh.position.z = Math.sin(angle) * radius
    mesh.position.y = 1 + Math.sin(t * 0.5 + i * 1.5) * 0.5
    mesh.rotation.y = -angle + Math.PI // face center
  })

  // Pillar cap glow pulse (access through forgeGroup)
  if (forgeGroup) {
    forgeGroup.children.forEach(child => {
      if (child.geometry?.type === 'SphereGeometry' && child.material?.emissive) {
        child.material.emissiveIntensity = 0.3 + Math.sin(t * 2 + child.position.x) * 0.2
      }
    })
  }

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
  if (containerRef.value) {
    containerRef.value.removeEventListener('mousemove', onMouseMove)
  }

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
  forgeGroup = null
  cauldron = null
  cauldronGlow = null
  symbolsGroup = null
  particles = null
  agentMeshes = []
}

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
  <div ref="containerRef" class="athanor-hero absolute inset-0 z-0">
    <!-- Gradient fallback when WebGL unavailable -->
    <div v-if="webglFailed" class="absolute inset-0 athanor-hero-fallback" />
  </div>
</template>

<style scoped>
.athanor-hero {
  pointer-events: auto;
}
.athanor-hero-fallback {
  background: radial-gradient(ellipse at 50% 60%, rgba(212,175,55,0.08) 0%, rgba(10,10,15,1) 70%);
}
</style>
