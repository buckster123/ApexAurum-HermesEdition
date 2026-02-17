// =============================================================================
// useVillageSoundscape.js — Phase 11: Spatial Audio
//
// Three-layer audio for the Athaverse Village:
// 1. Synthesized zone ambients (14 unique soundscapes, procedural)
// 2. Pre-generated TTS agent voices (musings & dialogue)
// 3. FPV footstep synthesis
//
// Uses THREE.AudioListener for spatial positioning. Separate AudioContext
// from useSound.js (UI beeps). Both coexist fine.
//
// "The Village finally speaks."
// =============================================================================

import { ref } from 'vue'
import * as THREE from 'three'

// =============================================================================
// CONSTANTS
// =============================================================================

const ACTIVATION_RADIUS = 35
const ZONE_REF_DISTANCE = 8
const ZONE_ROLLOFF = 1.5
const ZONE_MAX_DISTANCE = 40
const ZONE_VOLUME = 0.4
const VOICE_REF_DISTANCE = 5
const VOICE_ROLLOFF = 2
const VOICE_MAX_DISTANCE = 25
const VOICE_VOLUME = 0.8
const FOOTSTEP_WALK_INTERVAL = 0.45
const FOOTSTEP_SPRINT_INTERVAL = 0.28
const BUFFER_DURATION = 4 // seconds

// =============================================================================
// ZONE AMBIENT GENERATORS
//
// Each function fills stereo Float32Arrays (left, right) with a unique
// synthesized soundscape. All math, no files.
// =============================================================================

