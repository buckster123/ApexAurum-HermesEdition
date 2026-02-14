<script setup>
/**
 * NeuralSpace - 3D Memory Visualization
 *
 * A Three.js-powered 3D visualization of memories as glowing nodes.
 * "Memories float like stars in the neural cosmos"
 */

import { ref, shallowRef, watch, onMounted, onUnmounted, computed } from 'vue'
import * as THREE from 'three'
import { useThreeScene, createMemoryNode, createConnectionLine } from '@/composables/useThreeScene'
import { useNeoCortexStore, AGENT_COLORS, LAYER_CONFIG } from '@/stores/neocortex'
import { useDreamStore } from '@/stores/dream'
import { useSound } from '@/composables/useSound'
import { NeuralAmbientSystem } from '@/composables/useNeuralAmbient'
import { DreamNexusSystem } from '@/composables/useDreamNexus'
import { DreamEffectsSystem } from '@/composables/useDreamEffects'
import { useAgentModels } from '@/composables/useAgentModels'
import AlchemicalLoader from '@/components/ui/AlchemicalLoader.vue'

const props = defineProps({
  autoRotate: {
    type: Boolean,
    default: true,
  },
  showConnections: {
    type: Boolean,
    default: true,
  },
})

const emit = defineEmits(['select', 'hover', 'doubleClick'])

const store = useNeoCortexStore()
const dreamStore = useDreamStore()
const containerRef = ref(null)

// Initialize Three.js
const {
  scene,
  camera,
  isInitialized,
  getObjectAtMouse,
  focusOn,
  setAutoRotate,
  addAnimationCallback,
} = useThreeScene(containerRef, {
  backgroundColor: 0x0a0a0f,
  cameraPosition: [0, 50, 100],
  autoRotate: props.autoRotate,
})

// Sound
const { playTone } = useSound()

// Node tracking
const nodeGroup = shallowRef(null)
const connectionGroup = shallowRef(null)
const nodeMap = new Map() // id -> mesh
const auraMap = new Map() // id -> aura mesh (purple glow for queued nodes)
const hoveredNode = ref(null)
const selectedNode = ref(null)

// Agent 3D models (progressive enhancement)
const agentModels = useAgentModels()

// Ambient neural pulse system
let ambientSystem = null
let removeAmbientCallback = null
let initCheckInterval = null

// Dream Nexus (alchemy helix at scene center)
let nexusSystem = null
let removeNexusCallback = null

// Dream Effects (phase-by-phase visual transformations)
let effectsSystem = null
let removeEffectsCallback = null

/**
 * Walk up the parent chain to find the memory-node group.
 * GLB models are Groups, so raycasting hits child meshes —
 * this finds the ancestor that holds the userData.
 */
function findMemoryNode(obj) {
  let current = obj
  while (current) {
    if (current.userData?.type === 'memory-node') return current
    current = current.parent
  }
  return null
}

// Purple aura for dream-queued nodes
const auraMaterial = new THREE.MeshBasicMaterial({
  color: 0x9c27b0,
  transparent: true,
  opacity: 0.12,
  blending: THREE.AdditiveBlending,
  depthWrite: false,
  side: THREE.BackSide,
})

function createAura(parentNode) {
  const salience = parentNode.userData.memory?.salience ?? 0.5
  const baseSize = 0.5 + salience * 1.5
  const auraGeo = new THREE.SphereGeometry(baseSize * 2.2, 12, 12)
  const aura = new THREE.Mesh(auraGeo, auraMaterial.clone())
  aura.position.copy(parentNode.position)
  aura.userData = { type: 'dream-aura', phase: Math.random() * Math.PI * 2 }
  return aura
}

