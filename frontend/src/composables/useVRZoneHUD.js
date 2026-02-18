/**
 * useVRZoneHUD — Jarvis-Style Zone Interface for VR
 *
 * Floating holographic panels that appear when pressing A near a building
 * in VR. Three panels in an arc: Main (zone info), Stats (gamification),
 * Action (agent select + start chat). Interactive via controller ray /
 * hand pinch on invisible button meshes.
 *
 * Replaces VR interior entry — lighter weight, no scene swap, zero
 * frame budget risk. Desktop interiors remain unchanged.
 *
 * "The building speaks — holographic whispers of data and intent"
 */

import { ref } from 'vue'
import * as THREE from 'three'
import { useVillageGamification } from '@/composables/useVillageGamification'
import { VILLAGE_LAYOUT } from '@/composables/useVillage3D'

// =============================================================================
// CONSTANTS
// =============================================================================

const PANEL_DISTANCE = 1.5 // meters from player
const PANEL_Y_OFFSET = -0.1 // slightly below eye level
const ARC_ANGLE = (25 * Math.PI) / 180 // 25 degrees for side panels
const ANIM_DURATION = 0.2 // seconds for fly-in/out
const AUTO_DISMISS_DIST = 6 // meters — close HUD when player walks away
const UP = new THREE.Vector3(0, 1, 0)

// Main panel
const MAIN_W = 0.7
const MAIN_H = 0.5
const MAIN_CW = 600
const MAIN_CH = 430

// Stats panel
const STATS_W = 0.55
const STATS_H = 0.45
const STATS_CW = 480
const STATS_CH = 390

// Action panel
const ACTION_W = 0.55
const ACTION_H = 0.55
const ACTION_CW = 480
const ACTION_CH = 480

// =============================================================================
// STATIC DATA
// =============================================================================

const ZONE_INFO = {
  village_square: { desc: 'Central hub — all tools available', tools: ['All'], icon: '\u{1F3DB}' },
  workshop: { desc: 'Crafting & file manipulation', tools: ['Utility', 'Files'], icon: '\u2692' },
  library: { desc: 'Research and web exploration', tools: ['Web', 'Browser'], icon: '\u{1F4DA}' },
  dj_booth: { desc: 'Music generation & creative tools', tools: ['Music', 'Creative'], icon: '\u{1F3B5}' },
  memory_garden: { desc: 'Long-term memory operations', tools: ['Memory'], icon: '\u{1F33F}' },
  file_shed: { desc: 'File storage and management', tools: ['Files', 'Utility'], icon: '\u{1F4C1}' },
  bridge_portal: { desc: 'Cross-village portal connections', tools: ['Web', 'Agent'], icon: '\u{1F309}' },
  watchtower: { desc: 'Monitoring and web utilities', tools: ['Utility', 'Web'], icon: '\u{1F52D}' },
  arena: { desc: 'Competitive challenges', tools: ['Arena'], icon: '\u2694' },
  bazaar: { desc: 'Trading and marketplace', tools: ['Commerce'], icon: '\u{1F3EA}' },
  apothecary: { desc: 'Alchemical experimentation', tools: ['Alchemy'], icon: '\u2697' },
  nexus_tower: { desc: 'Advanced computational nexus', tools: ['Compute'], icon: '\u{1F4E1}' },
  mines: { desc: 'Deep data mining operations', tools: ['Mining'], icon: '\u26CF' },
  sanctum: { desc: 'Inner sanctum — advanced rituals', tools: ['Sacred'], icon: '\u{1F52E}' },
}

const ZONE_DEFAULT_AGENTS = {
  workshop: 'AZOTH',
  library: 'KETHER',
  dj_booth: 'ELYSIAN',
  memory_garden: 'KETHER',
  file_shed: 'VAJRA',
  bridge_portal: 'AZOTH',
  watchtower: 'VAJRA',
  village_square: 'AZOTH',
}

const AGENT_COLORS = {
  AZOTH: '#FFD700',
  KETHER: '#9370db',
  VAJRA: '#4FC3F7',
  ELYSIAN: '#ff69b4',
}

const AGENT_IDS = ['AZOTH', 'VAJRA', 'ELYSIAN', 'KETHER']

// =============================================================================
// CANVAS HELPERS
// =============================================================================

