<script setup>
/**
 * AthanorView — Immersive 3D Chat Experience
 *
 * Full-screen first-person alchemical laboratory.
 * Walk around with WASD + mouse, approach agents, chat via side panel.
 * Two interactive mirrors: SensorHead (IoT data) and Dream Portal (Backrooms).
 * Desktop-only. The Athanor made manifest.
 *
 * "Enter the Athanor. Walk among the agents. Gaze into the mirrors. Go deeper."
 */

import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as THREE from 'three'
import { marked } from 'marked'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import { useDevicesStore } from '@/stores/devices'
import { useDreamStore } from '@/stores/dream'
import { useFirstPerson } from '@/composables/useFirstPerson'
import { useAthanorRoom } from '@/composables/useAthanorRoom'
import { useBackrooms } from '@/composables/useBackrooms'
import api from '@/services/api'
import AlchemicalLoader from '@/components/ui/AlchemicalLoader.vue'

// ═══════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════

const chat = useChatStore()
const auth = useAuthStore()
const devicesStore = useDevicesStore()
const dreamStore = useDreamStore()

const canvasContainer = ref(null)
const messagesContainer = ref(null)
const chatInput = ref(null)

// Scene state
const isReady = ref(false)
const showInstructions = ref(true)

// First-person state (will be populated after init)
const isLocked = ref(false)

// Interaction state — Agents
const nearbyAgent = ref(null)
const isChatOpen = ref(false)
const chattingWith = ref(null)
const inputMessage = ref('')

// Interaction state — Mirrors
const nearbyMirror = ref(null) // 'SENSOR_HEAD' | 'BACKROOMS' | null

// SensorHead panel
const isSensorOpen = ref(false)
const sensorData = ref(null)
const sensorLoading = ref(false)
const sensorDevice = ref(null)

// Backrooms state
const isInBackrooms = ref(false)
const backroomsDepth = ref(0)
const backroomsFading = ref(false)
const nearExitMirror = ref(false)

// Three.js refs (not reactive — no Vue Proxy)
let renderer = null
let scene = null
let camera = null
let clock = null
let animId = null
let resizeObserver = null

let firstPerson = null
let athanorRoom = null
let backrooms = null
let headlamp = null
let headlampTarget = null
let sensorRefreshTimer = null

// Agent metadata
const AGENT_INFO = {
  AZOTH: { name: 'Azoth', color: '#FFD700', title: 'The Gold Alchemist' },
  ELYSIAN: { name: 'Elysian', color: '#E8B4FF', title: 'The Ethereal Healer' },
  VAJRA: { name: 'Vajra', color: '#4FC3F7', title: 'The Lightning Warrior' },
  KETHER: { name: 'Kether', color: '#AB47BC', title: 'The Mystic Sage' },
}

// Mirror display info
const MIRROR_INFO = {
  SENSOR_HEAD: { label: 'Scrying Glass', action: 'gaze', color: '#4FC3F7' },
  BACKROOMS: { label: 'Dream Portal', action: 'enter', color: '#8B5CF6' },
}

// ═══════════════════════════════════════════════════════════════
// COMPUTED
// ═══════════════════════════════════════════════════════════════

const agentColor = computed(() => {
  return nearbyAgent.value ? AGENT_INFO[nearbyAgent.value]?.color : '#fff'
})

const agentName = computed(() => {
  return nearbyAgent.value ? AGENT_INFO[nearbyAgent.value]?.name : ''
})

const chattingAgentInfo = computed(() => {
  return chattingWith.value ? AGENT_INFO[chattingWith.value] : null
})

const mirrorColor = computed(() => {
  return nearbyMirror.value ? MIRROR_INFO[nearbyMirror.value]?.color : '#fff'
})

const mirrorLabel = computed(() => {
  return nearbyMirror.value ? MIRROR_INFO[nearbyMirror.value]?.label : ''
})

const mirrorAction = computed(() => {
  return nearbyMirror.value ? MIRROR_INFO[nearbyMirror.value]?.action : ''
})

// ═══════════════════════════════════════════════════════════════
// SCENE INIT
// ═══════════════════════════════════════════════════════════════

