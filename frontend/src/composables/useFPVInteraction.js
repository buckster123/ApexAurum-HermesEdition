/**
 * useFPVInteraction — Agent Interaction System for FPV Mode
 *
 * Handles proximity detection, E-key conversations, streaming responses
 * projected as HTML overlays, and conversation continuity per agent.
 *
 * "Walk up. Press E. The agent speaks."
 */

import { ref } from 'vue'
import * as THREE from 'three'

// =============================================================================
// CONSTANTS
// =============================================================================

const INTERACTION_RANGE = 5     // Units — how close to trigger prompt
const SOFT_LOCK_SPEED = 1.5     // Radians/sec max nudge rate
const BUBBLE_OFFSET_Y = 3.5     // World units above agent position
const RESPONSE_DISPLAY_MS = 8000 // How long completed response stays visible

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useFPVInteraction() {
  // --- Reactive state (consumed by VillageGUIView template) ---
  const nearestAgent = ref(null)       // { id, distance, color } or null
  const isChatOpen = ref(false)        // Text input is showing
  const isChatStreaming = ref(false)   // Response currently streaming
  const chatInput = ref('')            // Current typed text
  const streamingText = ref('')        // Accumulated response tokens
  const streamingAgentId = ref(null)   // Which agent is responding
  const bubbleScreenPos = ref({ x: 0, y: 0, visible: false })

  // Conversation continuity — one conversationId per agent
  const conversations = {}

  // Internal refs
  let _camera = null
  let _agents = null      // Reference to agents Map from useVillage3D
  let _fpvMode = null     // Reference to useFPVMode instance
  let _renderer = null
  let _displayTimeout = null

  // Bubble world position (not reactive — updated per frame)
  const _bubbleWorldPos = new THREE.Vector3()

  // -------------------------------------------------------------------------
  // INIT
  // -------------------------------------------------------------------------

  function init(camera, renderer, agents, fpvMode) {
    _camera = camera
    _renderer = renderer
    _agents = agents
    _fpvMode = fpvMode
  }

  // -------------------------------------------------------------------------
  // PROXIMITY DETECTION (called every frame in FPV)
  // -------------------------------------------------------------------------

  function updateProximity() {
    if (!_camera || !_agents || isChatOpen.value) return

    const camX = _camera.position.x
    const camZ = _camera.position.z
    let closest = null
    let closestDist = INTERACTION_RANGE

    for (const [id, agent] of _agents.entries()) {
      const pos = agent.group.position
      const dx = camX - pos.x
      const dz = camZ - pos.z
      const dist = Math.sqrt(dx * dx + dz * dz)
      if (dist < closestDist) {
        closestDist = dist
        closest = { id, distance: dist, color: agent.colorHex || agent.color }
      }
    }

    nearestAgent.value = closest
  }

  // -------------------------------------------------------------------------
  // INTERACTION
  // -------------------------------------------------------------------------

  /**
   * Called when E is pressed in FPV mode.
   * Opens chat input if near an agent.
   */
  function beginInteraction() {
    if (!nearestAgent.value || isChatOpen.value || isChatStreaming.value) return

    isChatOpen.value = true
    chatInput.value = ''

    // Unlock pointer for typing (without exiting FPV)
    _fpvMode.unlockForInteraction()
  }

  /**
   * Called when user presses Enter in the chat input.
   * Returns task descriptor for useVillageTasking.executeTask().
   */
  function submitChat() {
    const text = chatInput.value.trim()
    if (!text || !nearestAgent.value) return null

    const agentId = nearestAgent.value.id

    isChatOpen.value = false
    isChatStreaming.value = true
    streamingText.value = ''
    streamingAgentId.value = agentId

    // Clear any pending display timeout
    if (_displayTimeout) {
      clearTimeout(_displayTimeout)
      _displayTimeout = null
    }

    // Re-lock pointer for FPV movement
    _fpvMode.relockAfterInteraction()

    // Build task descriptor
    const agent = _agents?.get(agentId)
    return {
      prompt: text,
      agents: [agentId],
      mode: 'single',
      zone: agent?.currentZone || 'village_square',
      useTools: true,
      conversationId: conversations[agentId] || null,
    }
  }

  /**
   * Called when streaming completes. Stores conversationId for continuity.
   */
  function onStreamComplete(agentId, conversationId) {
    if (conversationId) {
      conversations[agentId] = conversationId
    }
    isChatStreaming.value = false

    // Keep response visible for a while, then fade
    _displayTimeout = setTimeout(() => {
      if (!isChatStreaming.value) {
        streamingText.value = ''
        streamingAgentId.value = null
      }
    }, RESPONSE_DISPLAY_MS)
  }

  /**
   * Called when user presses Escape during chat input.
   */
  function cancelChat() {
    if (isChatOpen.value) {
      isChatOpen.value = false
      chatInput.value = ''
      _fpvMode?.relockAfterInteraction()
    }
  }

  /**
   * Update streaming text (called from watcher on useVillageTasking.streamingContent)
   */
  function updateStreamingText(text) {
    streamingText.value = text
  }

  // -------------------------------------------------------------------------
  // BUBBLE SCREEN PROJECTION (called every frame when bubble visible)
  // -------------------------------------------------------------------------

  function updateBubbleScreenPos() {
    if (!streamingAgentId.value || !_camera || !_renderer) return

    // Track agent position live
    const agent = _agents?.get(streamingAgentId.value)
    if (!agent) return

    _bubbleWorldPos.set(
      agent.group.position.x,
      agent.group.position.y + BUBBLE_OFFSET_Y,
      agent.group.position.z,
    )

    const projected = _bubbleWorldPos.clone().project(_camera)

    const el = _renderer.domElement
    const halfW = el.clientWidth / 2
    const halfH = el.clientHeight / 2

    bubbleScreenPos.value = {
      x: (projected.x * halfW) + halfW,
      y: -(projected.y * halfH) + halfH,
      visible: projected.z > 0 && projected.z < 1, // In front of camera
    }
  }

  // -------------------------------------------------------------------------
  // CAMERA SOFT-LOCK (called every frame during streaming)
  // -------------------------------------------------------------------------

  function applySoftLock(dt) {
    if (!isChatStreaming.value || !streamingAgentId.value || !_camera || !_agents) return

    const agent = _agents.get(streamingAgentId.value)
    if (!agent) return

    // Direction to agent (horizontal)
    const targetDir = new THREE.Vector3()
    targetDir.subVectors(agent.group.position, _camera.position)
    targetDir.y = 0
    if (targetDir.lengthSq() < 0.01) return
    targetDir.normalize()

    // Current forward (horizontal)
    const currentDir = new THREE.Vector3()
    _camera.getWorldDirection(currentDir)
    currentDir.y = 0
    if (currentDir.lengthSq() < 0.01) return
    currentDir.normalize()

    // Only nudge if agent is more than ~15 degrees off-center
    const dot = currentDir.dot(targetDir)
    if (dot > 0.966) return // cos(15deg)

    // Determine rotation direction
    const cross = new THREE.Vector3().crossVectors(currentDir, targetDir)
    const sign = cross.y > 0 ? 1 : -1

    // Very gentle nudge — doesn't fight PointerLockControls
    const nudge = sign * SOFT_LOCK_SPEED * dt * (1 - dot) * 0.3
    _camera.rotation.y += nudge
  }

  // -------------------------------------------------------------------------
  // DISPOSE
  // -------------------------------------------------------------------------

  function dispose() {
    nearestAgent.value = null
    isChatOpen.value = false
    isChatStreaming.value = false
    streamingText.value = ''
    streamingAgentId.value = null
    chatInput.value = ''
    bubbleScreenPos.value = { x: 0, y: 0, visible: false }

    if (_displayTimeout) {
      clearTimeout(_displayTimeout)
      _displayTimeout = null
    }

    _camera = null
    _renderer = null
    _agents = null
    _fpvMode = null
  }

  // -------------------------------------------------------------------------
  // RETURN
  // -------------------------------------------------------------------------

  return {
    // State (read by VillageGUIView template)
    nearestAgent,
    isChatOpen,
    isChatStreaming,
    chatInput,
    streamingText,
    streamingAgentId,
    bubbleScreenPos,

    // Lifecycle
    init,
    dispose,

    // Per-frame updates
    updateProximity,
    updateBubbleScreenPos,
    applySoftLock,

    // Actions
    beginInteraction,
    submitChat,
    cancelChat,
    onStreamComplete,
    updateStreamingText,
  }
}
