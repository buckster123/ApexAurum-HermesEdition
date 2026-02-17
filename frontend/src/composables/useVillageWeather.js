// =============================================================================
// useVillageWeather.js — Phase 16: Weather & Atmosphere
//
// Manages weather effects layered on top of the day/night cycle. Returns
// modifier values that the main _animate() loop applies to fog, ambient,
// exposure, etc. Includes rain, snow, aurora particle systems and lightning.
//
// Weather rolls every 3-5 minutes using probability tables keyed to the
// current day/night phase. Transitions smooth-lerp over 15 seconds.
//
// "The sky remembers what the ground forgets."
// =============================================================================

import { ref } from 'vue'
import * as THREE from 'three'

// =============================================================================
// WEATHER PRESETS
// =============================================================================

const WEATHER_PRESETS = {
  clear: {
    fogDensityMultiplier: 1.0,
    ambientIntensityMod: 0,
    sunIntensityMultiplier: 1.0,
    exposureMod: 0,
    particleType: null,
    skyTintColor: null,
    lightningChance: 0,
    auroraEnabled: false,
  },
  rain: {
    fogDensityMultiplier: 1.8,
    ambientIntensityMod: -0.1,
    sunIntensityMultiplier: 0.6,
    exposureMod: -0.15,
    particleType: 'rain',
    skyTintColor: new THREE.Color(0x334455),
    lightningChance: 0,
    auroraEnabled: false,
  },
  fog: {
    fogDensityMultiplier: 3.5,
    ambientIntensityMod: -0.05,
    sunIntensityMultiplier: 0.7,
    exposureMod: -0.1,
    particleType: null,
    skyTintColor: new THREE.Color(0x444455),
    lightningChance: 0,
    auroraEnabled: false,
  },
  snow: {
    fogDensityMultiplier: 1.4,
    ambientIntensityMod: 0.05,
    sunIntensityMultiplier: 0.8,
    exposureMod: 0.05,
    particleType: 'snow',
    skyTintColor: new THREE.Color(0x556677),
    lightningChance: 0,
    auroraEnabled: false,
  },
  storm: {
    fogDensityMultiplier: 2.5,
    ambientIntensityMod: -0.15,
    sunIntensityMultiplier: 0.4,
    exposureMod: -0.2,
    particleType: 'rain',
    skyTintColor: new THREE.Color(0x223344),
    lightningChance: 0.08,
    auroraEnabled: false,
  },
  aurora: {
    fogDensityMultiplier: 0.8,
    ambientIntensityMod: 0.05,
    sunIntensityMultiplier: 1.0,
    exposureMod: 0.05,
    particleType: null,
    skyTintColor: new THREE.Color(0x112233),
    lightningChance: 0,
    auroraEnabled: true,
  },
}

// =============================================================================
// PROBABILITY SCHEDULE (keyed to day/night phase name)
// =============================================================================

const WEATHER_SCHEDULE = {
  Night: { clear: 0.35, fog: 0.20, aurora: 0.25, rain: 0.10, snow: 0.05, storm: 0.05 },
  Dawn:  { clear: 0.30, fog: 0.30, rain: 0.25, snow: 0.05, storm: 0.05, aurora: 0.05 },
  Day:   { clear: 0.50, rain: 0.15, fog: 0.10, snow: 0.10, storm: 0.10, aurora: 0.05 },
  Dusk:  { clear: 0.30, fog: 0.25, rain: 0.15, storm: 0.10, snow: 0.10, aurora: 0.10 },
}

// Modifier key list for lerping
const MODIFIER_KEYS = ['fogDensityMultiplier', 'ambientIntensityMod', 'sunIntensityMultiplier', 'exposureMod']

// Default clear modifiers (numeric only, for lerp source)
const CLEAR_MODIFIERS = {
  fogDensityMultiplier: 1.0,
  ambientIntensityMod: 0,
  sunIntensityMultiplier: 1.0,
  exposureMod: 0,
}

// =============================================================================
// RAIN PARTICLE SYSTEM
// =============================================================================