function initScene() {
  if (!canvasContainer.value) return false

  // WebGL check
  try {
    const testCanvas = document.createElement('canvas')
    if (!testCanvas.getContext('webgl') && !testCanvas.getContext('experimental-webgl')) return false
  } catch { return false }

  const el = canvasContainer.value
  const w = el.clientWidth
  const h = el.clientHeight
  if (w === 0 || h === 0) return false

  try {
    scene = new THREE.Scene()
    clock = new THREE.Clock()

    camera = new THREE.PerspectiveCamera(70, w / h, 0.1, 100)
    camera.position.set(0, 1.6, 6) // Start near entrance

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    renderer.setSize(w, h)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.4
    el.appendChild(renderer.domElement)

    // First-person controls
    firstPerson = useFirstPerson(camera, renderer.domElement)
    firstPerson.init()

    // Sync isLocked ref
    watch(firstPerson.isLocked, (v) => { isLocked.value = v })

    // Build the room
    athanorRoom = useAthanorRoom(scene)
    athanorRoom.buildRoom()

    // Headlamp — SpotLight attached to camera, lights wherever you look
    headlamp = new THREE.SpotLight(0xffeedd, 2.0, 20, Math.PI / 5, 0.4, 1.5)
    headlampTarget = new THREE.Object3D()
    headlampTarget.position.set(0, 0, -1) // forward from camera
    camera.add(headlamp)
    camera.add(headlampTarget)
    headlamp.target = headlampTarget
    headlamp.position.set(0, 0, 0)
    scene.add(camera) // camera must be in scene for children to render

    // Preload agent GLBs then rebuild
    athanorRoom.agentModels.preloadAll().then(() => {
      athanorRoom.rebuildAgents()
    })

    // Resize handling
    resizeObserver = new ResizeObserver(() => handleResize())
    resizeObserver.observe(el)

    isReady.value = true
    return true
  } catch (err) {
    console.warn('[Athanor] Init failed:', err)
    return false
  }
}

// ═══════════════════════════════════════════════════════════════
// ANIMATION LOOP
// ═══════════════════════════════════════════════════════════════

function animate() {
  animId = requestAnimationFrame(animate)
  if (!renderer || !scene || !camera || !clock) return

  const delta = Math.min(clock.getDelta(), 0.1)
  const elapsed = clock.getElapsedTime()

  // Movement
  firstPerson.update(delta)

  if (isInBackrooms.value) {
    // ── Backrooms mode ──
    if (backrooms) {
      backrooms.update(delta, elapsed, camera.position)
      backroomsDepth.value = backrooms.getCurrentDepth()

      // Check exit mirror proximity
      nearExitMirror.value = !!backrooms.getExitMirrorAtPosition(camera.position)
    }
  } else {
    // ── Athanor mode ──
    athanorRoom.updateAnimations(delta, elapsed)

    // Proximity check — agents take priority over mirrors
    if (isLocked.value && !isChatOpen.value && !isSensorOpen.value) {
      const agent = athanorRoom.getAgentAtPosition(camera.position)
      nearbyAgent.value = agent
      nearbyMirror.value = agent ? null : athanorRoom.getMirrorAtPosition(camera.position)
    } else if (!isLocked.value) {
      nearbyAgent.value = null
      nearbyMirror.value = null
    }

    // Agent glow updates
    Object.keys(AGENT_INFO).forEach(id => {
      const isSpeaking = chat.isStreaming && chattingWith.value === id
      const isNearby = nearbyAgent.value === id
      const isChatTarget = isChatOpen.value && chattingWith.value === id

      let target = 0.2 // idle
      if (isSpeaking) target = 1.5
      else if (isChatTarget) target = 0.8
      else if (isNearby) target = 0.6

      const speed = isSpeaking ? 0.08 : 0.04
      athanorRoom.updateAgentGlow(id, target, speed)
    })
  }

  renderer.render(scene, camera)
}

// ═══════════════════════════════════════════════════════════════
// INTERACTION — Agents
// ═══════════════════════════════════════════════════════════════

function enterAthanor() {
  showInstructions.value = false
  firstPerson.lock()
}

function handleCanvasClick() {
  if (!isChatOpen.value && !isSensorOpen.value && !showInstructions.value && !isLocked.value) {
    firstPerson.lock()
  }
}

function openChat(agentId) {
  if (!agentId) return

  chattingWith.value = agentId
  isChatOpen.value = true
  firstPerson.unlock()

  // Create a new conversation if none exists
  if (!chat.currentConversation) {
    chat.createConversation()
  }

  nextTick(() => {
    chatInput.value?.focus()
  })
}

function closeChat() {
  isChatOpen.value = false
  chattingWith.value = null

  // Small delay before re-locking to avoid instant re-open
  setTimeout(() => {
    if (!showInstructions.value && !isSensorOpen.value) {
      firstPerson.lock()
    }
  }, 100)
}

async function sendMessage() {
  const content = inputMessage.value.trim()
  if (!content || chat.isStreaming) return

  inputMessage.value = ''

  try {
    await chat.sendMessage(content, chattingWith.value)
  } catch (err) {
    console.error('[Athanor] Send failed:', err)
  }
}

function renderMarkdown(content) {
  if (!content) return ''
  return marked(content, { breaks: true })
}

// ═══════════════════════════════════════════════════════════════
// INTERACTION — SensorHead Mirror
// ═══════════════════════════════════════════════════════════════

