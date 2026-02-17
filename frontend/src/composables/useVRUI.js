/**
 * useVRUI -- Spatial VR UI Panels (Phase 19)
 *
 * Floating CanvasTexture-based panels visible inside the VR headset.
 * Four panel types: Agent Info, Zone Info, Chat (streaming), Wrist HUD.
 * Billboard behavior via lookAt(camera). Texture re-upload only when
 * content changes (markDirty pattern). Follows the same CanvasTexture
 * approach used in useVillage3D.js (agent name sprites, speech bubbles,
 * zone labels).
 *
 * "Knowledge floats where the eye wanders"
 */

import * as THREE from 'three'

// =============================================================================
// CONSTANTS
// =============================================================================

const PANEL_WIDTH = 0.6 // meters
const PANEL_HEIGHT = 0.4 // meters
const PANEL_CANVAS_W = 512 // pixels (power of 2 for GPU)
const PANEL_CANVAS_H = 340 // pixels
const CHAT_PANEL_HEIGHT = 0.55 // taller for streaming text
const CHAT_CANVAS_H = 470 // pixels
const PANEL_DISTANCE = 1.5 // meters in front of headset
const PANEL_Y_OFFSET = -0.15 // slightly below eye level
const INFO_TIMEOUT = 8000 // ms before auto-hide (info panels)
const WRIST_HUD_SIZE = 0.08 // meters
const WRIST_HUD_CANVAS = 128 // pixels

// =============================================================================
// STATIC DATA
// =============================================================================

const AGENT_FLAVORS = {
  AZOTH: { title: 'The Gold Alchemist', flavor: 'Master of transformation and synthesis' },
  KETHER: { title: 'The Mystic Sage', flavor: 'Keeper of hidden knowledge' },
  VAJRA: { title: 'The Lightning Warrior', flavor: 'Swift analyzer and executor' },
  ELYSIAN: { title: 'The Ethereal Healer', flavor: 'Harmonizer of discord' },
}

const AGENT_COLORS = {
  AZOTH: '#FFD700',
  KETHER: '#a29bfe',
  VAJRA: '#fd79a8',
  ELYSIAN: '#00b894',
}

const ZONE_INFO = {
  village_square: { desc: 'Central hub -- all tools available', tools: ['All'] },
  workshop: { desc: 'Crafting & file manipulation', tools: ['Utility', 'Files'] },
  library: { desc: 'Research and web exploration', tools: ['Web', 'Browser'] },
  dj_booth: { desc: 'Music generation & creative tools', tools: ['Music', 'Creative'] },
  memory_garden: { desc: 'Long-term memory operations', tools: ['Memory'] },
  file_shed: { desc: 'File storage and management', tools: ['Files', 'Utility'] },
  bridge_portal: { desc: 'Cross-village portal connections', tools: ['Web', 'Agent'] },
  watchtower: { desc: 'Monitoring and web utilities', tools: ['Utility', 'Web'] },
  arena: { desc: 'Competitive challenges', tools: ['Arena'] },
  bazaar: { desc: 'Trading and marketplace', tools: ['Commerce'] },
  apothecary: { desc: 'Alchemical experimentation', tools: ['Alchemy'] },
  nexus_tower: { desc: 'Advanced computational nexus', tools: ['Compute'] },
  mines: { desc: 'Deep data mining operations', tools: ['Mining'] },
  sanctum: { desc: 'Inner sanctum -- advanced rituals', tools: ['Sacred'] },
}

// =============================================================================
// CANVAS RENDERING HELPERS
// =============================================================================

function _drawRoundedRect(ctx, x, y, w, h, r, fillStyle, strokeStyle) {
  ctx.fillStyle = fillStyle
  ctx.beginPath()
  ctx.roundRect(x, y, w, h, r)
  ctx.fill()
  if (strokeStyle) {
    ctx.strokeStyle = strokeStyle
    ctx.lineWidth = 1.5
    ctx.stroke()
  }
}

function _drawAccentBar(ctx, y, canvasW, color) {
  ctx.fillStyle = color
  ctx.fillRect(16, y, canvasW - 32, 3)
}

/**
 * Word-wrap text onto the canvas. Returns the number of lines drawn.
 */
function _wrapText(ctx, text, x, y, maxWidth, lineHeight) {
  const words = text.split(' ')
  let line = ''
  let lines = 0
  for (const word of words) {
    const test = line + word + ' '
    if (ctx.measureText(test).width > maxWidth && line !== '') {
      ctx.fillText(line.trim(), x, y + lines * lineHeight)
      line = word + ' '
      lines++
    } else {
      line = test
    }
  }
  ctx.fillText(line.trim(), x, y + lines * lineHeight)
  lines++
  return lines
}