class RainSystem {
  constructor(scene, isVR = false) {
    this._scene = scene
    this._count = isVR ? 400 : 800
    this._radius = 30
    this._minSpeed = 15
    this._maxSpeed = 25

    // Per-particle data
    this._speeds = new Float32Array(this._count)
    this._phases = new Float32Array(this._count)

    const positions = new Float32Array(this._count * 3)
    for (let i = 0; i < this._count; i++) {
      this._resetParticle(positions, i, true)
      this._speeds[i] = this._minSpeed + Math.random() * (this._maxSpeed - this._minSpeed)
      this._phases[i] = Math.random() * 20
    }

    this._geometry = new THREE.BufferGeometry()
    this._geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    this._material = new THREE.PointsMaterial({
      color: 0xffffff,
      size: 0.15,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
      fog: false,
      depthWrite: false,
    })

    this.mesh = new THREE.Points(this._geometry, this._material)
    this.mesh.visible = false
    this.mesh.frustumCulled = false
    scene.add(this.mesh)
  }

  _resetParticle(positions, i, randomY) {
    const angle = Math.random() * Math.PI * 2
    const r = Math.random() * this._radius
    positions[i * 3] = Math.cos(angle) * r
    positions[i * 3 + 1] = randomY ? Math.random() * 40 + 5 : 40 + Math.random() * 5
    positions[i * 3 + 2] = Math.sin(angle) * r
  }

  setParticleCount(count) {
    if (count === this._count) return
    // Rebuild geometry with new count
    this._scene.remove(this.mesh)
    this._geometry.dispose()

    this._count = count
    this._speeds = new Float32Array(count)
    this._phases = new Float32Array(count)
    const positions = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      this._resetParticle(positions, i, true)
      this._speeds[i] = this._minSpeed + Math.random() * (this._maxSpeed - this._minSpeed)
      this._phases[i] = Math.random() * 20
    }
    this._geometry = new THREE.BufferGeometry()
    this._geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    this.mesh.geometry = this._geometry
    this._scene.add(this.mesh)
  }

  update(dt, cameraPos) {
    if (!this.mesh.visible) return
    const posAttr = this._geometry.attributes.position
    const arr = posAttr.array

    for (let i = 0; i < this._count; i++) {
      const idx = i * 3
      arr[idx + 1] -= this._speeds[i] * dt

      // Recycle below ground
      if (arr[idx + 1] < -2) {
        const angle = Math.random() * Math.PI * 2
        const r = Math.random() * this._radius
        arr[idx] = cameraPos.x + Math.cos(angle) * r
        arr[idx + 1] = cameraPos.y + 30 + Math.random() * 10
        arr[idx + 2] = cameraPos.z + Math.sin(angle) * r
      }
    }
    posAttr.needsUpdate = true
  }

  show() { this.mesh.visible = true }
  hide() { this.mesh.visible = false }

  dispose() {
    this.mesh.visible = false
    this._scene.remove(this.mesh)
    this._geometry.dispose()
    this._material.dispose()
  }
}

// =============================================================================
// SNOW PARTICLE SYSTEM
// =============================================================================