const ZONE_GENERATORS = {
  village_square(L, R, n, sr) {
    // Flowing water + gentle crowd murmur
    for (let i = 0; i < n; i++) {
      const t = i / sr
      const noise = (Math.random() * 2 - 1) * 0.08
      const lfo = 0.5 + 0.5 * Math.sin(t * 1.2)
      const water = noise * lfo * 0.15
      const murmur = (Math.random() * 2 - 1) * 0.02 * (0.3 + 0.3 * Math.sin(t * 0.3))
      L[i] = water + murmur
      R[i] = water * 0.9 + murmur * 1.1
    }
  },

  dj_booth(L, R, n, sr) {
    // Bass pulse + subtle beat
    for (let i = 0; i < n; i++) {
      const t = i / sr
      const bass = Math.sin(t * Math.PI * 2 * 60) * 0.12 * (0.4 + 0.6 * Math.sin(t * Math.PI))
      const beat =
        t % 0.5 < 0.01
          ? Math.sin(t * 2000) * 0.06 * Math.max(0, 1 - ((t % 0.5) * 100))
          : 0
      L[i] = bass + beat
      R[i] = bass * 0.95 + beat
    }
  },

  memory_garden(L, R, n, sr) {
    // Wind chimes (pentatonic decaying sines) + breeze
    for (let i = 0; i < n; i++) {
      const t = i / sr
      const breeze = (Math.random() * 2 - 1) * 0.03 * (0.5 + 0.5 * Math.sin(t * 0.4))
      const chimes = [523, 659, 784]
      let chime = 0
      for (let c = 0; c < chimes.length; c++) {
        const onset = c * 1.2 + 0.3
        const age = t - onset
        if (age > 0 && age < 2) {
          chime += Math.sin(age * Math.PI * 2 * chimes[c]) * 0.04 * Math.exp(-age * 2)
        }
      }
      L[i] = breeze + chime
      R[i] = breeze * 1.1 + chime * 0.9
    }
  },

  file_shed(L, R, n, sr) {
    // Quiet hum + paper rustling
    for (let i = 0; i < n; i++) {
      const t = i / sr
      const hum = Math.sin(t * Math.PI * 2 * 120) * 0.025
      const rustle = (Math.random() * 2 - 1) * 0.015 * Math.max(0, Math.sin(t * 2.5))
      L[i] = hum + rustle
      R[i] = hum + rustle * 0.8
    }
  },

  workshop(L, R, n, sr) {
    // Hammer hits (noise transient + anvil ring) + fire crackle
    for (let i = 0; i < n; i++) {
      const t = i / sr
      const period = t % 1.5
      const hammer =
        period < 0.02 ? (Math.random() * 2 - 1) * 0.15 * (1 - period / 0.02) : 0
      const ring =
        period < 0.5
          ? Math.sin(period * Math.PI * 2 * 2200) * 0.03 * Math.exp(-period * 8)
          : 0
      const crackle = Math.random() < 0.003 ? (Math.random() * 2 - 1) * 0.08 : 0
      L[i] = hammer + ring + crackle
      R[i] = hammer * 0.8 + ring * 1.1 + crackle * 0.9
    }
  },

  bridge_portal(L, R, n, sr) {
    // Binaural shimmer (440/443Hz beating) + portal drone
    for (let i = 0; i < n; i++) {
      const t = i / sr
      const shimmer =
        Math.sin(t * Math.PI * 2 * 440) * 0.03 + Math.sin(t * Math.PI * 2 * 443) * 0.03
      const hum =
        Math.sin(t * Math.PI * 2 * 55) * 0.06 + Math.sin(t * Math.PI * 2 * 110) * 0.02
      L[i] = shimmer * 0.8 + hum
      R[i] = shimmer * 1.2 + hum
    }
  },

  library(L, R, n, sr) {
    // Hushed whispers + page-turning bursts
    for (let i = 0; i < n; i++) {
      const t = i / sr
      const whisper = (Math.random() * 2 - 1) * 0.012 * (0.3 + 0.3 * Math.sin(t * 0.7))
      const pageT = t % 3.0
      const page =
        pageT > 2.5 && pageT < 2.55
          ? (Math.random() * 2 - 1) * 0.06 * (1 - (pageT - 2.5) / 0.05)
          : 0
      L[i] = whisper + page
      R[i] = whisper * 0.9 + page * 1.1
    }
  },

  watchtower(L, R, n, sr) {
    // Wind howl (sweeping freq) + flag flutter
    for (let i = 0; i < n; i++) {
      const t = i / sr
      const windFreq = 300 + 200 * Math.sin(t * 0.3)
      const wind =
        Math.sin(t * Math.PI * 2 * windFreq) * (Math.random() * 0.5 + 0.5) * 0.06
      const flutter = (Math.random() * 2 - 1) * 0.04 * Math.abs(Math.sin(t * 15))
      L[i] = wind + flutter
      R[i] = wind * 0.85 + flutter * 1.15
    }
  },

  arena(L, R, n, sr) {
    // Distant roar swell + metallic clash transients
    for (let i = 0; i < n; i++) {
      const t = i / sr
      const roar =
        (Math.random() * 2 - 1) * 0.08 * (0.4 + 0.6 * Math.abs(Math.sin(t * 0.2)))
      const clashT = t % 2.2
      const clash =
        clashT < 0.01 ? Math.sin(clashT * 5000) * 0.1 * (1 - clashT / 0.01) : 0
      L[i] = roar + clash
      R[i] = roar * 0.9 + clash * 1.1
    }
  },

  bazaar(L, R, n, sr) {
    // Crowd chatter + coin clinks
    for (let i = 0; i < n; i++) {
      const t = i / sr
      const chatter =
        (Math.random() * 2 - 1) *
        0.04 *
        (0.5 + 0.3 * Math.sin(t * 1.5) + 0.2 * Math.sin(t * 0.4))
      const coinPhase = Math.sin(t * 7.3) * Math.sin(t * 3.1)
      const coin =
        coinPhase > 0.98
          ? Math.sin(t * Math.PI * 2 * 3500) * 0.05 * Math.exp(-(coinPhase - 0.98) * 50)
          : 0
      L[i] = chatter + coin
      R[i] = chatter * 1.05 + coin * 0.8
    }
  },

  apothecary(L, R, n, sr) {
    // Bubbling liquid + glass clinks
    for (let i = 0; i < n; i++) {
      const t = i / sr
      const bubbleT = t % 0.3
      const bubble =
        bubbleT < 0.05
          ? Math.sin(bubbleT * 600) * 0.06 * (1 - bubbleT / 0.05) * (0.5 + 0.5 * Math.sin(t * 2))
          : 0
      const glassT = t % 2.7
      const glass =
        glassT < 0.15
          ? Math.sin(glassT * Math.PI * 2 * 4000) * 0.03 * Math.exp(-glassT * 20)
          : 0
      L[i] = bubble + glass
      R[i] = bubble * 0.9 + glass * 1.2
    }
  },

  nexus_tower(L, R, n, sr) {
    // Electric crackling + detuned energy hum
    for (let i = 0; i < n; i++) {
      const t = i / sr
      const hum = (Math.sin(t * Math.PI * 2 * 80) + Math.sin(t * Math.PI * 2 * 82)) * 0.04
      const crackle = Math.random() < 0.005 ? (Math.random() * 2 - 1) * 0.12 : 0
      L[i] = hum + crackle
      R[i] = hum + crackle * 0.7
    }
  },

  mines(L, R, n, sr) {
    // Water drips + distant pickaxe taps
    for (let i = 0; i < n; i++) {
      const t = i / sr
      const dripT = t % 2.0
      const drip =
        dripT < 0.08
          ? Math.sin(dripT * Math.PI * 2 * 800) * 0.06 * Math.exp(-dripT * 30)
          : 0
      const pickT = (t + 0.7) % 3.0
      const pick = pickT < 0.03 ? (Math.random() * 2 - 1) * 0.08 * (1 - pickT / 0.03) : 0
      L[i] = drip + pick
      R[i] = drip * 1.1 + pick * 0.85
    }
  },

  sanctum(L, R, n, sr) {
    // Deep om drone + harmonics + bell resonance
    for (let i = 0; i < n; i++) {
      const t = i / sr
      const om =
        (Math.sin(t * Math.PI * 2 * 66) * 0.06 +
          Math.sin(t * Math.PI * 2 * 132) * 0.03 +
          Math.sin(t * Math.PI * 2 * 198) * 0.015) *
        (0.7 + 0.3 * Math.sin(t * 0.2))
      const bellT = t % 3.5
      const bell =
        bellT < 1.5
          ? Math.sin(bellT * Math.PI * 2 * 1200) * 0.04 * Math.exp(-bellT * 3)
          : 0
      L[i] = om + bell
      R[i] = om + bell * 0.8
    }
  },
}