function syncAuras() {
  if (!nodeGroup.value || !scene.value) return
  const queuedIds = new Set(dreamStore.dreamQueue.map(q => q.memory_id))

  // Remove auras for nodes no longer queued
  for (const [id, aura] of auraMap) {
    if (!queuedIds.has(id)) {
      scene.value.remove(aura)
      aura.geometry.dispose()
      aura.material.dispose()
      auraMap.delete(id)
    }
  }

  // Add auras for newly queued nodes
  for (const id of queuedIds) {
    if (!auraMap.has(id) && nodeMap.has(id)) {
      const aura = createAura(nodeMap.get(id))
      scene.value.add(aura)
      auraMap.set(id, aura)
    }
  }
}

// Build visualization from graph data
function buildVisualization() {
  if (!scene.value) return

  // Clear existing
  if (nodeGroup.value) {
    scene.value.remove(nodeGroup.value)
  }
  if (connectionGroup.value) {
    scene.value.remove(connectionGroup.value)
  }
  // Clear auras
  for (const [, aura] of auraMap) {
    scene.value.remove(aura)
    aura.geometry.dispose()
    aura.material.dispose()
  }
  auraMap.clear()

  nodeGroup.value = new THREE.Group()
  connectionGroup.value = new THREE.Group()
  nodeMap.clear()

  const nodes = store.filteredNodes
  const edges = store.filteredEdges

  // Create nodes (with GLB models when available, spheres as fallback)
  nodes.forEach(memory => {
    const mesh = createMemoryNode(memory, AGENT_COLORS, LAYER_CONFIG, agentModels)
    nodeGroup.value.add(mesh)
    nodeMap.set(memory.id, mesh)
  })

  // Create connections
  if (props.showConnections) {
    edges.forEach(edge => {
      const startMesh = nodeMap.get(edge.source)
      const endMesh = nodeMap.get(edge.target)

      if (startMesh && endMesh) {
        const line = createConnectionLine(
          startMesh.position.toArray(),
          endMesh.position.toArray(),
          edge.type,
          edge.weight
        )
        connectionGroup.value.add(line)
      }
    })
  }

  scene.value.add(nodeGroup.value)
  scene.value.add(connectionGroup.value)

  // Add purple auras for queued memories
  syncAuras()
}

// Mouse handlers
function onMouseMove(event) {
  if (!nodeGroup.value) return

  const intersect = getObjectAtMouse(event, nodeGroup.value.children)
  const memNode = intersect ? findMemoryNode(intersect.object) : null

  if (memNode) {
    const memory = memNode.userData.memory

    // Update hover state
    if (hoveredNode.value !== memNode) {
      // Reset previous hover
      if (hoveredNode.value) {
        hoveredNode.value.scale.set(1, 1, 1)
      }

      hoveredNode.value = memNode
      memNode.scale.set(1.2, 1.2, 1.2)

      store.hoveredMemory = memory
      emit('hover', memory)
    }

    containerRef.value.style.cursor = 'pointer'
  } else {
    // No hover
    if (hoveredNode.value) {
      hoveredNode.value.scale.set(1, 1, 1)
      hoveredNode.value = null
      store.hoveredMemory = null
      emit('hover', null)
    }
    containerRef.value.style.cursor = 'default'
  }
}

function setNodeEmissive(node, multiplier) {
  if (node.isMesh && node.material) {
    node.material.emissiveIntensity *= multiplier
  }
  if (node.children) {
    node.traverse((child) => {
      if (child.isMesh && child.material) {
        child.material.emissiveIntensity *= multiplier
      }
    })
  }
}

function onClick(event) {
  // Check nexus orbs first (they sit at scene center)
  if (nexusSystem) {
    const nexusHit = getObjectAtMouse(event, nexusSystem.getClickableObjects())
    if (nexusHit) {
      store.setRightPanelMode('dream')
      playTone(554, 0.1, 'sine', 0.15)
      return
    }
  }

  if (!nodeGroup.value) return

  const intersect = getObjectAtMouse(event, nodeGroup.value.children)
  const memNode = intersect ? findMemoryNode(intersect.object) : null

  if (memNode) {
    const memory = memNode.userData.memory

    // Reset previous selection
    if (selectedNode.value) {
      setNodeEmissive(selectedNode.value, 0.5)
    }

    // Select new node
    selectedNode.value = memNode
    setNodeEmissive(memNode, 2)

    store.selectMemory(memory)
    emit('select', memory)

    // Sound feedback
    playTone(659, 0.1, 'sine', 0.15)
  }
}