class SnowSystem {
  constructor(scene, isVR = false) {
    this._scene = scene
    this._count = isVR ? 200 : 400
    this._radius = 35
    this._minSpeed = 2
    this._maxSpeed = 5
    this._elapsed = 0

    // Per-particle data
    this._fallSpeeds = new Float32Array(this._count)
    this._driftPhases = new Float32Array(this._count)
    this._driftAmplitudes = new Float32Array(this._count)

    const positions = new Float32Array(this._count * 3)
    for (let i = 0; i < this._count; i++) {
      this._resetParticle(positions, i, true)
      this._fallSpeeds[i] = this._minSpeed + Math.random() * (this._maxSpeed - this._minSpeed)
      this._driftPhases[i] = Math.random() * Math.PI * 2
      this._driftAmplitudes[i] = 0.3 + Math.random() * 0.7
    }

    this._geometry = new THREE.BufferGeometry()
    this._geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))

    this._material = new THREE.PointsMaterial({
      color: 0xffffff,
      size: 0.25,
      transparent: true,
      opacity: 0.7,
      blending: THREE.AdditiveBlending,
      fog: false,
      depthWrite: false,
    })

    this.mesh = new THREE.Points(this._geometry, this._material)
    this.mesh.visible = false
    this.mesh.frustumCulled = false
    scene.add(this.mesh)
  }

  _resetParticle(positions, i, randomY) {
    const angle = Math.random() * Math.PI * 2
    const r = Math.random() * this._radius
    positions[i * 3] = Math.cos(angle) * r
    positions[i * 3 + 1] = randomY ? Math.random() * 35 + 5 : 35 + Math.random() * 5
    positions[i * 3 + 2] = Math.sin(angle) * r
  }

  setParticleCount(count) {
    if (count === this._count) return
    this._scene.remove(this.mesh)
    this._geometry.dispose()

    this._count = count
    this._fallSpeeds = new Float32Array(count)
    this._driftPhases = new Float32Array(count)
    this._driftAmplitudes = new Float32Array(count)
    const positions = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      this._resetParticle(positions, i, true)
      this._fallSpeeds[i] = this._minSpeed + Math.random() * (this._maxSpeed - this._minSpeed)
      this._driftPhases[i] = Math.random() * Math.PI * 2
      this._driftAmplitudes[i] = 0.3 + Math.random() * 0.7
    }
    this._geometry = new THREE.BufferGeometry()
    this._geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    this.mesh.geometry = this._geometry
    this._scene.add(this.mesh)
  }

  update(dt, cameraPos) {
    if (!this.mesh.visible) return
    this._elapsed += dt

    const posAttr = this._geometry.attributes.position
    const arr = posAttr.array

    for (let i = 0; i < this._count; i++) {
      const idx = i * 3

      // Fall
      arr[idx + 1] -= this._fallSpeeds[i] * dt

      // Lateral sine-wave drift
      const drift = Math.sin(this._elapsed + this._driftPhases[i]) * this._driftAmplitudes[i] * dt
      arr[idx] += drift
      arr[idx + 2] += drift * 0.5

      // Recycle below ground
      if (arr[idx + 1] < -2) {
        const angle = Math.random() * Math.PI * 2
        const r = Math.random() * this._radius
        arr[idx] = cameraPos.x + Math.cos(angle) * r
        arr[idx + 1] = cameraPos.y + 25 + Math.random() * 10
        arr[idx + 2] = cameraPos.z + Math.sin(angle) * r
      }
    }
    posAttr.needsUpdate = true
  }

  show() { this.mesh.visible = true }
  hide() { this.mesh.visible = false }

  dispose() {
    this.mesh.visible = false
    this._scene.remove(this.mesh)
    this._geometry.dispose()
    this._material.dispose()
  }
}

// =============================================================================
// AURORA SYSTEM (ribbon mesh)
// =============================================================================

class AuroraSystem {
  constructor(scene) {
    this._scene = scene
    this._segmentsX = 64
    this._segmentsY = 4

    this._geometry = new THREE.PlaneGeometry(200, 20, this._segmentsX, this._segmentsY)

    // Store original vertex positions for animation offset
    const posAttr = this._geometry.attributes.position
    this._basePositions = new Float32Array(posAttr.array.length)
    this._basePositions.set(posAttr.array)

    // Initialize vertex colors
    const vertCount = posAttr.count
    const colors = new Float32Array(vertCount * 3)
    for (let i = 0; i < vertCount; i++) {
      colors[i * 3] = 0.1
      colors[i * 3 + 1] = 0.8
      colors[i * 3 + 2] = 0.3
    }
    this._geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))

    this._material = new THREE.MeshBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.35,
      blending: THREE.AdditiveBlending,
      fog: false,
      side: THREE.DoubleSide,
      depthWrite: false,
    })

    this.mesh = new THREE.Mesh(this._geometry, this._material)
    this.mesh.position.y = 130
    this.mesh.rotation.x = -Math.PI * 0.15
    this.mesh.visible = false
    this.mesh.frustumCulled = false
    scene.add(this.mesh)

    // Pre-allocate color temp values
    this._colorA = new THREE.Color()
    this._colorB = new THREE.Color()
    this._colorC = new THREE.Color()
  }

  update(elapsed) {
    if (!this.mesh.visible) return

    const posAttr = this._geometry.attributes.position
    const colorAttr = this._geometry.attributes.color
    const pos = posAttr.array
    const col = colorAttr.array
    const base = this._basePositions
    const vertCount = posAttr.count

    for (let i = 0; i < vertCount; i++) {
      const bx = base[i * 3]
      const by = base[i * 3 + 1]

      // Normalized X along ribbon (0..1)
      const nx = (bx + 100) / 200

      // Sine-wave Y displacement (ripple along ribbon)
      const waveY = Math.sin(nx * 6 + elapsed * 0.8) * 3.0
        + Math.sin(nx * 3 + elapsed * 0.5) * 2.0

      // Sine-wave Z displacement (depth undulation)
      const waveZ = Math.sin(nx * 4 + elapsed * 0.6) * 1.5

      pos[i * 3 + 1] = by + waveY
      pos[i * 3 + 2] = base[i * 3 + 2] + waveZ

      // Cycling vertex colors: green -> teal -> purple
      const phase = nx * 3 + elapsed * 0.3
      const r = 0.15 + 0.35 * Math.max(0, Math.sin(phase + 2.0))
      const g = 0.4 + 0.4 * Math.max(0, Math.sin(phase))
      const b = 0.3 + 0.5 * Math.max(0, Math.sin(phase + 1.0))

      col[i * 3] = r
      col[i * 3 + 1] = g
      col[i * 3 + 2] = b
    }

    posAttr.needsUpdate = true
    colorAttr.needsUpdate = true
  }

  show() { this.mesh.visible = true }
  hide() { this.mesh.visible = false }

  dispose() {
    this.mesh.visible = false
    this._scene.remove(this.mesh)
    this._geometry.dispose()
    this._material.dispose()
  }
}