async function openSensorPanel() {
  isSensorOpen.value = true
  firstPerson.unlock()
  sensorLoading.value = true

  // Check for sensor_head device
  try {
    await devicesStore.fetchDevices()
    const device = devicesStore.devices.find(
      d => d.device_type === 'sensor_head' && d.status === 'active'
    )

    if (device) {
      sensorDevice.value = device
      await fetchSensorData(device.id)

      // Auto-refresh every 30s
      sensorRefreshTimer = setInterval(() => fetchSensorData(device.id), 30000)
    } else {
      sensorDevice.value = null
      sensorData.value = null
    }
  } catch (err) {
    console.error('[Athanor] Sensor fetch failed:', err)
    sensorDevice.value = null
    sensorData.value = null
  } finally {
    sensorLoading.value = false
  }
}

async function fetchSensorData(deviceId) {
  try {
    const { data } = await api.get(`/api/v1/devices/${deviceId}/sensors`)
    sensorData.value = data
  } catch {
    sensorData.value = null
  }
}

function iaqLabel(iaq) {
  if (iaq <= 50) return { text: 'Excellent', color: '#4ade80' }
  if (iaq <= 100) return { text: 'Good', color: '#86efac' }
  if (iaq <= 150) return { text: 'Moderate', color: '#facc15' }
  if (iaq <= 200) return { text: 'Poor', color: '#fb923c' }
  return { text: 'Hazardous', color: '#f87171' }
}

async function takeSensorSnapshot() {
  if (!sensorDevice.value) return
  sensorLoading.value = true
  try {
    const { data } = await api.post(`/api/v1/devices/${sensorDevice.value.id}/sensors/snapshot`)
    sensorData.value = { ...sensorData.value, snapshot: data }
  } catch (err) {
    console.error('[Athanor] Snapshot failed:', err)
  } finally {
    sensorLoading.value = false
  }
}

function closeSensorPanel() {
  isSensorOpen.value = false
  sensorData.value = null
  sensorDevice.value = null
  if (sensorRefreshTimer) {
    clearInterval(sensorRefreshTimer)
    sensorRefreshTimer = null
  }

  setTimeout(() => {
    if (!showInstructions.value && !isChatOpen.value) {
      firstPerson.lock()
    }
  }, 100)
}

// ═══════════════════════════════════════════════════════════════
// INTERACTION — Dream Portal / Backrooms
// ═══════════════════════════════════════════════════════════════

async function enterBackrooms() {
  backroomsFading.value = true

  // Fade to black
  await new Promise(r => setTimeout(r, 600))

  // Hide Athanor geometry (not dispose — we'll restore it)
  athanorRoom.hideAll()

  // Fetch dream log for wall text
  let fragments = []
  try {
    await dreamStore.fetchLog(50)
    fragments = dreamStore.log
      .filter(entry => entry.notes)
      .map(entry => entry.notes)
      .concat(
        dreamStore.log
          .filter(entry => entry.phase)
          .map(entry => entry.phase.replace(/_/g, ' '))
      )
  } catch (err) {
    console.error('[Athanor] Dream log fetch failed:', err)
  }

  // Build the backrooms
  backrooms = useBackrooms(scene)
  backrooms.build(fragments)

  // Reset camera to corridor start
  camera.position.set(0, 1.6, 0)

  // Disable room bounds, use corridor collision instead
  firstPerson.setBounds(null)
  firstPerson.setClampFunction((pos) => backrooms.clampPosition(pos))

  // Dim headlamp for backrooms atmosphere
  if (headlamp) headlamp.intensity = 1.0

  isInBackrooms.value = true
  backroomsDepth.value = 0
  backroomsFading.value = false

  // Re-lock pointer
  setTimeout(() => firstPerson.lock(), 100)
}

function exitBackrooms() {
  backroomsFading.value = true

  setTimeout(() => {
    // Dispose backrooms geometry
    if (backrooms) {
      backrooms.dispose()
      backrooms = null
    }

    // Restore Athanor
    athanorRoom.showAll()

    // Reset camera near the portal
    camera.position.set(0, 1.6, 6)

    // Restore room bounds
    firstPerson.setBounds({ x: 9, z: 7 })
    firstPerson.setClampFunction(null)

    // Restore Athanor fog + background
    scene.fog = new THREE.FogExp2(0x0a0612, 0.018)
    scene.background = new THREE.Color(0x0a0612)

    // Restore headlamp intensity
    if (headlamp) headlamp.intensity = 2.0

    isInBackrooms.value = false
    backroomsDepth.value = 0
    nearExitMirror.value = false
    backroomsFading.value = false

    // Re-lock pointer
    setTimeout(() => firstPerson.lock(), 100)
  }, 600)
}