function onDoubleClick(event) {
  if (!nodeGroup.value) return

  const intersect = getObjectAtMouse(event, nodeGroup.value.children)
  const memNode = intersect ? findMemoryNode(intersect.object) : null

  if (memNode) {
    const memory = memNode.userData.memory
    const pos = memNode.position.toArray()

    // Focus camera on node
    focusOn(pos)

    emit('doubleClick', memory)

    // Sound feedback
    playTone(880, 0.15, 'sine', 0.2)
  }
}

// Watch for data changes
watch(() => [store.filteredNodes, store.filteredEdges], () => {
  if (isInitialized.value) {
    buildVisualization()
    // Dim ambient when real memories exist
    if (ambientSystem) {
      ambientSystem.setHasRealMemories(store.filteredNodes.length > 0)
    }
  }
}, { deep: true })

// Watch auto rotate
watch(() => props.autoRotate, (val) => {
  setAutoRotate(val)
})

// Flash nexus orb + drive effects on dream phase transitions
watch(() => dreamStore.activePhase, (newPhase) => {
  if (nexusSystem && newPhase >= 0) {
    nexusSystem.flashPhase(newPhase)
  }
  if (effectsSystem) {
    effectsSystem.setPhase(newPhase)
  }
})

// Sync purple auras when dream queue changes
watch(() => dreamStore.dreamQueue, () => {
  if (isInitialized.value) syncAuras()
}, { deep: true })

// Start/stop dream effects when dream cycle begins/ends
watch(() => dreamStore.isRunning, (running, wasRunning) => {
  if (!effectsSystem) return
  if (running && !wasRunning) {
    // Start effects with current memory nodes
    const memNodes = nodeGroup.value ? [...nodeGroup.value.children] : []
    effectsSystem.startDream(memNodes)
  } else if (!running && wasRunning) {
    effectsSystem.completeDream()
  }
})

// Aura breathing animation
let removeAuraCallback = null
let auraTime = 0

function initAuraAnimation() {
  if (removeAuraCallback) return
  removeAuraCallback = addAnimationCallback((dt) => {
    auraTime += dt
    for (const [, aura] of auraMap) {
      const phase = aura.userData.phase || 0
      const breath = 0.08 + 0.06 * Math.sin(auraTime * 1.8 + phase)
      aura.material.opacity = breath
      const scale = 1.0 + 0.08 * Math.sin(auraTime * 1.2 + phase)
      aura.scale.setScalar(scale)
    }
  })
}

// Initialize ambient system once scene is ready
function initAmbient() {
  if (scene.value && !ambientSystem) {
    ambientSystem = new NeuralAmbientSystem(scene.value)
    removeAmbientCallback = addAnimationCallback((dt) => {
      ambientSystem.update(dt)
    })
    // Set initial memory state
    ambientSystem.setHasRealMemories(store.filteredNodes.length > 0)
  }
}

// Initialize dream nexus (alchemy helix at scene center)
function initNexus() {
  if (scene.value && !nexusSystem) {
    nexusSystem = new DreamNexusSystem(scene.value)
    removeNexusCallback = addAnimationCallback((dt) => {
      nexusSystem.update(dt, dreamStore.activePhase, dreamStore.isRunning)
    })
  }
}

// Initialize dream effects engine
function initEffects() {
  if (scene.value && !effectsSystem) {
    effectsSystem = new DreamEffectsSystem(scene.value)
    removeEffectsCallback = addAnimationCallback((dt) => {
      effectsSystem.update(dt)
    })
  }
}