// =============================================================================
// HELPERS
// =============================================================================

function _rollWeather(phaseName) {
  const table = WEATHER_SCHEDULE[phaseName] || WEATHER_SCHEDULE.Day
  const roll = Math.random()
  let cumulative = 0
  for (const [state, prob] of Object.entries(table)) {
    cumulative += prob
    if (roll <= cumulative) return state
  }
  return 'clear'
}

function _lerpModifiers(out, from, to, t) {
  for (const key of MODIFIER_KEYS) {
    out[key] = from[key] + (to[key] - from[key]) * t
  }
}

function _extractModifiers(preset) {
  const m = {}
  for (const key of MODIFIER_KEYS) {
    m[key] = preset[key]
  }
  return m
}

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useVillageWeather() {
  // Reactive state (exposed for HUD)
  const weatherState = ref('clear')
  const isTransitioning = ref(false)

  // Private state
  let _scene = null
  let _isVR = false
  let _rainSystem = null
  let _snowSystem = null
  let _auroraSystem = null
  let _thunderCallback = null

  // Transition state
  let _currentModifiers = { ...CLEAR_MODIFIERS }
  let _targetModifiers = null
  let _transitionProgress = 0
  let _transitionDuration = 15 // seconds
  let _fromModifiers = null

  // Schedule timer
  let _weatherTimer = 0
  let _nextWeatherChange = 180 + Math.random() * 120

  // Lightning state
  let _lightningActive = false
  let _lightningTimer = 0
  let _lightningDuration = 0.15
  let _thunderPending = false
  let _thunderDelay = 0

  // Output object reused each frame to avoid allocations
  const _output = {
    fogDensityMultiplier: 1.0,
    ambientIntensityMod: 0,
    sunIntensityMultiplier: 1.0,
    exposureMod: 0,
    lightningFlash: false,
  }

  // =========================================================================
  // INIT
  // =========================================================================

  function init(scene, isVR = false) {
    _scene = scene
    _isVR = isVR
    _rainSystem = new RainSystem(scene, isVR)
    _snowSystem = new SnowSystem(scene, isVR)
    _auroraSystem = new AuroraSystem(scene)
  }

  // =========================================================================
  // CALLBACKS
  // =========================================================================

  function setThunderCallback(cb) {
    _thunderCallback = cb
  }

  function setVR(isVR) {
    _isVR = isVR
    if (_rainSystem) _rainSystem.setParticleCount(isVR ? 400 : 800)
    if (_snowSystem) _snowSystem.setParticleCount(isVR ? 200 : 400)
  }

  // =========================================================================
  // UPDATE (called from _animate loop)
  // =========================================================================

  function update(dt, elapsed, cameraPos, villageHour, phaseName) {
    if (!_scene) {
      return _output
    }

    // --- 1. Schedule check: roll new weather if timer expired ---
    _weatherTimer += dt
    if (_weatherTimer >= _nextWeatherChange) {
      _weatherTimer = 0
      _nextWeatherChange = 180 + Math.random() * 120
      const newWeather = _rollWeather(phaseName)
      if (newWeather !== weatherState.value) {
        _beginTransition(newWeather)
      }
    }

    // --- 2. Transition lerp: blend modifiers over 15s ---
    if (_targetModifiers) {
      _transitionProgress += dt / _transitionDuration
      if (_transitionProgress >= 1) {
        _transitionProgress = 1
        _currentModifiers = { ..._targetModifiers }
        _targetModifiers = null
        _fromModifiers = null
        isTransitioning.value = false
      } else {
        // Smoothstep for natural easing
        const t = _transitionProgress
        const smooth = t * t * (3 - 2 * t)
        _lerpModifiers(_currentModifiers, _fromModifiers, _targetModifiers, smooth)
      }
    }

    // --- 3. Update particle systems based on current effective state ---
    const preset = WEATHER_PRESETS[weatherState.value]

    // Rain
    if (preset.particleType === 'rain') {
      _rainSystem.show()
      _rainSystem.update(dt, cameraPos)
    } else {
      _rainSystem.hide()
    }

    // Snow
    if (preset.particleType === 'snow') {
      _snowSystem.show()
      _snowSystem.update(dt, cameraPos)
    } else {
      _snowSystem.hide()
    }

    // Aurora: night-only (disabled if villageHour 6-18)
    const isNight = villageHour < 6 || villageHour >= 18
    if (preset.auroraEnabled && isNight) {
      _auroraSystem.show()
      _auroraSystem.update(elapsed)
    } else {
      _auroraSystem.hide()
    }

    // --- 4. Lightning check + thunder delay ---
    let flashActive = false

    if (_lightningActive) {
      _lightningTimer += dt
      if (_lightningTimer >= _lightningDuration) {
        _lightningActive = false
        _lightningTimer = 0
      } else {
        flashActive = true
      }
    }

    // Roll for new lightning strike
    const effectiveChance = _currentModifiers.fogDensityMultiplier > 2.0
      ? preset.lightningChance
      : 0
    if (!_lightningActive && effectiveChance > 0 && Math.random() < effectiveChance * dt) {
      _lightningActive = true
      _lightningTimer = 0
      // Schedule thunder after random delay
      _thunderPending = true
      _thunderDelay = 0.5 + Math.random() * 1.5
    }

    // Thunder callback delay
    if (_thunderPending) {
      _thunderDelay -= dt
      if (_thunderDelay <= 0) {
        _thunderPending = false
        if (_thunderCallback) _thunderCallback()
      }
    }

    // --- 5. Build output ---
    _output.fogDensityMultiplier = _currentModifiers.fogDensityMultiplier
    _output.ambientIntensityMod = _currentModifiers.ambientIntensityMod
    _output.sunIntensityMultiplier = _currentModifiers.sunIntensityMultiplier
    _output.exposureMod = _currentModifiers.exposureMod
    _output.lightningFlash = flashActive

    return _output
  }

  // =========================================================================
  // TRANSITION
  // =========================================================================

  function _beginTransition(newState) {
    const preset = WEATHER_PRESETS[newState]
    if (!preset) return

    _fromModifiers = { ..._currentModifiers }
    _targetModifiers = _extractModifiers(preset)
    _transitionProgress = 0
    isTransitioning.value = true
    weatherState.value = newState
  }

  // =========================================================================
  // MANUAL OVERRIDE (debug)
  // =========================================================================

  function setWeather(state) {
    if (!WEATHER_PRESETS[state]) return
    _weatherTimer = 0
    _nextWeatherChange = 180 + Math.random() * 120
    _beginTransition(state)
  }

  // =========================================================================
  // DISPOSE
  // =========================================================================

  function dispose() {
    if (_rainSystem) { _rainSystem.dispose(); _rainSystem = null }
    if (_snowSystem) { _snowSystem.dispose(); _snowSystem = null }
    if (_auroraSystem) { _auroraSystem.dispose(); _auroraSystem = null }
    _scene = null
    _thunderCallback = null
    _targetModifiers = null
    _fromModifiers = null
    _lightningActive = false
    _thunderPending = false
    weatherState.value = 'clear'
    isTransitioning.value = false
  }

  return {
    weatherState,
    isTransitioning,
    init,
    update,
    dispose,
    setWeather,
    setThunderCallback,
    setVR,
  }
}
