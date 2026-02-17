// =============================================================================
// useVillageDayNight.js — Phase 12: Dynamic day/night cycle
//
// Drives lighting, sky, fog, stars, and firefly intensity across a 24-hour
// village time cycle. Presets for Night/Dawn/Day/Dusk are interpolated via
// smoothstep for natural transitions.
// =============================================================================

import { ref } from 'vue'
import * as THREE from 'three'

// =============================================================================
// PHASE PRESETS
// =============================================================================

const PHASES = {
  night: {
    sunAngle: -Math.PI / 2,
    sunColor: new THREE.Color(0x4466aa),
    sunIntensity: 0.15,
    ambientColor: new THREE.Color(0x0a0a2e),
    ambientIntensity: 0.3,
    hemiSkyColor: new THREE.Color(0x0a0a2e),
    hemiGroundColor: new THREE.Color(0x1a0e00),
    hemiIntensity: 0.25,
    fogColor: new THREE.Color(0x060610),
    fogDensity: 0.012,
    zoneLightIntensity: 0.8,
    exposure: 0.7,
    starOpacity: 0.8,
    fireflyMultiplier: 1.0,
    skyHorizon: new THREE.Color(0x0a0a14),
    skyMid: new THREE.Color(0x0a0820),
    skyZenith: new THREE.Color(0x010108),
  },
  dawn: {
    sunAngle: 0,
    sunColor: new THREE.Color(0xffaa66),
    sunIntensity: 0.8,
    ambientColor: new THREE.Color(0x332244),
    ambientIntensity: 0.4,
    hemiSkyColor: new THREE.Color(0x443355),
    hemiGroundColor: new THREE.Color(0x2d1f00),
    hemiIntensity: 0.35,
    fogColor: new THREE.Color(0x1a1020),
    fogDensity: 0.01,
    zoneLightIntensity: 0.5,
    exposure: 0.85,
    starOpacity: 0.1,
    fireflyMultiplier: 0.3,
    skyHorizon: new THREE.Color(0x553333),
    skyMid: new THREE.Color(0x331133),
    skyZenith: new THREE.Color(0x0a0515),
  },
  day: {
    sunAngle: Math.PI / 2,
    sunColor: new THREE.Color(0xffe4b5),
    sunIntensity: 1.5,
    ambientColor: new THREE.Color(0x3a3a5e),
    ambientIntensity: 0.5,
    hemiSkyColor: new THREE.Color(0x4466aa),
    hemiGroundColor: new THREE.Color(0x2d1f00),
    hemiIntensity: 0.4,
    fogColor: new THREE.Color(0x1a1a2e),
    fogDensity: 0.006,
    zoneLightIntensity: 0.15,
    exposure: 1.1,
    starOpacity: 0.0,
    fireflyMultiplier: 0.0,
    skyHorizon: new THREE.Color(0x2a3050),
    skyMid: new THREE.Color(0x1a2040),
    skyZenith: new THREE.Color(0x0a0a20),
  },
  dusk: {
    sunAngle: Math.PI,
    sunColor: new THREE.Color(0xff7744),
    sunIntensity: 0.7,
    ambientColor: new THREE.Color(0x2a1a3e),
    ambientIntensity: 0.4,
    hemiSkyColor: new THREE.Color(0x3a2244),
    hemiGroundColor: new THREE.Color(0x2d1f00),
    hemiIntensity: 0.3,
    fogColor: new THREE.Color(0x15101a),
    fogDensity: 0.01,
    zoneLightIntensity: 0.6,
    exposure: 0.8,
    starOpacity: 0.2,
    fireflyMultiplier: 0.5,
    skyHorizon: new THREE.Color(0x442222),
    skyMid: new THREE.Color(0x220a22),
    skyZenith: new THREE.Color(0x080410),
  },
}