// Lifecycle
onMounted(() => {
  if (containerRef.value) {
    containerRef.value.addEventListener('mousemove', onMouseMove)
    containerRef.value.addEventListener('click', onClick)
    containerRef.value.addEventListener('dblclick', onDoubleClick)
  }

  // Preload agent GLB models (non-blocking — spheres used until loaded)
  agentModels.preloadAll().then(() => {
    // Rebuild with models if scene is ready and has data
    if (isInitialized.value && store.filteredNodes.length > 0) {
      buildVisualization()
    }
  })

  // Build visualization when scene is ready
  if (isInitialized.value) {
    buildVisualization()
    initAmbient()
    initNexus()
    initEffects()
    initAuraAnimation()
  } else {
    // Wait for initialization
    initCheckInterval = setInterval(() => {
      if (isInitialized.value) {
        buildVisualization()
        initAmbient()
        initNexus()
        initEffects()
        initAuraAnimation()
        clearInterval(initCheckInterval)
        initCheckInterval = null
      }
    }, 100)
  }
})

onUnmounted(() => {
  if (initCheckInterval) clearInterval(initCheckInterval)
  if (containerRef.value) {
    containerRef.value.removeEventListener('mousemove', onMouseMove)
    containerRef.value.removeEventListener('click', onClick)
    containerRef.value.removeEventListener('dblclick', onDoubleClick)
  }
  if (removeAmbientCallback) removeAmbientCallback()
  if (ambientSystem) {
    ambientSystem.dispose()
    ambientSystem = null
  }
  if (removeNexusCallback) removeNexusCallback()
  if (nexusSystem) {
    nexusSystem.dispose()
    nexusSystem = null
  }
  if (removeEffectsCallback) removeEffectsCallback()
  if (effectsSystem) {
    effectsSystem.dispose()
    effectsSystem = null
  }
  if (removeAuraCallback) removeAuraCallback()
  for (const [, aura] of auraMap) {
    aura.geometry.dispose()
    aura.material.dispose()
  }
  auraMap.clear()
  agentModels.disposeAll()
})

// Expose methods
defineExpose({
  focusOn,
  buildVisualization,
})
</script>

<template>
  <div ref="containerRef" class="neural-space w-full h-full relative">
    <!-- Loading overlay -->
    <div
      v-if="store.isLoading"
      class="absolute inset-0 bg-black/50 flex items-center justify-center z-10"
    >
      <div class="text-center">
        <AlchemicalLoader size="lg" variant="stone" class="mx-auto mb-4" />
        <p class="text-gray-400">Loading neural space...</p>
      </div>
    </div>

    <!-- Empty state hint (ambient handles visual interest) -->
    <div
      v-if="!store.isLoading && store.filteredNodes.length === 0"
      class="absolute top-4 left-1/2 -translate-x-1/2 z-10 pointer-events-none"
    >
      <p class="text-gray-600 text-sm bg-black/30 px-4 py-2 rounded-full backdrop-blur">
        Neural space awaiting memories...
      </p>
    </div>

    <!-- Hover tooltip -->
    <div
      v-if="store.hoveredMemory"
      class="absolute bottom-4 left-4 bg-apex-dark/90 border border-apex-border rounded-lg p-3 max-w-sm z-10 pointer-events-none"
    >
      <div class="flex items-center gap-2 mb-2">
        <span
          class="w-3 h-3 rounded-full"
          :style="{ backgroundColor: AGENT_COLORS[store.hoveredMemory.agent_id]?.hex || '#888' }"
        ></span>
        <span class="text-xs text-gray-400">{{ store.hoveredMemory.agent_id || 'CLAUDE' }}</span>
        <span class="text-xs text-gray-600">|</span>
        <span class="text-xs text-gray-400">{{ store.hoveredMemory.layer }}</span>
      </div>
      <p class="text-sm text-gray-300 line-clamp-2">
        {{ store.hoveredMemory.content }}
      </p>
    </div>

    <!-- Controls hint -->
    <div class="absolute bottom-4 right-4 text-xs text-gray-600 pointer-events-none">
      Drag to orbit | Scroll to zoom | Click to select | Double-click to focus
    </div>
  </div>
</template>

<style scoped>
.neural-space {
  background: radial-gradient(ellipse at center, #1a1a2e 0%, #0a0a0f 100%);
}
</style>
