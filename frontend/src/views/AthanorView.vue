<script setup>
/**
 * AthanorView — Immersive 3D Chat Experience
 *
 * Full-screen first-person alchemical laboratory.
 * Walk around with WASD + mouse, approach agents, chat via side panel.
 * Desktop-only. The Athanor made manifest.
 *
 * "Enter the Athanor. Walk among the agents. Speak, and be heard."
 */

import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as THREE from 'three'
import { marked } from 'marked'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import { useFirstPerson } from '@/composables/useFirstPerson'
import { useAthanorRoom } from '@/composables/useAthanorRoom'
import AlchemicalLoader from '@/components/ui/AlchemicalLoader.vue'

// ═══════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════

const chat = useChatStore()
const auth = useAuthStore()

const canvasContainer = ref(null)
const messagesContainer = ref(null)
const chatInput = ref(null)

// Scene state
const isReady = ref(false)
const showInstructions = ref(true)

// First-person state (will be populated after init)
const isLocked = ref(false)

// Interaction state
const nearbyAgent = ref(null)
const isChatOpen = ref(false)
const chattingWith = ref(null)
const inputMessage = ref('')

// Three.js refs (not reactive — no Vue Proxy)
let renderer = null
let scene = null
let camera = null
let clock = null
let animId = null
let resizeObserver = null

let firstPerson = null
let athanorRoom = null
let headlamp = null
let headlampTarget = null

// Agent metadata
const AGENT_INFO = {
  AZOTH: { name: 'Azoth', color: '#FFD700', title: 'The Gold Alchemist' },
  ELYSIAN: { name: 'Elysian', color: '#E8B4FF', title: 'The Ethereal Healer' },
  VAJRA: { name: 'Vajra', color: '#4FC3F7', title: 'The Lightning Warrior' },
  KETHER: { name: 'Kether', color: '#AB47BC', title: 'The Mystic Sage' },
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

  // Room animations
  athanorRoom.updateAnimations(delta, elapsed)

  // Proximity check
  if (isLocked.value) {
    nearbyAgent.value = athanorRoom.getAgentAtPosition(camera.position)
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

  renderer.render(scene, camera)
}

// ═══════════════════════════════════════════════════════════════
// INTERACTION
// ═══════════════════════════════════════════════════════════════

function enterAthanor() {
  showInstructions.value = false
  firstPerson.lock()
}

function handleCanvasClick() {
  if (!isChatOpen.value && !showInstructions.value && !isLocked.value) {
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
    if (!showInstructions.value) {
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

// ─── Keyboard shortcuts ───

function onKeyDown(e) {
  // Don't handle when typing
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
    if (e.key === 'Escape') {
      closeChat()
      e.preventDefault()
    }
    return
  }

  if (e.key === 'e' || e.key === 'E') {
    if (isLocked.value && nearbyAgent.value && !isChatOpen.value) {
      openChat(nearbyAgent.value)
      e.preventDefault()
    }
  }

  if (e.key === 'Escape') {
    if (isChatOpen.value) {
      closeChat()
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

  if (animId) cancelAnimationFrame(animId)
  if (resizeObserver) resizeObserver.disconnect()

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

    <!-- Crosshair -->
    <div
      v-if="isLocked && !nearbyAgent"
      class="crosshair"
    />

    <!-- Agent proximity prompt -->
    <div
      v-if="isLocked && nearbyAgent && !isChatOpen"
      class="agent-prompt"
    >
      <div
        class="text-lg font-bold tracking-wide"
        :style="{ color: agentColor, textShadow: `0 0 12px ${agentColor}` }"
      >
        {{ agentName }}
      </div>
      <div class="text-gray-400 text-sm mt-1">
        Press <kbd class="px-1.5 py-0.5 bg-white/10 rounded text-xs text-gold border border-gold/20">E</kbd> to talk
      </div>
    </div>

    <!-- Chat Side Panel -->
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

    <!-- Instructions overlay -->
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
              <div>Talk to agent</div>
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
      Exit Athanor
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

.agent-prompt {
  position: absolute;
  bottom: 28%;
  left: 50%;
  transform: translateX(-50%);
  text-align: center;
  pointer-events: none;
  z-index: 55;
}

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

/* Transitions */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Prose overrides for dark theme */
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