// ═══════════════════════════════════════════════════════════════
// KEYBOARD
// ═══════════════════════════════════════════════════════════════

function onKeyDown(e) {
  // Don't handle when typing in inputs
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
    if (e.key === 'Escape') {
      closeChat()
      e.preventDefault()
    }
    return
  }

  if (e.key === 'e' || e.key === 'E') {
    if (!isLocked.value) return

    if (isInBackrooms.value) {
      // In backrooms: E on exit mirror → leave
      if (nearExitMirror.value) {
        exitBackrooms()
        e.preventDefault()
      }
    } else {
      // In Athanor: agents > mirrors
      if (nearbyAgent.value && !isChatOpen.value && !isSensorOpen.value) {
        openChat(nearbyAgent.value)
        e.preventDefault()
      } else if (nearbyMirror.value === 'SENSOR_HEAD' && !isChatOpen.value && !isSensorOpen.value) {
        openSensorPanel()
        e.preventDefault()
      } else if (nearbyMirror.value === 'BACKROOMS' && !isChatOpen.value && !isSensorOpen.value) {
        enterBackrooms()
        e.preventDefault()
      }
    }
  }

  if (e.key === 'Escape') {
    if (isChatOpen.value) {
      closeChat()
      e.preventDefault()
    } else if (isSensorOpen.value) {
      closeSensorPanel()
      e.preventDefault()
    }
  }
}

// ═══════════════════════════════════════════════════════════════
// SCROLL & RESIZE
// ═══════════════════════════════════════════════════════════════

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// Auto-scroll on new messages
watch(() => chat.messages.length, () => {
  nextTick(scrollToBottom)
})

watch(() => chat.streamingContent, () => {
  nextTick(scrollToBottom)
})

function handleResize() {
  if (!canvasContainer.value || !camera || !renderer) return
  const w = canvasContainer.value.clientWidth
  const h = canvasContainer.value.clientHeight
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
}

// ═══════════════════════════════════════════════════════════════
// LIFECYCLE
// ═══════════════════════════════════════════════════════════════

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)

  if (initScene()) {
    animate()
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)

  if (sensorRefreshTimer) clearInterval(sensorRefreshTimer)
  if (animId) cancelAnimationFrame(animId)
  if (resizeObserver) resizeObserver.disconnect()

  if (backrooms) backrooms.dispose()
  if (firstPerson) firstPerson.dispose()
  if (athanorRoom) {
    athanorRoom.dispose()
    athanorRoom.agentModels.disposeAll()
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
    if (canvasContainer.value && renderer.domElement) {
      canvasContainer.value.removeChild(renderer.domElement)
    }
  }

  renderer = null
  scene = null
  camera = null
  clock = null
})
</script>