// =============================================================================
// VRPanel CLASS
// =============================================================================

class VRPanel {
  /**
   * @param {object} opts
   * @param {number} opts.width       Panel world width in meters
   * @param {number} opts.height      Panel world height in meters
   * @param {number} opts.canvasW     Canvas pixel width
   * @param {number} opts.canvasH     Canvas pixel height
   * @param {boolean} [opts.billboard] Billboard toward camera each frame (default true)
   * @param {number} [opts.timeout]   Auto-hide after ms (0 = manual hide)
   */
  constructor({ width, height, canvasW, canvasH, billboard = true, timeout = 0 }) {
    this.canvas = document.createElement('canvas')
    this.canvas.width = canvasW
    this.canvas.height = canvasH
    this.ctx = this.canvas.getContext('2d')

    this.texture = new THREE.CanvasTexture(this.canvas)
    this.texture.minFilter = THREE.LinearFilter
    this.texture.generateMipmaps = false

    this.material = new THREE.MeshBasicMaterial({
      map: this.texture,
      transparent: true,
      side: THREE.DoubleSide,
      depthTest: true,
    })

    this.geometry = new THREE.PlaneGeometry(width, height)
    this.mesh = new THREE.Mesh(this.geometry, this.material)
    this.mesh.renderOrder = 100
    this.mesh.userData = { type: 'vr-panel' }

    this.billboard = billboard
    this.timeout = timeout
    this._dirty = false
    this._showTime = 0
    this._scene = null
  }

  show(scene, position) {
    if (this._scene) this.hide()
    this._scene = scene
    this.mesh.position.copy(position)
    scene.add(this.mesh)
    this._showTime = performance.now()
  }

  hide() {
    if (this._scene) {
      this._scene.remove(this.mesh)
      this._scene = null
    }
  }

  get isVisible() {
    return this._scene !== null
  }

  markDirty() {
    this._dirty = true
  }

  /**
   * Called every frame. Handles billboard rotation, auto-hide timeout,
   * and deferred texture upload.
   * @param {THREE.Camera} camera
   * @param {number} dt  delta time in seconds (unused but available)
   * @param {THREE.Vector3} tempVec  pre-allocated scratch vector
   */
  update(camera, dt, tempVec) {
    if (!this.isVisible) return

    // Billboard
    if (this.billboard) {
      camera.getWorldPosition(tempVec)
      this.mesh.lookAt(tempVec)
    }

    // Auto-hide timeout
    if (this.timeout > 0 && performance.now() - this._showTime > this.timeout) {
      this.hide()
      return
    }

    // Deferred texture upload
    if (this._dirty) {
      this.texture.needsUpdate = true
      this._dirty = false
    }
  }

  dispose() {
    this.hide()
    this.texture.dispose()
    this.material.dispose()
    this.geometry.dispose()
  }
}

// =============================================================================
// PANEL CONTENT RENDERERS
// =============================================================================

function _renderAgentInfo(panel, agentId, currentZone, color) {
  const ctx = panel.ctx
  const w = panel.canvas.width
  const h = panel.canvas.height
  const info = AGENT_FLAVORS[agentId] || { title: 'Unknown', flavor: '' }

  // Clear
  ctx.clearRect(0, 0, w, h)

  // Background
  _drawRoundedRect(ctx, 8, 8, w - 16, h - 16, 12, 'rgba(10, 10, 20, 0.9)', 'rgba(255,255,255,0.1)')

  // Accent bar
  _drawAccentBar(ctx, 24, w, color)

  // Agent name
  ctx.fillStyle = color
  ctx.font = 'bold 28px sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'top'
  ctx.fillText(agentId, 28, 40)

  // Title
  ctx.fillStyle = '#999999'
  ctx.font = '18px sans-serif'
  ctx.fillText(info.title, 28, 76)

  // Zone
  const zonePretty = currentZone ? currentZone.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : 'Unknown'
  ctx.fillStyle = '#ffffff'
  ctx.font = '16px sans-serif'
  ctx.fillText('Zone: ' + zonePretty, 28, 110)

  // Flavor text
  ctx.fillStyle = '#777777'
  ctx.font = 'italic 14px sans-serif'
  _wrapText(ctx, info.flavor, 28, 148, w - 56, 20)

  panel.markDirty()
}

