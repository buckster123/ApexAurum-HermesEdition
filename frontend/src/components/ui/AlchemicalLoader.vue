<script setup>
/**
 * AlchemicalLoader — 3D Loading Animation
 *
 * Three procedural variants replacing generic spinners:
 *   ouroboros — rotating golden torus ring
 *   stone    — pulsing icosahedron philosopher's stone
 *   particles — spiraling gold dust
 *
 * "The Great Work requires patience. The Athanor churns."
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'

const props = defineProps({
  size: {
    type: String,
    default: 'md',
    validator: v => ['sm', 'md', 'lg'].includes(v),
  },
  variant: {
    type: String,
    default: 'stone',
    validator: v => ['ouroboros', 'stone', 'particles'].includes(v),
  },
})

const containerRef = ref(null)
const webglFailed = ref(false)

const sizeMap = { sm: 48, md: 96, lg: 192 }
const px = computed(() => sizeMap[props.size])

let renderer = null
let scene = null
let camera = null
let animId = null
let clock = null

// Variant-specific objects
let mainObject = null
let particleSystem = null
let haloParticles = null

function initScene() {
  if (!containerRef.value) return false

  try {
    const canvas = document.createElement('canvas')
    if (!canvas.getContext('webgl') && !canvas.getContext('experimental-webgl')) {
      webglFailed.value = true
      return false
    }
  } catch { webglFailed.value = true; return false }

  const s = px.value

  try {
    scene = new THREE.Scene()
    camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100)
    camera.position.set(0, 0, 4)

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(s, s)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x000000, 0)
    containerRef.value.appendChild(renderer.domElement)

    // Lighting
    const ambient = new THREE.AmbientLight(0x404040, 0.6)
    scene.add(ambient)
    const point = new THREE.PointLight(0xffd700, 1.5, 20)
    point.position.set(2, 2, 3)
    scene.add(point)

    clock = new THREE.Clock()

    if (props.variant === 'ouroboros') buildOuroboros()
    else if (props.variant === 'stone') buildStone()
    else buildParticles()

    return true
  } catch {
    webglFailed.value = true
    return false
  }
}

function buildOuroboros() {
  // Golden torus ring
  const geo = new THREE.TorusGeometry(1, 0.15, 16, 48)
  const mat = new THREE.MeshStandardMaterial({
    color: 0xd4af37,
    emissive: 0xffd700,
    emissiveIntensity: 0.4,
    metalness: 0.8,
    roughness: 0.2,
  })
  mainObject = new THREE.Mesh(geo, mat)
  scene.add(mainObject)

  // "Head" marker — small sphere at one point of the torus
  const headGeo = new THREE.SphereGeometry(0.22, 8, 8)
  const headMat = new THREE.MeshStandardMaterial({
    color: 0xffd700,
    emissive: 0xffd700,
    emissiveIntensity: 1.0,
    metalness: 0.9,
    roughness: 0.1,
  })
  const head = new THREE.Mesh(headGeo, headMat)
  head.position.set(1, 0, 0)
  mainObject.add(head)

  // Tail taper — slightly smaller sphere opposite
  const tailGeo = new THREE.ConeGeometry(0.12, 0.3, 6)
  const tail = new THREE.Mesh(tailGeo, headMat.clone())
  tail.position.set(-1, 0, 0)
  tail.rotation.z = Math.PI / 2
  mainObject.add(tail)
}

function buildStone() {
  // Philosopher's Stone — wireframe icosahedron inside solid one
  const innerGeo = new THREE.IcosahedronGeometry(0.7, 1)
  const innerMat = new THREE.MeshStandardMaterial({
    color: 0xd4af37,
    emissive: 0xffd700,
    emissiveIntensity: 0.6,
    metalness: 0.5,
    roughness: 0.3,
    transparent: true,
    opacity: 0.85,
  })
  const inner = new THREE.Mesh(innerGeo, innerMat)

  const outerGeo = new THREE.IcosahedronGeometry(1.0, 1)
  const outerMat = new THREE.MeshBasicMaterial({
    color: 0xffd700,
    wireframe: true,
    transparent: true,
    opacity: 0.3,
  })
  const outer = new THREE.Mesh(outerGeo, outerMat)

  mainObject = new THREE.Group()
  mainObject.add(inner)
  mainObject.add(outer)
  scene.add(mainObject)

  // Halo particles around the stone
  const count = 40
  const positions = new Float32Array(count * 3)
  for (let i = 0; i < count; i++) {
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)
    const r = 1.3 + Math.random() * 0.5
    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
    positions[i * 3 + 2] = r * Math.cos(phi)
  }
  const pGeo = new THREE.BufferGeometry()
  pGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  const pMat = new THREE.PointsMaterial({
    color: 0xffd700,
    size: 0.06,
    transparent: true,
    opacity: 0.6,
    sizeAttenuation: true,
  })
  haloParticles = new THREE.Points(pGeo, pMat)
  scene.add(haloParticles)
}

function buildParticles() {
  const count = 80
  const positions = new Float32Array(count * 3)
  const velocities = new Float32Array(count * 3) // stored separately for animation

  for (let i = 0; i < count; i++) {
    const angle = (i / count) * Math.PI * 2 * 3 // 3 spiral arms
    const r = 0.2 + (i / count) * 1.5
    positions[i * 3] = Math.cos(angle) * r
    positions[i * 3 + 1] = (Math.random() - 0.5) * 0.5
    positions[i * 3 + 2] = Math.sin(angle) * r
    velocities[i * 3] = 0
    velocities[i * 3 + 1] = 0.3 + Math.random() * 0.5
    velocities[i * 3 + 2] = 0
  }

  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))

  const mat = new THREE.PointsMaterial({
    color: 0xffd700,
    size: 0.08,
    transparent: true,
    opacity: 0.8,
    sizeAttenuation: true,
  })

  particleSystem = new THREE.Points(geo, mat)
  particleSystem._velocities = velocities
  particleSystem._basePositions = new Float32Array(positions)
  scene.add(particleSystem)

  mainObject = particleSystem
}

function animate() {
  animId = requestAnimationFrame(animate)
  if (!renderer || !scene || !camera) return

  const t = clock.getElapsedTime()

  if (props.variant === 'ouroboros') {
    // Rotate the ring
    mainObject.rotation.z = t * 1.5
    mainObject.rotation.x = Math.sin(t * 0.5) * 0.3
    // Pulsing emissive
    mainObject.children.forEach(c => {
      if (c.material) c.material.emissiveIntensity = 0.6 + Math.sin(t * 3) * 0.4
    })
    mainObject.material.emissiveIntensity = 0.3 + Math.sin(t * 2) * 0.2
  } else if (props.variant === 'stone') {
    // Rotate stone + wireframe at different speeds
    const inner = mainObject.children[0]
    const outer = mainObject.children[1]
    inner.rotation.y = t * 0.8
    inner.rotation.x = t * 0.3
    outer.rotation.y = -t * 0.5
    outer.rotation.z = t * 0.2

    // Pulsing emissive — breathing rhythm
    inner.material.emissiveIntensity = 0.4 + Math.sin(t * 2) * 0.4

    // Scale pulse
    const scale = 1 + Math.sin(t * 2) * 0.08
    mainObject.scale.setScalar(scale)

    // Rotate halo particles
    if (haloParticles) {
      haloParticles.rotation.y = t * 0.3
      haloParticles.rotation.x = Math.sin(t * 0.7) * 0.2
      haloParticles.material.opacity = 0.4 + Math.sin(t * 3) * 0.2
    }
  } else {
    // Particles — spiral rotation + vertical drift
    mainObject.rotation.y = t * 0.8

    const positions = particleSystem.geometry.attributes.position.array
    const base = particleSystem._basePositions
    const count = positions.length / 3

    for (let i = 0; i < count; i++) {
      const phase = (i / count) * Math.PI * 2
      const yOffset = ((t * 0.5 + phase) % 2) - 1 // cycle -1 to 1
      positions[i * 3] = base[i * 3]
      positions[i * 3 + 1] = base[i * 3 + 1] + yOffset
      positions[i * 3 + 2] = base[i * 3 + 2]
    }
    particleSystem.geometry.attributes.position.needsUpdate = true

    // Pulsing opacity
    particleSystem.material.opacity = 0.5 + Math.sin(t * 2) * 0.3
  }

  renderer.render(scene, camera)
}

function dispose() {
  if (animId) cancelAnimationFrame(animId)
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
  mainObject = null
  particleSystem = null
  haloParticles = null
}

onMounted(() => {
  if (initScene()) animate()
})

onUnmounted(dispose)
</script>

<template>
  <div
    ref="containerRef"
    class="alchemical-loader inline-flex items-center justify-center"
    :style="{ width: px + 'px', height: px + 'px' }"
  >
    <!-- CSS fallback when WebGL unavailable -->
    <div
      v-if="webglFailed"
      class="border-2 border-gold border-t-transparent rounded-full animate-spin"
      :style="{ width: (px * 0.6) + 'px', height: (px * 0.6) + 'px' }"
    ></div>
  </div>
</template>

<style scoped>
.alchemical-loader {
  overflow: hidden;
  border-radius: 8px;
}
</style>