<template>
  <div class="athanor-view fixed inset-0 z-50 bg-[#0a0612]">
    <!-- 3D Canvas -->
    <div
      ref="canvasContainer"
      class="absolute inset-0"
      @click="handleCanvasClick"
    />

    <!-- Crosshair (changes color in backrooms) -->
    <div
      v-if="isLocked && !nearbyAgent && !nearbyMirror && !nearExitMirror"
      class="crosshair"
      :class="{ 'crosshair--backrooms': isInBackrooms }"
    />

    <!-- ═══ ATHANOR MODE HUD ═══ -->

    <!-- Agent proximity prompt -->
    <div
      v-if="isLocked && nearbyAgent && !isChatOpen && !isSensorOpen && !isInBackrooms"
      class="interaction-prompt"
    >
      <div
        class="text-lg font-bold tracking-wide"
        :style="{ color: agentColor, textShadow: `0 0 12px ${agentColor}` }"
      >
        {{ agentName }}
      </div>
      <div class="text-gray-400 text-sm mt-1">
        Press <kbd class="kbd">E</kbd> to talk
      </div>
    </div>

    <!-- Mirror proximity prompt -->
    <div
      v-if="isLocked && nearbyMirror && !nearbyAgent && !isChatOpen && !isSensorOpen && !isInBackrooms"
      class="interaction-prompt"
    >
      <div
        class="text-lg font-bold tracking-wide"
        :style="{ color: mirrorColor, textShadow: `0 0 12px ${mirrorColor}` }"
      >
        {{ mirrorLabel }}
      </div>
      <div class="text-gray-400 text-sm mt-1">
        Press <kbd class="kbd">E</kbd> to {{ mirrorAction }}
      </div>
    </div>

    <!-- ═══ BACKROOMS MODE HUD ═══ -->

    <!-- Depth counter -->
    <div v-if="isInBackrooms && isLocked" class="backrooms-hud">
      <div class="backrooms-depth">DEPTH {{ backroomsDepth }}</div>
      <div v-if="backroomsDepth >= 5 && !nearExitMirror" class="backrooms-hint">
        "find the mirror"
      </div>
    </div>

    <!-- Exit mirror prompt -->
    <div
      v-if="isInBackrooms && isLocked && nearExitMirror"
      class="interaction-prompt"
    >
      <div
        class="text-lg font-bold tracking-wide"
        style="color: #8B5CF6; text-shadow: 0 0 16px #8B5CF6"
      >
        Exit Portal
      </div>
      <div class="text-gray-400 text-sm mt-1">
        Press <kbd class="kbd kbd--violet">E</kbd> to return to the Athanor
      </div>
    </div>

    <!-- ═══ FADE OVERLAY (Backrooms transition) ═══ -->
    <Transition name="fade-fast">
      <div v-if="backroomsFading" class="fade-overlay" />
    </Transition>

    <!-- ═══ CHAT SIDE PANEL (right) ═══ -->
    <Transition name="slide-right">
      <div v-if="isChatOpen" class="chat-panel">
        <!-- Header -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-gold/10">
          <div class="flex items-center gap-3">
            <div
              class="w-3 h-3 rounded-full"
              :style="{ backgroundColor: chattingAgentInfo?.color, boxShadow: `0 0 8px ${chattingAgentInfo?.color}` }"
            />
            <div>
              <div class="text-sm font-semibold text-white">{{ chattingAgentInfo?.name }}</div>
              <div class="text-[10px] text-gray-500">{{ chattingAgentInfo?.title }}</div>
            </div>
          </div>
          <button
            @click="closeChat"
            class="text-gray-500 hover:text-white transition-colors text-xs px-2 py-1 rounded bg-white/5 hover:bg-white/10"
          >
            ESC
          </button>
        </div>

        <!-- Messages -->
        <div ref="messagesContainer" class="messages-scroll flex-1 overflow-y-auto px-4 py-3 space-y-3">
          <div
            v-for="msg in chat.messages"
            :key="msg.id"
            class="message"
          >
            <!-- User message -->
            <div
              v-if="msg.role === 'user'"
              class="flex justify-end"
            >
              <div class="user-msg max-w-[85%] px-3 py-2 rounded-lg bg-gold/10 border border-gold/15 text-sm text-gray-200">
                {{ msg.content }}
              </div>
            </div>

            <!-- Assistant message -->
            <div
              v-else-if="msg.role === 'assistant'"
              class="flex justify-start"
            >
              <div class="agent-msg max-w-[90%]">
                <!-- Thinking (collapsible) -->
                <details v-if="msg.thinking" class="mb-2">
                  <summary class="text-[10px] text-gray-500 cursor-pointer hover:text-gray-400">
                    Show reasoning
                  </summary>
                  <div
                    class="mt-1 text-xs text-gray-500 border-l border-gray-700 pl-2 prose prose-invert prose-xs max-w-none"
                    v-html="renderMarkdown(msg.thinking)"
                  />
                </details>

                <!-- Content -->
                <div
                  class="text-sm text-gray-300 prose prose-invert prose-sm max-w-none"
                  v-html="renderMarkdown(msg.content)"
                />
              </div>
            </div>
          </div>

          <!-- Streaming indicator -->
          <div v-if="chat.isStreaming" class="flex items-center gap-2 text-xs text-gold/60 py-1">
            <AlchemicalLoader size="sm" variant="ouroboros" />
            <span v-if="chat.currentToolExecution">Using {{ chat.currentToolExecution.name }}...</span>
          </div>

          <!-- Empty state -->
          <div
            v-if="chat.messages.length === 0"
            class="flex flex-col items-center justify-center h-full text-gray-600 text-sm"
          >
            <div class="text-2xl mb-2" :style="{ color: chattingAgentInfo?.color }">
              &bull;
            </div>
            <p>Speak to {{ chattingAgentInfo?.name }}.</p>
            <p class="text-xs text-gray-700 mt-1">{{ chattingAgentInfo?.title }}</p>
          </div>
        </div>

        <!-- Input -->
        <div class="px-4 py-3 border-t border-gold/10">
          <div class="flex gap-2">
            <input
              ref="chatInput"
              v-model="inputMessage"
              @keydown.enter.prevent="sendMessage"
              :placeholder="`Speak to ${chattingAgentInfo?.name || 'the agent'}...`"
              :disabled="chat.isStreaming"
              class="flex-1 bg-white/5 border border-gold/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-gold/30 focus:ring-1 focus:ring-gold/20 transition-colors"
            />
            <button
              @click="sendMessage"
              :disabled="chat.isStreaming || !inputMessage.trim()"
              class="px-4 py-2 bg-gold/15 hover:bg-gold/25 border border-gold/20 rounded-lg text-sm text-gold disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ═══ SENSOR PANEL (left) ═══ -->
    <Transition name="slide-left">
      <div v-if="isSensorOpen" class="sensor-panel">
        <!-- Header -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-cyan-500/10">
          <div class="flex items-center gap-3">
            <div class="w-3 h-3 rounded-full bg-cyan-400" style="box-shadow: 0 0 8px #4fc3f7" />
            <div>
              <div class="text-sm font-semibold text-white">Scrying Glass</div>
              <div class="text-[10px] text-gray-500">SensorHead Telemetry</div>
            </div>
          </div>
          <button
            @click="closeSensorPanel"
            class="text-gray-500 hover:text-white transition-colors text-xs px-2 py-1 rounded bg-white/5 hover:bg-white/10"
          >
            ESC
          </button>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-y-auto px-4 py-4">
          <!-- Loading -->
          <div v-if="sensorLoading" class="flex flex-col items-center justify-center h-full">
            <AlchemicalLoader size="md" variant="ouroboros" />
            <p class="text-gray-500 text-xs mt-3">Scrying...</p>
          </div>

          <!-- No device -->
          <div v-else-if="!sensorDevice" class="flex flex-col items-center justify-center h-full text-center">
            <div class="text-4xl mb-4 opacity-30">&#x1f56e;</div>
            <p class="text-gray-400 text-sm font-medium">Mirror Dormant</p>
            <p class="text-gray-600 text-xs mt-2 max-w-[200px]">
              Connect a SensorHead device to awaken the scrying glass.
            </p>
          </div>

          <!-- Sensor data -->
          <div v-else class="space-y-3">
            <!-- Device status header -->
            <div class="flex items-center gap-2 mb-3">
              <div
                class="w-2 h-2 rounded-full"
                :class="sensorData?.online ? 'bg-green-400 animate-pulse' : 'bg-gray-500'"
              />
              <span class="text-xs text-gray-400">{{ sensorData?.device_name || sensorDevice.device_name }}</span>
              <span v-if="sensorData?.online" class="text-[10px] text-green-400/60 ml-auto">LIVE</span>
              <span v-else class="text-[10px] text-yellow-500/60 ml-auto">CACHED</span>
            </div>

            <!-- Telemetry readings -->
            <template v-if="sensorData?.telemetry?.readings">
              <!-- Temperature -->
              <div v-if="sensorData.telemetry.readings.temperature_c != null" class="sensor-gauge">
                <div class="flex items-center justify-between">
                  <span class="text-xs text-gray-400 uppercase tracking-wider">Temperature</span>
                  <span class="text-sm font-mono text-cyan-300">{{ sensorData.telemetry.readings.temperature_c.toFixed(1) }}&deg;C</span>
                </div>
                <div class="mt-1 h-1 bg-white/5 rounded-full overflow-hidden">
                  <div class="h-full bg-gradient-to-r from-blue-600 to-red-400 rounded-full transition-all duration-500"
                    :style="{ width: Math.min(100, Math.max(5, (sensorData.telemetry.readings.temperature_c / 50) * 100)) + '%' }" />
                </div>
              </div>

              <!-- Humidity -->
              <div v-if="sensorData.telemetry.readings.humidity_pct != null" class="sensor-gauge">
                <div class="flex items-center justify-between">
                  <span class="text-xs text-gray-400 uppercase tracking-wider">Humidity</span>
                  <span class="text-sm font-mono text-cyan-300">{{ Math.round(sensorData.telemetry.readings.humidity_pct) }}%</span>
                </div>
                <div class="mt-1 h-1 bg-white/5 rounded-full overflow-hidden">
                  <div class="h-full bg-gradient-to-r from-cyan-600 to-cyan-400 rounded-full transition-all duration-500"
                    :style="{ width: sensorData.telemetry.readings.humidity_pct + '%' }" />
                </div>
              </div>

              <!-- Pressure -->
              <div v-if="sensorData.telemetry.readings.pressure_hpa != null" class="sensor-gauge">
                <div class="flex items-center justify-between">
                  <span class="text-xs text-gray-400 uppercase tracking-wider">Pressure</span>
                  <span class="text-sm font-mono text-cyan-300">{{ Math.round(sensorData.telemetry.readings.pressure_hpa) }} hPa</span>
                </div>
              </div>

              <!-- IAQ (color-coded) -->
              <div v-if="sensorData.telemetry.readings.iaq != null" class="sensor-gauge">
                <div class="flex items-center justify-between">
                  <span class="text-xs text-gray-400 uppercase tracking-wider">Air Quality</span>
                  <div class="flex items-center gap-2">
                    <span class="text-[10px] font-medium" :style="{ color: iaqLabel(sensorData.telemetry.readings.iaq).color }">
                      {{ iaqLabel(sensorData.telemetry.readings.iaq).text }}
                    </span>
                    <span class="text-sm font-mono text-cyan-300">{{ Math.round(sensorData.telemetry.readings.iaq) }}</span>
                  </div>
                </div>
                <div class="mt-1 h-1 bg-white/5 rounded-full overflow-hidden">
                  <div class="h-full rounded-full transition-all duration-500"
                    :style="{ width: Math.min(100, (sensorData.telemetry.readings.iaq / 300) * 100) + '%', backgroundColor: iaqLabel(sensorData.telemetry.readings.iaq).color }" />
                </div>
              </div>

              <!-- CO2 -->
              <div v-if="sensorData.telemetry.readings.co2_ppm != null" class="sensor-gauge">
                <div class="flex items-center justify-between">
                  <span class="text-xs text-gray-400 uppercase tracking-wider">CO2</span>
                  <span class="text-sm font-mono text-cyan-300">{{ Math.round(sensorData.telemetry.readings.co2_ppm) }} ppm</span>
                </div>
              </div>

              <!-- VOC -->
              <div v-if="sensorData.telemetry.readings.voc_ppm != null" class="sensor-gauge">
                <div class="flex items-center justify-between">
                  <span class="text-xs text-gray-400 uppercase tracking-wider">VOC</span>
                  <span class="text-sm font-mono text-cyan-300">{{ sensorData.telemetry.readings.voc_ppm.toFixed(2) }} ppm</span>
                </div>
              </div>

              <!-- Data age -->
              <div v-if="sensorData.telemetry.age_s != null" class="text-[10px] text-gray-600 text-right mt-2">
                {{ sensorData.telemetry.age_s < 60 ? sensorData.telemetry.age_s + 's ago' : Math.round(sensorData.telemetry.age_s / 60) + 'm ago' }}
                <span class="ml-1 text-gray-700">({{ sensorData.telemetry.source }})</span>
              </div>
            </template>

            <!-- Snapshot images -->
            <template v-if="sensorData?.snapshot">
              <div class="border-t border-cyan-500/10 pt-3 mt-3">
                <div class="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Vision</div>
                <div class="space-y-2">
                  <img v-if="sensorData.snapshot.visual_base64" :src="'data:image/jpeg;base64,' + sensorData.snapshot.visual_base64" class="w-full rounded border border-cyan-500/10 aspect-[4/3] object-cover" />
                  <img v-if="sensorData.snapshot.night_base64" :src="'data:image/jpeg;base64,' + sensorData.snapshot.night_base64" class="w-full rounded border border-green-500/10 aspect-[4/3] object-cover" />
                  <img v-if="sensorData.snapshot.thermal_base64" :src="'data:image/jpeg;base64,' + sensorData.snapshot.thermal_base64" class="w-full rounded border border-red-500/10 aspect-[4/3] object-cover" />
                </div>
              </div>
            </template>

            <!-- Snapshot button -->
            <button
              v-if="sensorData?.online"
              @click="takeSensorSnapshot"
              :disabled="sensorLoading"
              class="w-full mt-3 px-3 py-2 bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/15 rounded-lg text-xs text-cyan-300 disabled:opacity-30 transition-colors"
            >
              {{ sensorLoading ? 'Capturing...' : 'Capture Snapshot' }}
            </button>

            <!-- No telemetry data yet -->
            <div v-if="!sensorData?.telemetry?.readings" class="text-center py-8">
              <p class="text-gray-500 text-xs">Device connected but no telemetry received yet.</p>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ═══ INSTRUCTIONS OVERLAY ═══ -->
    <Transition name="fade">
      <div v-if="showInstructions && isReady" class="instructions-overlay">
        <div class="text-center max-w-md mx-auto">
          <h1 class="text-3xl font-bold text-gold mb-2" style="text-shadow: 0 0 20px rgba(212,175,55,0.5)">
            The Athanor
          </h1>
          <p class="text-gray-400 text-sm mb-6">
            Walk the alchemical halls. Seek the agents at their stations.
          </p>

          <div class="grid grid-cols-2 gap-3 text-xs text-gray-500 mb-8">
            <div class="bg-white/5 rounded-lg p-3 border border-white/5">
              <div class="text-white font-mono mb-1">WASD</div>
              <div>Move</div>
            </div>
            <div class="bg-white/5 rounded-lg p-3 border border-white/5">
              <div class="text-white font-mono mb-1">Mouse</div>
              <div>Look around</div>
            </div>
            <div class="bg-white/5 rounded-lg p-3 border border-white/5">
              <div class="text-white font-mono mb-1">E</div>
              <div>Talk / Interact</div>
            </div>
            <div class="bg-white/5 rounded-lg p-3 border border-white/5">
              <div class="text-white font-mono mb-1">ESC</div>
              <div>Close / Exit</div>
            </div>
          </div>

          <button
            @click="enterAthanor"
            class="px-8 py-3 bg-gold/20 hover:bg-gold/30 border border-gold/30 rounded-lg text-gold font-semibold transition-all hover:scale-105"
            style="text-shadow: 0 0 8px rgba(212,175,55,0.4)"
          >
            Enter the Athanor
          </button>
        </div>
      </div>
    </Transition>

    <!-- Loading state -->
    <div
      v-if="!isReady"
      class="absolute inset-0 flex items-center justify-center"
    >
      <div class="text-center">
        <AlchemicalLoader size="lg" variant="stone" />
        <p class="text-gray-500 text-sm mt-4">Kindling the forge...</p>
      </div>
    </div>

    <!-- Exit button -->
    <router-link
      v-if="!showInstructions"
      to="/chat"
      class="fixed top-4 left-4 z-[60] px-3 py-1.5 bg-black/60 backdrop-blur border border-white/10 rounded-lg text-xs text-gray-400 hover:text-white hover:border-white/20 transition-colors"
    >
      {{ isInBackrooms ? 'Find the mirror...' : 'Exit Athanor' }}
    </router-link>
  </div>