function _renderZoneInfo(panel, zoneName, label, color) {
  const ctx = panel.ctx
  const w = panel.canvas.width
  const h = panel.canvas.height
  const info = ZONE_INFO[zoneName] || { desc: 'Uncharted territory', tools: [] }

  // Clear
  ctx.clearRect(0, 0, w, h)

  // Background
  _drawRoundedRect(ctx, 8, 8, w - 16, h - 16, 12, 'rgba(10, 10, 20, 0.9)', 'rgba(255,255,255,0.1)')

  // Accent bar
  _drawAccentBar(ctx, 24, w, color)

  // Zone label
  ctx.fillStyle = '#ffffff'
  ctx.font = 'bold 26px sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'top'
  ctx.fillText(label || zoneName, 28, 40)

  // Description
  ctx.fillStyle = '#aaaaaa'
  ctx.font = '16px sans-serif'
  _wrapText(ctx, info.desc, 28, 82, w - 56, 22)

  // Tool category pills
  let pillX = 28
  const pillY = 140
  ctx.font = 'bold 13px sans-serif'
  ctx.textBaseline = 'middle'

  for (const tool of info.tools) {
    const tw = ctx.measureText(tool).width + 16
    _drawRoundedRect(ctx, pillX, pillY, tw, 26, 8, 'rgba(255,255,255,0.12)')
    ctx.fillStyle = '#cccccc'
    ctx.textAlign = 'center'
    ctx.fillText(tool, pillX + tw / 2, pillY + 13)
    pillX += tw + 8
  }

  panel.markDirty()
}

function _renderChatText(panel, agentId, text, isStreaming, color) {
  const ctx = panel.ctx
  const w = panel.canvas.width
  const h = panel.canvas.height

  // Clear
  ctx.clearRect(0, 0, w, h)

  // Background
  _drawRoundedRect(ctx, 8, 8, w - 16, h - 16, 12, 'rgba(10, 10, 20, 0.92)', 'rgba(255,255,255,0.1)')

  // Agent name header with colored dot
  ctx.fillStyle = color
  ctx.beginPath()
  ctx.arc(28, 36, 6, 0, Math.PI * 2)
  ctx.fill()

  ctx.fillStyle = color
  ctx.font = 'bold 20px sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'top'
  ctx.fillText(agentId, 42, 24)

  // Divider line
  ctx.fillStyle = 'rgba(255,255,255,0.08)'
  ctx.fillRect(20, 52, w - 40, 1)

  // Word-wrapped body text -- show last lines if overflow
  ctx.fillStyle = '#dddddd'
  ctx.font = '15px sans-serif'
  ctx.textBaseline = 'top'

  const maxWidth = w - 56
  const lineHeight = 20
  const maxLines = Math.floor((h - 100) / lineHeight)

  // Split into wrapped lines first
  const words = text.split(' ')
  const lines = []
  let line = ''
  for (const word of words) {
    const test = line + word + ' '
    if (ctx.measureText(test).width > maxWidth && line !== '') {
      lines.push(line.trim())
      line = word + ' '
    } else {
      line = test
    }
  }
  if (line.trim()) lines.push(line.trim())

  // Show last N lines if overflow
  const start = Math.max(0, lines.length - maxLines)
  const visible = lines.slice(start)
  for (let i = 0; i < visible.length; i++) {
    ctx.fillText(visible[i], 28, 62 + i * lineHeight)
  }

  // Streaming indicator -- 3 pulsing dots
  if (isStreaming) {
    const baseY = 62 + visible.length * lineHeight + 8
    const now = performance.now()
    for (let i = 0; i < 3; i++) {
      const alpha = 0.3 + 0.7 * ((Math.sin(now / 300 + i) + 1) / 2)
      ctx.fillStyle = `rgba(255, 255, 255, ${alpha.toFixed(2)})`
      ctx.beginPath()
      ctx.arc(28 + i * 14, baseY + 6, 4, 0, Math.PI * 2)
      ctx.fill()
    }
  }

  panel.markDirty()
}

