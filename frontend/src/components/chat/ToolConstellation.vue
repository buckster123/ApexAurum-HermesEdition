<script setup>
import { ref, shallowRef, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'

const emit = defineEmits(['select'])

const containerRef = ref(null)
const webglFailed = ref(false)

const CATEGORIES = [
  { id: 'utility',    label: 'Utility',   color: '#9E9E9E', shape: 'octahedron' },
  { id: 'web',        label: 'Web',       color: '#66BB6A', shape: 'icosahedron' },
  { id: 'memory',     label: 'Memory',    color: '#FFD700', shape: 'sphere' },
  { id: 'files',      label: 'Files',     color: '#4FC3F7', shape: 'box' },
  { id: 'agent',      label: 'Agents',    color: '#E8B4FF', shape: 'dodecahedron' },
  { id: 'music',      label: 'Music',     color: '#AB47BC', shape: 'torus' },
  { id: 'browser',    label: 'Browser',   color: '#EF5350', shape: 'cone' },
  { id: 'creative',   label: 'Creative',  color: '#FF9800', shape: 'torusknot' },
  { id: 'nursery',    label: 'Nursery',   color: '#8BC34A', shape: 'tetrahedron' },
  { id: 'sensorhead', label: 'Sensors',   color: '#00BCD4', shape: 'cylinder' },
]

const CONNECTIONS = [
  ['utility', 'web'], ['utility', 'files'], ['web', 'browser'],
  ['memory', 'agent'], ['memory', 'files'], ['agent', 'nursery'],
  ['music', 'creative'], ['creative', 'agent'], ['browser', 'web'],
  ['nursery', 'memory'], ['sensorhead', 'utility'], ['sensorhead', 'memory'],
]

let renderer = null
let scene = null
let camera = null
let rafId = null
let resizeObserver = null
let raycaster = null
let mouse = null
let clock = null

const nodeGroup = shallowRef(null)
const nodeMeshes = []
const nodePositions = []
const hoveredIndex = ref(-1)

function createGeometry(shape) {
  switch (shape) {
    case 'octahedron':    return new THREE.OctahedronGeometry(0.6, 0)
    case 'icosahedron':   return new THREE.IcosahedronGeometry(0.6, 1)
    case 'sphere':        return new THREE.SphereGeometry(0.6, 8, 8)
    case 'box':           return new THREE.BoxGeometry(0.9, 0.9, 0.9)
    case 'dodecahedron':  return new THREE.DodecahedronGeometry(0.6, 0)
    case 'torus':         return new THREE.TorusGeometry(0.5, 0.2, 8, 16)
    case 'cone':          return new THREE.ConeGeometry(0.5, 1, 6)
    case 'torusknot':     return new THREE.TorusKnotGeometry(0.4, 0.15, 64, 8)
    case 'tetrahedron':   return new THREE.TetrahedronGeometry(0.7, 0)
    case 'cylinder':      return new THREE.CylinderGeometry(0.4, 0.4, 0.8, 8)
    default:              return new THREE.SphereGeometry(0.6, 8, 8)
  }
}

function fibonacciSphere(count, radius) {
  const points = []
  const goldenAngle = Math.PI * (3 - Math.sqrt(5))
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2
    const r = Math.sqrt(1 - y * y)
    const theta = goldenAngle * i
    points.push(new THREE.Vector3(
      Math.cos(theta) * r * radius,
      y * radius,
      Math.sin(theta) * r * radius,
    ))
  }
  return points
}

function createLabel(text) {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  canvas.width = 256
  canvas.height = 64
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  ctx.font = '600 28px system-ui, sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = 'rgba(255, 255, 255, 0.85)'
  ctx.fillText(text, 128, 32)

  const texture = new THREE.CanvasTexture(canvas)
  texture.needsUpdate = true
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false })
  const sprite = new THREE.Sprite(material)
  sprite.scale.set(2.5, 0.625, 1)
  return sprite
}

function buildScene() {
  const el = containerRef.value
  if (!el) return

  // WebGL availability check
  try {
    const testCanvas = document.createElement('canvas')
    if (!testCanvas.getContext('webgl') && !testCanvas.getContext('experimental-webgl')) {
      webglFailed.value = true
      return
    }
  } catch { webglFailed.value = true; return }

  scene = new THREE.Scene()
  clock = new THREE.Clock()
  raycaster = new THREE.Raycaster()
  mouse = new THREE.Vector2()

  const rect = el.getBoundingClientRect()
  if (rect.width === 0 || rect.height === 0) return

  camera = new THREE.PerspectiveCamera(50, rect.width / rect.height, 0.1, 100)
  camera.position.set(0, 0, 20)

  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  } catch { webglFailed.value = true; return }
  renderer.setSize(rect.width, rect.height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setClearColor(0x000000, 0)
  el.appendChild(renderer.domElement)

  scene.add(new THREE.AmbientLight(0x404040, 0.8))
  const point = new THREE.PointLight(0xffffff, 1.5)
  point.position.set(5, 5, 10)
  scene.add(point)

  const group = new THREE.Group()
  nodeGroup.value = group
  const positions = fibonacciSphere(CATEGORIES.length, 6)

  CATEGORIES.forEach((cat, i) => {
    const pos = positions[i]
    nodePositions.push(pos.clone())

    const color = new THREE.Color(cat.color)
    const geo = createGeometry(cat.shape)
    const mat = new THREE.MeshStandardMaterial({
      color,
      emissive: color,
      emissiveIntensity: 0.4,
      metalness: 0.5,
      roughness: 0.3,
    })
    const mesh = new THREE.Mesh(geo, mat)
    mesh.position.copy(pos)
    mesh.userData = { categoryIndex: i, categoryId: cat.id }
    nodeMeshes.push(mesh)
    group.add(mesh)

    const label = createLabel(cat.label)
    label.position.copy(pos)
    label.position.y -= 1.2
    group.add(label)
  })

  buildConnections(group, positions)
  scene.add(group)
}