</template>

<style scoped>
.crosshair {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(212, 175, 55, 0.7);
  box-shadow: 0 0 6px rgba(212, 175, 55, 0.4);
  pointer-events: none;
  z-index: 55;
}
.crosshair--backrooms {
  background: rgba(204, 170, 68, 0.5);
  box-shadow: 0 0 4px rgba(204, 170, 68, 0.3);
}

.interaction-prompt {
  position: absolute;
  bottom: 28%;
  left: 50%;
  transform: translateX(-50%);
  text-align: center;
  pointer-events: none;
  z-index: 55;
}

.kbd {
  padding: 2px 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  font-size: 11px;
  color: #d4af37;
  border: 1px solid rgba(212, 175, 55, 0.2);
}
.kbd--violet {
  color: #8b5cf6;
  border-color: rgba(139, 92, 246, 0.3);
}

/* ── Chat panel (slides from right) ── */
.chat-panel {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 40%;
  max-width: 500px;
  min-width: 320px;
  background: rgba(10, 6, 18, 0.94);
  backdrop-filter: blur(16px);
  border-left: 1px solid rgba(212, 175, 55, 0.1);
  display: flex;
  flex-direction: column;
  z-index: 56;
}

/* ── Sensor panel (slides from left) ── */
.sensor-panel {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 35%;
  max-width: 400px;
  min-width: 280px;
  background: rgba(6, 12, 18, 0.94);
  backdrop-filter: blur(16px);
  border-right: 1px solid rgba(79, 195, 247, 0.1);
  display: flex;
  flex-direction: column;
  z-index: 56;
}