function _renderWristHUD(panel, hour, weatherState) {
  const ctx = panel.ctx
  const s = panel.canvas.width // 128

  // Clear
  ctx.clearRect(0, 0, s, s)

  // Semi-transparent dark circle background
  ctx.fillStyle = 'rgba(10, 10, 20, 0.75)'
  ctx.beginPath()
  ctx.arc(s / 2, s / 2, s / 2 - 4, 0, Math.PI * 2)
  ctx.fill()

  // Thin border ring
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)'
  ctx.lineWidth = 1.5
  ctx.stroke()

  // Time display
  const hh = String(Math.floor(hour)).padStart(2, '0')
  const mm = String(Math.floor((hour % 1) * 60)).padStart(2, '0')
  ctx.fillStyle = '#ffffff'
  ctx.font = 'bold 24px sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(`${hh}:${mm}`, s / 2, s / 2 - 10)

  // Weather icon
  const weatherIcons = {
    clear: '\u2600',  // sun
    rain: '\uD83C\uDF27',   // cloud with rain
    fog: '\uD83C\uDF2B',    // fog
    snow: '\u2744',   // snowflake
    storm: '\u26C8',  // thunder cloud
    aurora: '\uD83C\uDF0C', // milky way
  }
  const icon = weatherIcons[weatherState] || weatherIcons.clear
  ctx.font = '22px sans-serif'
  ctx.fillText(icon, s / 2, s / 2 + 18)

  panel.markDirty()
}

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useVRUI() {
  // --- Private state ---
  let _scene = null
  let _camera = null
  let _cameraRig = null
  let _controller0 = null
  let _hand0 = null

  let _agentPanel = null
  let _zonePanel = null
  let _chatPanel = null
  let _wristHUD = null

  let _lastChatText = ''
  let _lastHour = -1
  let _lastWeather = ''
  let _chatAgentId = ''
  let _chatColor = '#ffffff'
  let _chatIsStreaming = false

  // Pre-allocated scratch vectors to avoid GC pressure in update()
  const _tempVec = new THREE.Vector3()
  const _tempQuat = new THREE.Quaternion()
  const _spawnPos = new THREE.Vector3()

  // -------------------------------------------------------------------------
  // INIT / DISPOSE
  // -------------------------------------------------------------------------

  function init(scene, camera, cameraRig, controller0, hand0) {
    _scene = scene
    _camera = camera
    _cameraRig = cameraRig
    _controller0 = controller0
    _hand0 = hand0

    _agentPanel = new VRPanel({
      width: PANEL_WIDTH,
      height: PANEL_HEIGHT,
      canvasW: PANEL_CANVAS_W,
      canvasH: PANEL_CANVAS_H,
      billboard: true,
      timeout: INFO_TIMEOUT,
    })

    _zonePanel = new VRPanel({
      width: PANEL_WIDTH,
      height: PANEL_HEIGHT,
      canvasW: PANEL_CANVAS_W,
      canvasH: PANEL_CANVAS_H,
      billboard: true,
      timeout: INFO_TIMEOUT,
    })

    _chatPanel = new VRPanel({
      width: PANEL_WIDTH,
      height: CHAT_PANEL_HEIGHT,
      canvasW: PANEL_CANVAS_W,
      canvasH: CHAT_CANVAS_H,
      billboard: true,
      timeout: 0, // manual hide
    })

    _wristHUD = new VRPanel({
      width: WRIST_HUD_SIZE,
      height: WRIST_HUD_SIZE,
      canvasW: WRIST_HUD_CANVAS,
      canvasH: WRIST_HUD_CANVAS,
      billboard: false, // attached to wrist, not billboarded
      timeout: 0,
    })
  }

  // -------------------------------------------------------------------------
  // SPAWN POSITION
  // -------------------------------------------------------------------------

  function _getSpawnPosition() {
    _camera.getWorldPosition(_tempVec)

    // Horizontal-only forward direction (ignore pitch)
    const forward = new THREE.Vector3(0, 0, -1)
    _camera.getWorldQuaternion(_tempQuat)
    forward.applyQuaternion(_tempQuat)
    forward.y = 0
    forward.normalize()

    _spawnPos.copy(_tempVec).addScaledVector(forward, PANEL_DISTANCE)
    _spawnPos.y = _tempVec.y + PANEL_Y_OFFSET
    return _spawnPos
  }

  // -------------------------------------------------------------------------
  // PUBLIC API
  // -------------------------------------------------------------------------

  function showAgentInfo(agentId, currentZone) {
    if (!_agentPanel || !_scene) return
    const color = AGENT_COLORS[agentId] || '#ffffff'
    _renderAgentInfo(_agentPanel, agentId, currentZone, color)
    _agentPanel.show(_scene, _getSpawnPosition())
  }

  function showZoneInfo(zoneName, label, color) {
    if (!_zonePanel || !_scene) return
    const zoneColor = color || '#888888'
    _renderZoneInfo(_zonePanel, zoneName, label, zoneColor)
    _zonePanel.show(_scene, _getSpawnPosition())
  }

  function showChat(agentId) {
    if (!_chatPanel || !_scene) return
    _chatAgentId = agentId
    _chatColor = AGENT_COLORS[agentId] || '#ffffff'
    _chatIsStreaming = true
    _lastChatText = ''
    _renderChatText(_chatPanel, _chatAgentId, '', true, _chatColor)
    _chatPanel.show(_scene, _getSpawnPosition())
  }

  function updateChatText(text, isStreaming) {
    if (!_chatPanel || !_chatPanel.isVisible) return
    _chatIsStreaming = isStreaming
    // Only re-render when text actually changes (or streaming state toggles)
    if (text !== _lastChatText || isStreaming !== _chatIsStreaming) {
      _lastChatText = text
      _renderChatText(_chatPanel, _chatAgentId, text, isStreaming, _chatColor)
    }
  }

  function hideChat() {
    if (_chatPanel) {
      _chatPanel.hide()
      _lastChatText = ''
      _chatIsStreaming = false
    }
  }

  function updateWristHUD(hour, weatherState) {
    if (!_wristHUD) return
    // Only re-render when values change
    if (hour === _lastHour && weatherState === _lastWeather) return
    _lastHour = hour
    _lastWeather = weatherState
    _renderWristHUD(_wristHUD, hour, weatherState)

    // Show on scene if not already visible (initial attach)
    if (!_wristHUD.isVisible && _scene) {
      _wristHUD.show(_scene, new THREE.Vector3(0, 0, 0))
    }
  }

  // -------------------------------------------------------------------------
  // FRAME UPDATE
  // -------------------------------------------------------------------------

  function update(dt) {
    if (!_camera) return

    // Billboard visible info panels
    if (_agentPanel) _agentPanel.update(_camera, dt, _tempVec)
    if (_zonePanel) _zonePanel.update(_camera, dt, _tempVec)
    if (_chatPanel) _chatPanel.update(_camera, dt, _tempVec)

    // Re-render chat typing indicator every frame while streaming
    if (_chatPanel && _chatPanel.isVisible && _chatIsStreaming) {
      _renderChatText(_chatPanel, _chatAgentId, _lastChatText, true, _chatColor)
    }

    // Attach wrist HUD to hand0 wrist joint or fallback to controller0
    if (_wristHUD && _wristHUD.isVisible) {
      let attached = false

      // Try hand tracking wrist joint first
      if (_hand0 && _hand0.joints && _hand0.joints['wrist']) {
        const wrist = _hand0.joints['wrist']
        _wristHUD.mesh.position.copy(wrist.position)
        // Offset slightly above the wrist so it does not clip
        _wristHUD.mesh.position.y += 0.05
        _wristHUD.mesh.quaternion.copy(wrist.quaternion)
        attached = true
      }

      // Fallback: attach to left controller
      if (!attached && _controller0) {
        _controller0.getWorldPosition(_tempVec)
        _tempVec.y += 0.06
        _wristHUD.mesh.position.copy(_tempVec)
        // Face the camera for readability
        _camera.getWorldPosition(_tempVec)
        _wristHUD.mesh.lookAt(_tempVec)
        attached = true
      }

      // Deferred texture upload (no billboard -- handled above)
      if (_wristHUD._dirty) {
        _wristHUD.texture.needsUpdate = true
        _wristHUD._dirty = false
      }
    }
  }

  // -------------------------------------------------------------------------
  // DISPOSE
  // -------------------------------------------------------------------------

  function dispose() {
    if (_agentPanel) { _agentPanel.dispose(); _agentPanel = null }
    if (_zonePanel) { _zonePanel.dispose(); _zonePanel = null }
    if (_chatPanel) { _chatPanel.dispose(); _chatPanel = null }
    if (_wristHUD) { _wristHUD.dispose(); _wristHUD = null }
    _scene = null
    _camera = null
    _cameraRig = null
    _controller0 = null
    _hand0 = null
    _lastChatText = ''
    _lastHour = -1
    _lastWeather = ''
  }

  // -------------------------------------------------------------------------
  // RETURN
  // -------------------------------------------------------------------------

  // Return the agent currently streaming chat (for VR presence animations)
  function getSpeakingAgentId() {
    return _chatIsStreaming ? _chatAgentId : null
  }

  return {
    init,
    showAgentInfo,
    showZoneInfo,
    showChat,
    updateChatText,
    hideChat,
    updateWristHUD,
    update,
    dispose,
    getSpeakingAgentId,
  }
}