function buildConnections(group, positions) {
  const indexMap = {}
  CATEGORIES.forEach((c, i) => { indexMap[c.id] = i })
  const gold = new THREE.Color('#FFD700')

  CONNECTIONS.forEach(([a, b]) => {
    const ia = indexMap[a]
    const ib = indexMap[b]
    if (ia === undefined || ib === undefined) return

    const points = [positions[ia], positions[ib]]
    const geo = new THREE.BufferGeometry().setFromPoints(points)
    const mat = new THREE.LineBasicMaterial({ color: gold, transparent: true, opacity: 0.15 })
    group.add(new THREE.Line(geo, mat))
  })
}

function onResize() {
  const el = containerRef.value
  if (!el || !renderer || !camera) return
  const rect = el.getBoundingClientRect()
  camera.aspect = rect.width / rect.height
  camera.updateProjectionMatrix()
  renderer.setSize(rect.width, rect.height)
}

function onMouseMove(event) {
  const el = containerRef.value
  if (!el || !raycaster || !camera) return

  const rect = el.getBoundingClientRect()
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(mouse, camera)
  const hits = raycaster.intersectObjects(nodeMeshes)

  if (hits.length > 0) {
    const idx = hits[0].object.userData.categoryIndex
    if (hoveredIndex.value !== idx) {
      resetHover()
      hoveredIndex.value = idx
      const mesh = nodeMeshes[idx]
      mesh.scale.set(1.3, 1.3, 1.3)
      mesh.material.emissiveIntensity = 1.0
    }
    el.style.cursor = 'pointer'
  } else {
    resetHover()
    el.style.cursor = 'default'
  }
}

function resetHover() {
  if (hoveredIndex.value >= 0) {
    const mesh = nodeMeshes[hoveredIndex.value]
    mesh.scale.set(1, 1, 1)
    mesh.material.emissiveIntensity = 0.4
    hoveredIndex.value = -1
  }
}

function onClick(event) {
  const el = containerRef.value
  if (!el || !raycaster || !camera) return

  const rect = el.getBoundingClientRect()
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(mouse, camera)
  const hits = raycaster.intersectObjects(nodeMeshes)
  if (hits.length > 0) {
    emit('select', hits[0].object.userData.categoryId)
  }
}

function onTouchStart(event) {
  if (!event.touches.length) return
  const touch = event.touches[0]
  // Update hover on touch
  onMouseMove({ clientX: touch.clientX, clientY: touch.clientY })
}

function onTouchEnd(event) {
  if (!event.changedTouches.length) return
  const touch = event.changedTouches[0]
  // Simulate click at touch point
  onClick({ clientX: touch.clientX, clientY: touch.clientY })
  // Clear hover after short delay
  setTimeout(resetHover, 300)
}

function animate() {
  rafId = requestAnimationFrame(animate)
  if (!scene || !camera || !renderer || !nodeGroup.value) return

  const dt = clock.getDelta()
  const t = clock.elapsedTime
  nodeGroup.value.rotation.y += 0.15 * dt

  nodeMeshes.forEach((mesh, i) => {
    const base = nodePositions[i]
    mesh.position.y = base.y + Math.sin(t + i * 1.1) * 0.3
    mesh.rotation.x = t * 0.3 + i
    mesh.rotation.z = t * 0.2 + i * 0.5
  })

  renderer.render(scene, camera)
}

function dispose() {
  if (rafId) cancelAnimationFrame(rafId)
  if (resizeObserver) resizeObserver.disconnect()

  const el = containerRef.value
  if (el) {
    el.removeEventListener('mousemove', onMouseMove)
    el.removeEventListener('click', onClick)
    el.removeEventListener('touchstart', onTouchStart)
    el.removeEventListener('touchend', onTouchEnd)
  }

  if (scene) {
    scene.traverse(obj => {
      if (obj.geometry) obj.geometry.dispose()
      if (obj.material) {
        if (obj.material.map) obj.material.map.dispose()
        obj.material.dispose()
      }
    })
  }

  if (renderer) {
    renderer.dispose()
    if (renderer.domElement?.parentNode) {
      renderer.domElement.parentNode.removeChild(renderer.domElement)
    }
  }

  nodeMeshes.length = 0
  nodePositions.length = 0
  renderer = null
  scene = null
  camera = null
}

onMounted(() => {
  buildScene()
  if (!webglFailed.value && renderer) {
    animate()

    const el = containerRef.value
    if (el) {
      el.addEventListener('mousemove', onMouseMove)
      el.addEventListener('click', onClick)
      el.addEventListener('touchstart', onTouchStart, { passive: true })
      el.addEventListener('touchend', onTouchEnd, { passive: true })
      resizeObserver = new ResizeObserver(onResize)
      resizeObserver.observe(el)
    }
  }
})

onUnmounted(dispose)
</script>

<template>
  <div ref="containerRef" class="w-full h-64 relative">
    <!-- CSS fallback when WebGL unavailable -->
    <div v-if="webglFailed" class="absolute inset-0 flex flex-wrap items-center justify-center gap-3 p-4">
      <button
        v-for="cat in CATEGORIES"
        :key="cat.id"
        @click="emit('select', cat.id)"
        class="px-3 py-1.5 rounded-full text-xs border transition-colors hover:scale-105"
        :style="{ borderColor: cat.color + '40', color: cat.color }"
      >
        {{ cat.label }}
      </button>
    </div>
  </div>
</template>