.sensor-gauge {
  padding: 8px 10px;
  background: rgba(79, 195, 247, 0.03);
  border: 1px solid rgba(79, 195, 247, 0.06);
  border-radius: 6px;
}

.instructions-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(10, 6, 18, 0.85);
  backdrop-filter: blur(8px);
  z-index: 58;
}

/* ── Backrooms HUD ── */
.backrooms-hud {
  position: absolute;
  top: 16px;
  right: 16px;
  text-align: right;
  pointer-events: none;
  z-index: 55;
}
.backrooms-depth {
  font-family: monospace;
  font-size: 14px;
  color: rgba(204, 170, 68, 0.6);
  letter-spacing: 0.15em;
  text-shadow: 0 0 8px rgba(204, 170, 68, 0.2);
}
.backrooms-hint {
  font-family: monospace;
  font-size: 11px;
  color: rgba(139, 92, 246, 0.5);
  margin-top: 4px;
  animation: hint-pulse 3s ease-in-out infinite;
}
@keyframes hint-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.8; }
}

/* ── Fade overlay for backrooms transition ── */
.fade-overlay {
  position: absolute;
  inset: 0;
  background: #000;
  z-index: 57;
}

/* ── Transitions ── */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
}

.slide-left-enter-active,
.slide-left-leave-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-left-enter-from,
.slide-left-leave-to {
  transform: translateX(-100%);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.fade-fast-enter-active {
  transition: opacity 0.4s ease;
}
.fade-fast-leave-active {
  transition: opacity 0.3s ease;
}
.fade-fast-enter-from,
.fade-fast-leave-to {
  opacity: 0;
}

/* ── Prose overrides ── */
.chat-panel :deep(pre) {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  overflow-x: auto;
}

.chat-panel :deep(code) {
  color: #ffd700;
  font-size: 12px;
}

.chat-panel :deep(a) {
  color: #4fc3f7;
}

.messages-scroll::-webkit-scrollbar {
  width: 4px;
}
.messages-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.messages-scroll::-webkit-scrollbar-thumb {
  background: rgba(212, 175, 55, 0.15);
  border-radius: 2px;
}
</style>