// =============================================================================
// COMPOSABLE
// =============================================================================

export function useVillageSoundscape() {
  const masterVolume = ref(parseFloat(localStorage.getItem('village_audio_volume') ?? '0.6'))
  const audioReady = ref(false)

  let _listener = null
  let _camera = null
  let _scene = null
  let _agents = null

  // Zone ambients: Map<zoneName, { audio, anchor, active }>
  const _zoneAudios = new Map()

  // Agent voice: Map<agentId, THREE.PositionalAudio>
  const _agentVoices = new Map()

  // Voice line cache: Map<key, AudioBuffer>
  const _voiceBufferCache = new Map()

  // FPV footstep state
  let _footstepTimer = 0

  // =========================================================================
  // INIT
  // =========================================================================

  function init(camera, scene, agents, villageLayout) {
    _camera = camera
    _scene = scene
    _agents = agents

    // Create AudioListener and attach to camera
    _listener = new THREE.AudioListener()
    _listener.setMasterVolume(masterVolume.value)
    camera.add(_listener)

    const ctx = _listener.context
    const sampleRate = ctx.sampleRate

    // Generate zone ambient buffers and create PositionalAudio per zone
    for (const [zoneName, zoneData] of Object.entries(villageLayout)) {
      const generator = ZONE_GENERATORS[zoneName]
      if (!generator) continue

      const length = sampleRate * BUFFER_DURATION
      const buffer = ctx.createBuffer(2, length, sampleRate)
      const left = buffer.getChannelData(0)
      const right = buffer.getChannelData(1)
      generator(left, right, length, sampleRate)

      const audio = new THREE.PositionalAudio(_listener)
      audio.setBuffer(buffer)
      audio.setRefDistance(ZONE_REF_DISTANCE)
      audio.setRolloffFactor(ZONE_ROLLOFF)
      audio.setMaxDistance(ZONE_MAX_DISTANCE)
      audio.setLoop(true)
      audio.setVolume(ZONE_VOLUME)

      // Anchor at zone position (y=1.5 for ear height)
      const anchor = new THREE.Object3D()
      anchor.position.set(zoneData.pos[0], 1.5, zoneData.pos[2])
      scene.add(anchor)
      anchor.add(audio)

      _zoneAudios.set(zoneName, { audio, anchor, active: false })
    }

    // Create reusable PositionalAudio per agent for voice lines
    for (const [agentId, agent] of agents.entries()) {
      const voice = new THREE.PositionalAudio(_listener)
      voice.setRefDistance(VOICE_REF_DISTANCE)
      voice.setRolloffFactor(VOICE_ROLLOFF)
      voice.setMaxDistance(VOICE_MAX_DISTANCE)
      voice.setLoop(false)
      voice.setVolume(VOICE_VOLUME)
      agent.group.add(voice)
      _agentVoices.set(agentId, voice)
    }

    audioReady.value = true
  }

  // =========================================================================
  // UPDATE (called from _animate loop)
  // =========================================================================

  function update(dt, cameraPosition, fpvState) {
    if (!_listener || !audioReady.value) return

    // Skip if AudioContext is suspended (autoplay policy)
    if (_listener.context.state === 'suspended') return

    // --- Zone ambient distance activation ---
    for (const [, entry] of _zoneAudios) {
      const pos = entry.anchor.position
      const dx = pos.x - cameraPosition.x
      const dz = pos.z - cameraPosition.z
      const dist = Math.sqrt(dx * dx + dz * dz)

      if (dist < ACTIVATION_RADIUS) {
        if (!entry.active) {
          try {
            entry.audio.play()
          } catch {
            /* already playing or not ready */
          }
          entry.active = true
        }
      } else {
        if (entry.active) {
          try {
            entry.audio.stop()
          } catch {
            /* already stopped */
          }
          entry.active = false
        }
      }
    }

    // --- FPV Footsteps ---
    if (fpvState && fpvState.isMoving && fpvState.isFPV) {
      const interval = fpvState.isSprinting
        ? FOOTSTEP_SPRINT_INTERVAL
        : FOOTSTEP_WALK_INTERVAL
      _footstepTimer += dt
      if (_footstepTimer >= interval) {
        _footstepTimer -= interval
        _playFootstep()
      }
    } else {
      _footstepTimer = 0
    }
  }

  // =========================================================================
  // AGENT VOICE PLAYBACK
  // =========================================================================

  async function playAgentVoice(agentId, lineText, lineKey) {
    if (!audioReady.value || !_listener) return

    const voice = _agentVoices.get(agentId)
    if (!voice) return

    // Stop any current playback for this agent
    if (voice.isPlaying) {
      try {
        voice.stop()
      } catch {
        /* noop */
      }
    }

    // Check cache first
    let buffer = _voiceBufferCache.get(lineKey)

    if (!buffer) {
      // Load from pre-generated OGG file
      const url = `/audio/agents/${lineKey}.ogg`
      try {
        const response = await fetch(url)
        if (!response.ok) return // File not available — silent degradation
        const arrayBuffer = await response.arrayBuffer()
        buffer = await _listener.context.decodeAudioData(arrayBuffer)
        _voiceBufferCache.set(lineKey, buffer)
      } catch {
        return // Progressive enhancement — audio is optional
      }
    }

    voice.setBuffer(buffer)
    voice.setVolume(VOICE_VOLUME)
    try {
      voice.play()
    } catch {
      /* context not ready */
    }
  }

  // =========================================================================
  // FPV FOOTSTEP SYNTHESIS
  // =========================================================================

  function _playFootstep() {
    if (!_listener || masterVolume.value === 0) return

    const ctx = _listener.context
    if (ctx.state !== 'running') return

    try {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      const filter = ctx.createBiquadFilter()

      osc.connect(filter)
      filter.connect(gain)
      gain.connect(ctx.destination)

      osc.type = 'square'
      osc.frequency.value = 70 + Math.random() * 50
      filter.type = 'lowpass'
      filter.frequency.value = 180 + Math.random() * 60

      const now = ctx.currentTime
      gain.gain.setValueAtTime(0, now)
      gain.gain.linearRampToValueAtTime(0.04 * masterVolume.value, now + 0.005)
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.07)

      osc.start(now)
      osc.stop(now + 0.08)
    } catch {
      /* audio synthesis error — skip */
    }
  }

  // =========================================================================
  // THUNDER (Phase 16 — Weather)
  // =========================================================================

  function playThunder() {
    if (!_listener || masterVolume.value === 0) return

    const ctx = _listener.context
    if (ctx.state !== 'running') return

    try {
      // Low-frequency noise burst with exponential decay, lowpass filtered
      const duration = 1.5
      const sampleRate = ctx.sampleRate
      const length = Math.floor(sampleRate * duration)
      const buffer = ctx.createBuffer(1, length, sampleRate)
      const data = buffer.getChannelData(0)

      for (let i = 0; i < length; i++) {
        const t = i / sampleRate
        const envelope = Math.exp(-t * 3) * 0.6
        data[i] = (Math.random() * 2 - 1) * envelope
      }

      const source = ctx.createBufferSource()
      source.buffer = buffer

      const filter = ctx.createBiquadFilter()
      filter.type = 'lowpass'
      filter.frequency.value = 200

      const gain = ctx.createGain()
      gain.gain.value = 0.4 * masterVolume.value

      source.connect(filter)
      filter.connect(gain)
      gain.connect(ctx.destination)

      source.start()
    } catch {
      /* audio synthesis error — skip */
    }
  }

  // =========================================================================
  // VOLUME CONTROL
  // =========================================================================

  function setVolume(val) {
    masterVolume.value = Math.max(0, Math.min(1, val))
    localStorage.setItem('village_audio_volume', String(masterVolume.value))
    if (_listener) {
      _listener.setMasterVolume(masterVolume.value)
    }
  }

  // =========================================================================
  // DISPOSE
  // =========================================================================

  function dispose() {
    // Stop and remove all zone audios
    for (const [, entry] of _zoneAudios) {
      if (entry.audio.isPlaying) {
        try {
          entry.audio.stop()
        } catch {
          /* noop */
        }
      }
      entry.audio.disconnect()
      if (_scene) _scene.remove(entry.anchor)
    }
    _zoneAudios.clear()

    // Stop agent voices
    for (const [, voice] of _agentVoices) {
      if (voice.isPlaying) {
        try {
          voice.stop()
        } catch {
          /* noop */
        }
      }
      voice.disconnect()
    }
    _agentVoices.clear()

    // Clear buffer cache
    _voiceBufferCache.clear()

    // Remove listener from camera
    if (_listener && _camera) {
      _camera.remove(_listener)
    }

    _listener = null
    _camera = null
    _scene = null
    _agents = null
    _footstepTimer = 0
    audioReady.value = false
  }

  return {
    masterVolume,
    audioReady,
    init,
    update,
    dispose,
    setVolume,
    playAgentVoice,
    playThunder,
  }
}