function _hexToRgb(hex) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return { r, g, b }
}

function _drawGlassPanel(ctx, w, h, zoneColor) {
  // Dark glass background
  ctx.clearRect(0, 0, w, h)
  ctx.fillStyle = 'rgba(8, 10, 22, 0.92)'
  ctx.beginPath()
  ctx.roundRect(6, 6, w - 12, h - 12, 10)
  ctx.fill()

  // Glowing border
  ctx.shadowColor = zoneColor
  ctx.shadowBlur = 12
  ctx.strokeStyle = zoneColor
  ctx.lineWidth = 1.5
  ctx.stroke()
  ctx.shadowBlur = 0

  // Corner alchemical glyphs
  ctx.fillStyle = 'rgba(255,255,255,0.12)'
  ctx.font = '12px serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'top'
  ctx.fillText('Au', 16, 14)
  ctx.textAlign = 'right'
  ctx.textBaseline = 'bottom'
  ctx.fillText('\u25B3', w - 16, h - 10)
}

function _drawAccentLine(ctx, y, w, color) {
  const { r, g, b } = _hexToRgb(color)
  ctx.strokeStyle = `rgba(${r},${g},${b},0.25)`
  ctx.lineWidth = 0.5
  ctx.beginPath()
  ctx.moveTo(20, y)
  ctx.lineTo(w - 20, y)
  ctx.stroke()
}

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
  return lines + 1
}

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useVRZoneHUD() {
  // --- Reactive state ---
  const isOpen = ref(false)

  // --- Private state ---
  let _scene = null
  let _camera = null
  let _cameraRig = null

  // Panels
  let _mainPanel = null
  let _statsPanel = null
  let _actionPanel = null
  const _buttonMeshes = []

  // State
  let _activeZone = null
  let _selectedAgent = null
  let _animProgress = 0
  let _animDirection = 0 // 1 = opening, -1 = closing, 0 = idle
  let _openPos = new THREE.Vector3() // where HUD was opened (for auto-dismiss)
  let _onStartChat = null
  let _agentsAtZone = [] // agent IDs currently at the active zone

  // Scratch vectors
  const _tempPos = new THREE.Vector3()
  const _tempFwd = new THREE.Vector3()

  // Gamification
  let _gamification = null

  // =========================================================================
  // PANEL CREATION (canvas + mesh, like VRPanel in useVRUI)
  // =========================================================================

  function _createPanel(width, height, canvasW, canvasH) {
    const canvas = document.createElement('canvas')
    canvas.width = canvasW
    canvas.height = canvasH
    const ctx = canvas.getContext('2d')

    const texture = new THREE.CanvasTexture(canvas)
    texture.minFilter = THREE.LinearFilter
    texture.generateMipmaps = false

    const material = new THREE.MeshBasicMaterial({
      map: texture,
      transparent: true,
      side: THREE.DoubleSide,
      depthTest: true,
    })

    const geometry = new THREE.PlaneGeometry(width, height)
    const mesh = new THREE.Mesh(geometry, material)
    mesh.renderOrder = 100
    mesh.visible = false

    return { canvas, ctx, texture, material, geometry, mesh, width, height }
  }

  // =========================================================================
  // INIT / DISPOSE
  // =========================================================================

  function init(scene, camera, cameraRig) {
    _scene = scene
    _camera = camera
    _cameraRig = cameraRig
    _gamification = useVillageGamification()

    _mainPanel = _createPanel(MAIN_W, MAIN_H, MAIN_CW, MAIN_CH)
    _statsPanel = _createPanel(STATS_W, STATS_H, STATS_CW, STATS_CH)
    _actionPanel = _createPanel(ACTION_W, ACTION_H, ACTION_CW, ACTION_CH)
  }

  function dispose() {
    close()
    for (const panel of [_mainPanel, _statsPanel, _actionPanel]) {
      if (!panel) continue
      panel.texture.dispose()
      panel.material.dispose()
      panel.geometry.dispose()
    }
    _clearButtonMeshes()
    _mainPanel = null
    _statsPanel = null
    _actionPanel = null
    _scene = null
    _camera = null
    _cameraRig = null
    _gamification = null
    _onStartChat = null
    isOpen.value = false
  }

  // =========================================================================
  // OPEN / CLOSE / TOGGLE
  // =========================================================================

  function open(zoneName) {
    if (!_scene || !_mainPanel) return

    _activeZone = zoneName
    _selectedAgent = ZONE_DEFAULT_AGENTS[zoneName] || 'AZOTH'

    // Render all panels
    _renderMainPanel(zoneName)
    _renderStatsPanel(zoneName)
    _renderActionPanel(zoneName, _selectedAgent)

    // Position panels in arc
    _positionPanels()

    // Store open position for auto-dismiss
    _camera.getWorldPosition(_openPos)
    _openPos.y = 0

    // Add to scene
    _scene.add(_mainPanel.mesh)
    _scene.add(_statsPanel.mesh)
    _scene.add(_actionPanel.mesh)
    _mainPanel.mesh.visible = true
    _statsPanel.mesh.visible = true
    _actionPanel.mesh.visible = true

    // Build interactive button meshes
    _buildButtonMeshes()

    // Start fly-in animation
    _animProgress = 0
    _animDirection = 1
    isOpen.value = true
  }

  function close() {
    if (!isOpen.value) return
    _animDirection = -1
    _animProgress = 1
  }

  function _finishClose() {
    if (_mainPanel?.mesh.parent) _scene.remove(_mainPanel.mesh)
    if (_statsPanel?.mesh.parent) _scene.remove(_statsPanel.mesh)
    if (_actionPanel?.mesh.parent) _scene.remove(_actionPanel.mesh)
    _mainPanel.mesh.visible = false
    _statsPanel.mesh.visible = false
    _actionPanel.mesh.visible = false
    _clearButtonMeshes()
    _activeZone = null
    isOpen.value = false
    _animDirection = 0
  }

  function toggle(zoneName) {
    if (isOpen.value && _activeZone === zoneName) {
      close()
    } else {
      if (isOpen.value) _finishClose() // instant close old before opening new
      open(zoneName)
    }
  }

  // =========================================================================
  // PANEL POSITIONING
  // =========================================================================

  function _positionPanels() {
    _camera.getWorldPosition(_tempPos)
    _camera.getWorldDirection(_tempFwd)
    _tempFwd.y = 0
    _tempFwd.normalize()

    const eyeY = _tempPos.y + PANEL_Y_OFFSET

    // Main panel: directly ahead
    _mainPanel.mesh.position.copy(_tempPos).addScaledVector(_tempFwd, PANEL_DISTANCE)
    _mainPanel.mesh.position.y = eyeY

    // Stats panel: 25 degrees left
    const leftDir = _tempFwd.clone().applyAxisAngle(UP, ARC_ANGLE)
    _statsPanel.mesh.position.copy(_tempPos).addScaledVector(leftDir, PANEL_DISTANCE)
    _statsPanel.mesh.position.y = eyeY

    // Action panel: 25 degrees right
    const rightDir = _tempFwd.clone().applyAxisAngle(UP, -ARC_ANGLE)
    _actionPanel.mesh.position.copy(_tempPos).addScaledVector(rightDir, PANEL_DISTANCE)
    _actionPanel.mesh.position.y = eyeY
  }

  // =========================================================================
  // INTERACTIVE BUTTONS (invisible meshes for raycasting)
  // =========================================================================

  function _clearButtonMeshes() {
    for (const btn of _buttonMeshes) {
      if (btn.parent) btn.parent.remove(btn)
      btn.geometry.dispose()
      btn.material.dispose()
    }
    _buttonMeshes.length = 0
  }

  function _buildButtonMeshes() {
    _clearButtonMeshes()
    if (!_actionPanel) return

    // Button layout on action panel canvas (ACTION_CW x ACTION_CH):
    // Agent buttons: 4 in a 2x2 grid starting at y=140, each 200x50 canvas px
    // Start Chat: full width at y=320, 430x60 canvas px
    // Dismiss: full width at y=400, 430x50 canvas px

    const panelW = ACTION_W
    const panelH = ACTION_H
    const cw = ACTION_CW
    const ch = ACTION_CH

    const buttons = [
      // Agent buttons (2x2 grid)
      { id: 'agent_azoth', cx: 120, cy: 165, bw: 200, bh: 50 },
      { id: 'agent_vajra', cx: 340, cy: 165, bw: 200, bh: 50 },
      { id: 'agent_elysian', cx: 120, cy: 235, bw: 200, bh: 50 },
      { id: 'agent_kether', cx: 340, cy: 235, bw: 200, bh: 50 },
      // Start Chat
      { id: 'start_chat', cx: cw / 2, cy: 340, bw: 400, bh: 60 },
      // Dismiss
      { id: 'dismiss', cx: cw / 2, cy: 420, bw: 400, bh: 50 },
    ]

    for (const btn of buttons) {
      // Convert canvas px to panel meters
      const mX = ((btn.cx / cw) - 0.5) * panelW
      const mY = (0.5 - (btn.cy / ch)) * panelH
      const mW = (btn.bw / cw) * panelW
      const mH = (btn.bh / ch) * panelH

      const mesh = new THREE.Mesh(
        new THREE.PlaneGeometry(mW, mH),
        new THREE.MeshBasicMaterial({ visible: false }),
      )
      mesh.userData = { type: 'hud-button', id: btn.id }
      mesh.position.set(mX, mY, 0.002) // slightly in front of panel
      _actionPanel.mesh.add(mesh)
      _buttonMeshes.push(mesh)
    }
  }

  function getInteractables() {
    return _buttonMeshes
  }

  // =========================================================================
  // BUTTON CLICK HANDLER
  // =========================================================================

  function handleButtonClick(buttonId) {
    if (!isOpen.value || !_activeZone) return

    if (buttonId.startsWith('agent_')) {
      _selectedAgent = buttonId.replace('agent_', '').toUpperCase()
      _renderActionPanel(_activeZone, _selectedAgent)
      _actionPanel.texture.needsUpdate = true
    } else if (buttonId === 'start_chat') {
      if (_onStartChat) _onStartChat(_selectedAgent, _activeZone)
    } else if (buttonId === 'dismiss') {
      close()
    }
  }

  // =========================================================================
  // FRAME UPDATE
  // =========================================================================

  function update(dt) {
    if (!isOpen.value && _animDirection === 0) return

    // --- Animation ---
    if (_animDirection !== 0) {
      _animProgress += _animDirection * (dt / ANIM_DURATION)
      _animProgress = Math.max(0, Math.min(1, _animProgress))

      // Ease out cubic
      const t = _animDirection > 0
        ? 1 - Math.pow(1 - _animProgress, 3)
        : Math.pow(_animProgress, 3)

      const scale = t
      const yOffset = (1 - t) * -0.1 // rise from below

      for (const panel of [_mainPanel, _statsPanel, _actionPanel]) {
        if (!panel) continue
        panel.mesh.scale.setScalar(scale)
        // Apply Y offset relative to base position
        // (mesh.position.y was set in _positionPanels; animation offsets temporarily)
      }

      if (_animDirection > 0 && _animProgress >= 1) {
        _animDirection = 0 // done opening
      } else if (_animDirection < 0 && _animProgress <= 0) {
        _finishClose()
        return
      }
    }

    // --- Billboard ---
    if (_camera) {
      _camera.getWorldPosition(_tempPos)
      for (const panel of [_mainPanel, _statsPanel, _actionPanel]) {
        if (panel?.mesh.visible) panel.mesh.lookAt(_tempPos)
      }
    }

    // --- Auto-dismiss (player walked away) ---
    if (isOpen.value && _cameraRig) {
      _tempPos.set(_cameraRig.position.x, 0, _cameraRig.position.z)
      if (_tempPos.distanceTo(_openPos) > AUTO_DISMISS_DIST) {
        close()
      }
    }
  }

  // =========================================================================
  // SET AGENTS AT ZONE (called from outside with current zone occupants)
  // =========================================================================

  function setAgentsAtZone(agentIds) {
    _agentsAtZone = agentIds || []
  }

  function setOnStartChat(fn) {
    _onStartChat = fn
  }

  // =========================================================================
  // CANVAS RENDERERS
  // =========================================================================

  function _renderMainPanel(zoneName) {
    const panel = _mainPanel
    if (!panel) return
    const { ctx, canvas } = panel
    const w = canvas.width
    const h = canvas.height
    const layout = VILLAGE_LAYOUT[zoneName]
    const info = ZONE_INFO[zoneName] || ZONE_INFO.village_square
    const zoneColor = layout?.color || '#888888'

    _drawGlassPanel(ctx, w, h, zoneColor)

    // Zone icon + name + level
    const level = _gamification?.getZoneStats(zoneName)?.level || 0
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'

    // Icon
    ctx.font = '32px sans-serif'
    ctx.fillStyle = '#ffffff'
    ctx.fillText(info.icon || '\u{1F3DB}', 24, 36)

    // Zone name
    ctx.font = 'bold 28px sans-serif'
    ctx.fillStyle = '#ffffff'
    const label = layout?.label || zoneName.replace(/_/g, ' ')
    ctx.fillText(label, 68, 38)

    // Level badge
    ctx.font = 'bold 14px sans-serif'
    ctx.fillStyle = zoneColor
    const lvText = `Lv.${level}`
    const lvW = ctx.measureText(lvText).width + 14
    const lvX = w - lvW - 20
    ctx.fillStyle = 'rgba(255,255,255,0.08)'
    ctx.beginPath()
    ctx.roundRect(lvX, 38, lvW, 24, 6)
    ctx.fill()
    ctx.fillStyle = zoneColor
    ctx.textAlign = 'center'
    ctx.fillText(lvText, lvX + lvW / 2, 44)

    // Accent line
    _drawAccentLine(ctx, 76, w, zoneColor)

    // Description
    ctx.textAlign = 'left'
    ctx.fillStyle = '#aaaaaa'
    ctx.font = '16px sans-serif'
    const descLines = _wrapText(ctx, info.desc, 24, 92, w - 48, 22)

    // Tool pills
    const pillY = 92 + descLines * 22 + 16
    let pillX = 24
    ctx.font = 'bold 12px sans-serif'
    ctx.textBaseline = 'middle'
    for (const tool of info.tools) {
      const tw = ctx.measureText(tool).width + 16
      ctx.fillStyle = 'rgba(255,255,255,0.1)'
      ctx.beginPath()
      ctx.roundRect(pillX, pillY, tw, 24, 6)
      ctx.fill()
      ctx.fillStyle = '#cccccc'
      ctx.textAlign = 'center'
      ctx.fillText(tool, pillX + tw / 2, pillY + 12)
      pillX += tw + 8
    }

    // Accent line before agents
    const agentY = pillY + 42
    _drawAccentLine(ctx, agentY - 8, w, zoneColor)

    // Agents at zone
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'
    ctx.font = '13px sans-serif'
    ctx.fillStyle = 'rgba(255,255,255,0.5)'
    ctx.fillText('Agents present:', 24, agentY)

    let dotX = 24
    const dotY = agentY + 22
    if (_agentsAtZone.length === 0) {
      ctx.fillStyle = 'rgba(255,255,255,0.3)'
      ctx.font = 'italic 13px sans-serif'
      ctx.fillText('None nearby', 24, dotY)
    } else {
      for (const agentId of _agentsAtZone) {
        const col = AGENT_COLORS[agentId] || '#888'
        // Colored dot
        ctx.fillStyle = col
        ctx.beginPath()
        ctx.arc(dotX + 6, dotY + 7, 6, 0, Math.PI * 2)
        ctx.fill()
        // Name
        ctx.fillStyle = '#dddddd'
        ctx.font = '13px sans-serif'
        ctx.fillText(agentId, dotX + 18, dotY)
        dotX += ctx.measureText(agentId).width + 32
      }
    }

    panel.texture.needsUpdate = true
  }

  function _renderStatsPanel(zoneName) {
    const panel = _statsPanel
    if (!panel) return
    const { ctx, canvas } = panel
    const w = canvas.width
    const h = canvas.height
    const layout = VILLAGE_LAYOUT[zoneName]
    const zoneColor = layout?.color || '#888888'
    const stats = _gamification?.getZoneStats(zoneName) || { tasks: 0, successes: 0, level: 0 }
    const history = _gamification?.getZoneHistory(zoneName) || []

    _drawGlassPanel(ctx, w, h, zoneColor)

    // Header
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'
    ctx.font = 'bold 20px sans-serif'
    ctx.fillStyle = '#ffffff'
    ctx.fillText('Zone Stats', 24, 28)

    _drawAccentLine(ctx, 58, w, zoneColor)

    // Arc gauge — tasks and success rate
    const centerX = w / 2
    const gaugeY = 130
    const radius = 50
    const total = stats.tasks || 0
    const successes = stats.successes || 0
    const rate = total > 0 ? successes / total : 0

    // Background arc
    ctx.strokeStyle = 'rgba(255,255,255,0.08)'
    ctx.lineWidth = 8
    ctx.lineCap = 'round'
    ctx.beginPath()
    ctx.arc(centerX, gaugeY, radius, Math.PI * 0.8, Math.PI * 2.2)
    ctx.stroke()

    // Progress arc (zone color)
    if (rate > 0) {
      const sweep = rate * Math.PI * 1.4 // 1.4 radians total arc
      ctx.strokeStyle = zoneColor
      ctx.lineWidth = 8
      ctx.beginPath()
      ctx.arc(centerX, gaugeY, radius, Math.PI * 0.8, Math.PI * 0.8 + sweep)
      ctx.stroke()
    }

    // Rate text in center
    ctx.fillStyle = '#ffffff'
    ctx.font = 'bold 22px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(`${Math.round(rate * 100)}%`, centerX, gaugeY - 4)
    ctx.font = '12px sans-serif'
    ctx.fillStyle = '#888888'
    ctx.fillText('success', centerX, gaugeY + 16)

    // Task count
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'
    ctx.font = '14px sans-serif'
    ctx.fillStyle = '#aaaaaa'
    ctx.fillText(`${total} tasks completed`, 24, gaugeY + radius + 20)

    // Level progress bar
    const levelY = gaugeY + radius + 46
    const tasksForNext = (stats.level + 1) * 5
    const levelProgress = Math.min(1, total / tasksForNext)

    ctx.fillStyle = 'rgba(255,255,255,0.06)'
    ctx.beginPath()
    ctx.roundRect(24, levelY, w - 48, 10, 5)
    ctx.fill()

    if (levelProgress > 0) {
      ctx.fillStyle = zoneColor
      ctx.beginPath()
      ctx.roundRect(24, levelY, (w - 48) * levelProgress, 10, 5)
      ctx.fill()
    }

    ctx.fillStyle = '#777777'
    ctx.font = '11px sans-serif'
    ctx.fillText(`Level ${stats.level} → ${stats.level + 1}  (${total}/${tasksForNext} tasks)`, 24, levelY + 16)

    // Recent tasks
    _drawAccentLine(ctx, levelY + 40, w, zoneColor)

    ctx.fillStyle = '#999999'
    ctx.font = '13px sans-serif'
    ctx.fillText('Recent:', 24, levelY + 50)

    const recentTasks = history.slice(-3).reverse()
    let ty = levelY + 70
    if (recentTasks.length === 0) {
      ctx.fillStyle = 'rgba(255,255,255,0.3)'
      ctx.font = 'italic 12px sans-serif'
      ctx.fillText('No tasks yet', 24, ty)
    } else {
      for (const task of recentTasks) {
        // Success dot
        ctx.fillStyle = task.success ? '#00ff88' : '#ff4444'
        ctx.beginPath()
        ctx.arc(30, ty + 7, 4, 0, Math.PI * 2)
        ctx.fill()

        // Prompt snippet
        ctx.fillStyle = '#cccccc'
        ctx.font = '12px sans-serif'
        const snippet = (task.prompt || '').slice(0, 40) + ((task.prompt || '').length > 40 ? '...' : '')
        ctx.fillText(snippet, 42, ty)

        // Time ago
        const ago = _timeAgo(task.timestamp)
        ctx.fillStyle = '#666666'
        ctx.font = '10px sans-serif'
        ctx.textAlign = 'right'
        ctx.fillText(ago, w - 24, ty)
        ctx.textAlign = 'left'

        ty += 22
      }
    }

    panel.texture.needsUpdate = true
  }

  function _renderActionPanel(zoneName, selectedAgent) {
    const panel = _actionPanel
    if (!panel) return
    const { ctx, canvas } = panel
    const w = canvas.width
    const h = canvas.height
    const layout = VILLAGE_LAYOUT[zoneName]
    const zoneColor = layout?.color || '#888888'

    _drawGlassPanel(ctx, w, h, zoneColor)

    // Header
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'
    ctx.font = 'bold 20px sans-serif'
    ctx.fillStyle = '#ffffff'
    ctx.fillText('Actions', 24, 28)

    _drawAccentLine(ctx, 58, w, zoneColor)

    // Agent label
    ctx.font = '14px sans-serif'
    ctx.fillStyle = '#999999'
    ctx.fillText('Select Agent:', 24, 72)

    // --- Agent selection buttons (2x2 grid) ---
    const agentGrid = [
      { id: 'AZOTH', col: 0, row: 0 },
      { id: 'VAJRA', col: 1, row: 0 },
      { id: 'ELYSIAN', col: 0, row: 1 },
      { id: 'KETHER', col: 1, row: 1 },
    ]

    const btnW = 195
    const btnH = 44
    const gridX = 22
    const gridY = 96
    const gapX = 10
    const gapY = 10

    for (const agent of agentGrid) {
      const bx = gridX + agent.col * (btnW + gapX)
      const by = gridY + agent.row * (btnH + gapY)
      const isSelected = agent.id === selectedAgent
      const agentColor = AGENT_COLORS[agent.id] || '#888'

      // Button background
      if (isSelected) {
        // Selected: filled with agent color at low opacity + brighter border
        const { r, g, b } = _hexToRgb(agentColor)
        ctx.fillStyle = `rgba(${r},${g},${b},0.2)`
        ctx.beginPath()
        ctx.roundRect(bx, by, btnW, btnH, 8)
        ctx.fill()
        ctx.strokeStyle = agentColor
        ctx.lineWidth = 2
        ctx.stroke()
      } else {
        // Unselected: subtle outline
        ctx.fillStyle = 'rgba(255,255,255,0.04)'
        ctx.beginPath()
        ctx.roundRect(bx, by, btnW, btnH, 8)
        ctx.fill()
        ctx.strokeStyle = 'rgba(255,255,255,0.1)'
        ctx.lineWidth = 1
        ctx.stroke()
      }

      // Agent color dot
      ctx.fillStyle = agentColor
      ctx.beginPath()
      ctx.arc(bx + 20, by + btnH / 2, 7, 0, Math.PI * 2)
      ctx.fill()

      // Agent name
      ctx.fillStyle = isSelected ? '#ffffff' : '#aaaaaa'
      ctx.font = isSelected ? 'bold 14px sans-serif' : '14px sans-serif'
      ctx.textAlign = 'left'
      ctx.textBaseline = 'middle'
      ctx.fillText(agent.id, bx + 36, by + btnH / 2)
    }

    // --- "Start Chat" button ---
    const chatY = gridY + 2 * (btnH + gapY) + 20
    const chatW = w - 48
    const chatH = 54

    // Green-ish glow button
    ctx.fillStyle = 'rgba(0, 255, 136, 0.12)'
    ctx.beginPath()
    ctx.roundRect(24, chatY, chatW, chatH, 10)
    ctx.fill()
    ctx.shadowColor = '#00ff88'
    ctx.shadowBlur = 8
    ctx.strokeStyle = '#00ff88'
    ctx.lineWidth = 1.5
    ctx.stroke()
    ctx.shadowBlur = 0

    ctx.fillStyle = '#00ff88'
    ctx.font = 'bold 18px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('\u{1F5E8}  Start Chat', w / 2, chatY + chatH / 2)

    // --- "Dismiss" button ---
    const dismissY = chatY + chatH + 16
    const dismissH = 44

    ctx.fillStyle = 'rgba(255,255,255,0.05)'
    ctx.beginPath()
    ctx.roundRect(24, dismissY, chatW, dismissH, 8)
    ctx.fill()
    ctx.strokeStyle = 'rgba(255,255,255,0.15)'
    ctx.lineWidth = 1
    ctx.stroke()

    ctx.fillStyle = '#888888'
    ctx.font = '15px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('Dismiss  [A]', w / 2, dismissY + dismissH / 2)

    panel.texture.needsUpdate = true
  }

  // =========================================================================
  // HELPERS
  // =========================================================================

  function _timeAgo(timestamp) {
    if (!timestamp) return ''
    const diff = Date.now() - new Date(timestamp).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'just now'
    if (mins < 60) return `${mins}m ago`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  }

  // =========================================================================
  // RETURN
  // =========================================================================

  return {
    isOpen,
    init,
    dispose,
    open,
    close,
    toggle,
    update,
    handleButtonClick,
    getInteractables,
    setOnStartChat,
    setAgentsAtZone,
  }
}