// Keyframe table: maps hour ranges to phase pairs for interpolation
const PHASE_KEYFRAMES = [
  { hour: 0, phase: 'night' },
  { hour: 5, phase: 'night' },
  { hour: 6, phase: 'dawn' },
  { hour: 7, phase: 'dawn' },
  { hour: 8, phase: 'day' },
  { hour: 16, phase: 'day' },
  { hour: 17, phase: 'dusk' },
  { hour: 19, phase: 'dusk' },
  { hour: 20, phase: 'night' },
  { hour: 24, phase: 'night' },
]

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useVillageDayNight() {
  // Reactive state (exposed for HUD)
  const villageHour = ref(22) // Start at night, matching existing aesthetic
  const phaseName = ref('Night')
  const isPaused = ref(false)

  // 1 real minute = 1 village hour → full cycle in 24 min
  const cycleSpeed = ref(1 / 60)

  // Internal references (set at init)
  let _dirLight = null
  let _ambient = null
  let _hemi = null
  let _zoneLights = []
  let _skyDome = null
  let _stars = null
  let _fog = null
  let _renderer = null

  // Pre-baked sky vertex color arrays (one per phase)
  const _skyArrays = {}

  // Temp colors for lerping (avoid allocations)
  const _c1 = new THREE.Color()
  const _c2 = new THREE.Color()

  // =========================================================================
  // INIT
  // =========================================================================

  function init({ dirLight, ambient, hemi, zoneLights, skyDome, stars, fog, renderer }) {
    _dirLight = dirLight
    _ambient = ambient
    _hemi = hemi
    _zoneLights = zoneLights || []
    _skyDome = skyDome
    _stars = stars
    _fog = fog
    _renderer = renderer
    _bakeSkyArrays()
  }

  // =========================================================================
  // PRE-BAKE SKY VERTEX COLORS
  // =========================================================================

  function _bakeSkyArrays() {
    if (!_skyDome) return
    const posAttr = _skyDome.geometry.getAttribute('position')
    const vertCount = posAttr.count

    for (const [name, preset] of Object.entries(PHASES)) {
      const arr = new Float32Array(vertCount * 3)
      for (let i = 0; i < vertCount; i++) {
        const y = posAttr.getY(i)
        const normalizedY = (y + 200) / 400

        let color
        if (normalizedY < 0.55) {
          color = preset.skyHorizon.clone().lerp(preset.skyMid, normalizedY / 0.55)
        } else {
          color = preset.skyMid.clone().lerp(preset.skyZenith, (normalizedY - 0.55) / 0.45)
        }
        arr[i * 3] = color.r
        arr[i * 3 + 1] = color.g
        arr[i * 3 + 2] = color.b
      }
      _skyArrays[name] = arr
    }
  }

  // =========================================================================
  // INTERPOLATION HELPERS
  // =========================================================================

  function _getInterpolation(hour) {
    const h = ((hour % 24) + 24) % 24
    for (let i = 0; i < PHASE_KEYFRAMES.length - 1; i++) {
      const a = PHASE_KEYFRAMES[i]
      const b = PHASE_KEYFRAMES[i + 1]
      if (h >= a.hour && h <= b.hour) {
        const range = b.hour - a.hour
        const t = range > 0 ? (h - a.hour) / range : 0
        const smooth = t * t * (3 - 2 * t) // smoothstep
        return { from: a.phase, to: b.phase, t: smooth }
      }
    }
    return { from: 'night', to: 'night', t: 0 }
  }

  function _lerp(a, b, t) {
    return a + (b - a) * t
  }

  function _getPhaseName(hour) {
    const h = ((hour % 24) + 24) % 24
    if (h >= 5 && h < 8) return 'Dawn'
    if (h >= 8 && h < 17) return 'Day'
    if (h >= 17 && h < 20) return 'Dusk'
    return 'Night'
  }

  // =========================================================================
  // UPDATE (called from _animate loop)
  // =========================================================================

  function update(dt) {
    if (isPaused.value) {
      return { fireflyMultiplier: PHASES[_getInterpolation(villageHour.value).from]?.fireflyMultiplier ?? 0.5 }
    }

    // Advance time
    villageHour.value = (villageHour.value + dt * cycleSpeed.value) % 24
    const hour = villageHour.value
    phaseName.value = _getPhaseName(hour)

    const { from, to, t } = _getInterpolation(hour)
    const fromP = PHASES[from]
    const toP = PHASES[to]

    // --- Directional light (sun/moon) ---
    if (_dirLight) {
      _c1.copy(fromP.sunColor).lerp(toP.sunColor, t)
      _dirLight.color.copy(_c1)
      _dirLight.intensity = _lerp(fromP.sunIntensity, toP.sunIntensity, t)

      const angle = _lerp(fromP.sunAngle, toP.sunAngle, t)
      const radius = 35
      _dirLight.position.set(
        Math.cos(angle) * radius,
        Math.sin(angle) * radius + 5,
        Math.sin(angle * 0.5) * 15,
      )
    }

    // --- Ambient light ---
    if (_ambient) {
      _c1.copy(fromP.ambientColor).lerp(toP.ambientColor, t)
      _ambient.color.copy(_c1)
      _ambient.intensity = _lerp(fromP.ambientIntensity, toP.ambientIntensity, t)
    }

    // --- Hemisphere light ---
    if (_hemi) {
      _c1.copy(fromP.hemiSkyColor).lerp(toP.hemiSkyColor, t)
      _hemi.color.copy(_c1)
      _c2.copy(fromP.hemiGroundColor).lerp(toP.hemiGroundColor, t)
      _hemi.groundColor.copy(_c2)
      _hemi.intensity = _lerp(fromP.hemiIntensity, toP.hemiIntensity, t)
    }

    // --- Fog ---
    if (_fog) {
      _c1.copy(fromP.fogColor).lerp(toP.fogColor, t)
      _fog.color.copy(_c1)
      _fog.density = _lerp(fromP.fogDensity, toP.fogDensity, t)
    }

    // --- Zone point lights (lanterns) ---
    const zoneI = _lerp(fromP.zoneLightIntensity, toP.zoneLightIntensity, t)
    for (const light of _zoneLights) {
      light.intensity = zoneI
    }

    // --- Stars ---
    if (_stars) {
      _stars.material.opacity = _lerp(fromP.starOpacity, toP.starOpacity, t)
    }

    // --- Tone mapping exposure ---
    if (_renderer) {
      _renderer.toneMappingExposure = _lerp(fromP.exposure, toP.exposure, t)
    }

    // --- Sky dome vertex colors ---
    if (_skyDome && _skyArrays[from] && _skyArrays[to]) {
      const colorAttr = _skyDome.geometry.getAttribute('color')
      const arr = colorAttr.array
      const fromArr = _skyArrays[from]
      const toArr = _skyArrays[to]
      for (let i = 0; i < arr.length; i++) {
        arr[i] = fromArr[i] + (toArr[i] - fromArr[i]) * t
      }
      colorAttr.needsUpdate = true
    }

    // Base values (for weather modulation — Phase 16)
    const baseFogDensity = _lerp(fromP.fogDensity, toP.fogDensity, t)
    const baseAmbientIntensity = _lerp(fromP.ambientIntensity, toP.ambientIntensity, t)
    const baseSunIntensity = _lerp(fromP.sunIntensity, toP.sunIntensity, t)
    const baseExposure = _lerp(fromP.exposure, toP.exposure, t)

    return {
      fireflyMultiplier: _lerp(fromP.fireflyMultiplier, toP.fireflyMultiplier, t),
      baseFogDensity,
      baseAmbientIntensity,
      baseSunIntensity,
      baseExposure,
    }
  }

  // =========================================================================
  // MANUAL CONTROLS
  // =========================================================================

  function setHour(hour) {
    villageHour.value = ((hour % 24) + 24) % 24
  }

  function setSpeed(villageHoursPerSecond) {
    cycleSpeed.value = villageHoursPerSecond
  }

  function togglePause() {
    isPaused.value = !isPaused.value
  }

  // =========================================================================
  // DISPOSE
  // =========================================================================

  function dispose() {
    _dirLight = null
    _ambient = null
    _hemi = null
    _zoneLights = []
    _skyDome = null
    _stars = null
    _fog = null
    _renderer = null
  }

  return {
    villageHour,
    phaseName,
    isPaused,
    cycleSpeed,
    init,
    update,
    dispose,
    setHour,
    setSpeed,
    togglePause,
  }
}
