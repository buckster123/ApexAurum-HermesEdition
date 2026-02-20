<script setup>
/**
 * BrainMap — SVG Topographic Head Map
 *
 * 2D head outline with electrode positions from the 10-20 system.
 * Each electrode glows with its dominant frequency band color.
 * ZUNA-ready: extra electrode positions hidden until enhanced mode activates.
 *
 * "The topology of thought"
 */

import { computed } from 'vue'

const props = defineProps({
  bandPowers: { type: Object, default: null },
  // Per-channel: { Fp1: { theta: 0.3, alpha: 0.5, beta: 0.15, gamma: 0.05 }, ... }
  // Or flat/aggregated: { theta: 0.3, alpha: 0.5, ... }
  streaming: { type: Boolean, default: false },
  channelCount: { type: Number, default: 8 },
  zunaActive: { type: Boolean, default: false },
})

// Band colors matching BandPowerBars
const BAND_COLORS = {
  theta: '#4FC3F7',
  alpha: '#4CAF50',
  beta:  '#FFD700',
  gamma: '#FF69B4',
}

// Standard 8-channel electrode positions (10-20 system on 300x340 SVG)
const ELECTRODES_8CH = [
  { name: 'Fp1', x: 115, y: 70,  label: 'Fp1' },
  { name: 'Fp2', x: 185, y: 70,  label: 'Fp2' },
  { name: 'F3',  x: 95,  y: 125, label: 'F3' },
  { name: 'F4',  x: 205, y: 125, label: 'F4' },
  { name: 'T7',  x: 45,  y: 180, label: 'T7' },
  { name: 'T8',  x: 255, y: 180, label: 'T8' },
  { name: 'P3',  x: 95,  y: 240, label: 'P3' },
  { name: 'P4',  x: 205, y: 240, label: 'P4' },
]

// ZUNA-enhanced positions (future, rendered hidden)
const ELECTRODES_ZUNA = [
  { name: 'Fz',  x: 150, y: 110, label: 'Fz' },
  { name: 'Cz',  x: 150, y: 180, label: 'Cz' },
  { name: 'Pz',  x: 150, y: 245, label: 'Pz' },
  { name: 'O1',  x: 115, y: 295, label: 'O1' },
  { name: 'O2',  x: 185, y: 295, label: 'O2' },
  { name: 'F7',  x: 55,  y: 115, label: 'F7' },
  { name: 'F8',  x: 245, y: 115, label: 'F8' },
  { name: 'C3',  x: 80,  y: 180, label: 'C3' },
  { name: 'C4',  x: 220, y: 180, label: 'C4' },
  { name: 'T5',  x: 55,  y: 245, label: 'T5' },
  { name: 'T6',  x: 245, y: 245, label: 'T6' },
  { name: 'FC1', x: 120, y: 145, label: 'FC1' },
  { name: 'FC2', x: 180, y: 145, label: 'FC2' },
]

// Determine if band_powers is per-channel or flat
function isPerChannel(bp) {
  if (!bp) return false
  const firstKey = Object.keys(bp)[0]
  return firstKey && typeof bp[firstKey] === 'object'
}

// Get band powers for a specific electrode
function getElectrodePowers(name) {
  if (!props.bandPowers || !props.streaming) return null
  if (isPerChannel(props.bandPowers)) {
    return props.bandPowers[name] || null
  }
  // Flat/aggregated — same powers for all electrodes
  return props.bandPowers
}

// Determine dominant band for an electrode
function getDominantBand(name) {
  const powers = getElectrodePowers(name)
  if (!powers) return null
  let maxBand = null
  let maxVal = -1
  for (const band of ['theta', 'alpha', 'beta', 'gamma']) {
    const val = powers[band] || 0
    if (val > maxVal) {
      maxVal = val
      maxBand = band
    }
  }
  return maxBand
}

// Get the color for an electrode based on dominant band
function getElectrodeColor(name) {
  const band = getDominantBand(name)
  return band ? BAND_COLORS[band] : '#555'
}

// Get the signal strength (total power) for radius scaling
function getSignalStrength(name) {
  const powers = getElectrodePowers(name)
  if (!powers) return 0
  const total = (powers.theta || 0) + (powers.alpha || 0) + (powers.beta || 0) + (powers.gamma || 0)
  return Math.min(1, total)
}

// Electrode radius: base + signal strength scaling
function getElectrodeRadius(name) {
  if (!props.streaming) return 8
  return 8 + getSignalStrength(name) * 6
}

// All electrodes visible in current mode
const activeElectrodes = computed(() => {
  return ELECTRODES_8CH
})

const zunaElectrodes = computed(() => {
  return ELECTRODES_ZUNA
})
</script>

<template>
  <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
    <div class="flex items-center justify-between mb-2">
      <h3 class="text-xs font-mono text-gray-400 uppercase tracking-wider">Brain Map</h3>
      <span class="text-[10px] font-mono text-gray-600">
        {{ channelCount }}ch &middot; 10-20 System
      </span>
    </div>

    <div class="flex justify-center">
      <svg viewBox="0 0 300 340" width="300" height="340" class="max-w-full">
        <defs>
          <!-- Glow filters per band color -->
          <filter id="glow-theta" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feFlood flood-color="#4FC3F7" flood-opacity="0.6" />
            <feComposite in2="blur" operator="in" />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-alpha" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feFlood flood-color="#4CAF50" flood-opacity="0.6" />
            <feComposite in2="blur" operator="in" />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-beta" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feFlood flood-color="#FFD700" flood-opacity="0.6" />
            <feComposite in2="blur" operator="in" />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-gamma" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feFlood flood-color="#FF69B4" flood-opacity="0.6" />
            <feComposite in2="blur" operator="in" />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-off" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2" />
          </filter>
        </defs>

        <!-- Head outline -->
        <ellipse cx="150" cy="180" rx="130" ry="150" fill="none" stroke="#333" stroke-width="1.5" />

        <!-- Nose -->
        <polygon points="150,22 140,42 160,42" fill="none" stroke="#444" stroke-width="1.2" />

        <!-- Left ear -->
        <path d="M 20,155 Q 5,180 20,205" fill="none" stroke="#444" stroke-width="1.2" />

        <!-- Right ear -->
        <path d="M 280,155 Q 295,180 280,205" fill="none" stroke="#444" stroke-width="1.2" />

        <!-- Midline reference (faint) -->
        <line x1="150" y1="30" x2="150" y2="330" stroke="#1a1a1a" stroke-width="0.5" stroke-dasharray="4,4" />
        <line x1="20" y1="180" x2="280" y2="180" stroke="#1a1a1a" stroke-width="0.5" stroke-dasharray="4,4" />

        <!-- ZUNA electrode placeholders (hidden until active) -->
        <g v-for="e in zunaElectrodes" :key="'zuna-' + e.name"
           :opacity="zunaActive ? 0.7 : 0"
           class="zuna-electrode">
          <circle
            :cx="e.x" :cy="e.y" r="5"
            :fill="zunaActive ? getElectrodeColor(e.name) : '#333'"
            :filter="zunaActive && streaming ? `url(#glow-${getDominantBand(e.name) || 'off'})` : 'none'"
          />
          <text
            :x="e.x" :y="e.y + 18"
            text-anchor="middle"
            fill="#555"
            font-size="8"
            class="electrode-label"
          >{{ e.label }}</text>
        </g>

        <!-- Active electrodes -->
        <g v-for="e in activeElectrodes" :key="e.name">
          <!-- Electrode node -->
          <circle
            :cx="e.x"
            :cy="e.y"
            :r="getElectrodeRadius(e.name)"
            :fill="streaming ? getElectrodeColor(e.name) : '#555'"
            :opacity="streaming ? 0.9 : 0.4"
            :filter="streaming ? `url(#glow-${getDominantBand(e.name) || 'off'})` : 'none'"
            :class="streaming ? 'electrode-pulse' : ''"
            :style="streaming ? { animationDelay: `${Math.random() * 2}s` } : {}"
          />

          <!-- Inner bright core -->
          <circle
            v-if="streaming"
            :cx="e.x"
            :cy="e.y"
            :r="getElectrodeRadius(e.name) * 0.4"
            fill="white"
            opacity="0.3"
          />

          <!-- Label -->
          <text
            :x="e.x"
            :y="e.y + getElectrodeRadius(e.name) + 14"
            text-anchor="middle"
            :fill="streaming ? '#aaa' : '#555'"
            font-size="10"
            class="electrode-label"
          >{{ e.label }}</text>
        </g>

        <!-- Band legend (bottom) -->
        <g transform="translate(40, 320)">
          <circle cx="0" cy="0" r="4" fill="#4FC3F7" />
          <text x="8" y="4" fill="#666" font-size="8" class="electrode-label">Theta</text>

          <circle cx="60" cy="0" r="4" fill="#4CAF50" />
          <text x="68" y="4" fill="#666" font-size="8" class="electrode-label">Alpha</text>

          <circle cx="120" cy="0" r="4" fill="#FFD700" />
          <text x="128" y="4" fill="#666" font-size="8" class="electrode-label">Beta</text>

          <circle cx="175" cy="0" r="4" fill="#FF69B4" />
          <text x="183" y="4" fill="#666" font-size="8" class="electrode-label">Gamma</text>
        </g>
      </svg>
    </div>
  </div>
</template>

<style scoped>
.electrode-label {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  pointer-events: none;
}

.electrode-pulse {
  animation: electrode-breathe 2.5s ease-in-out infinite;
  transform-origin: center;
}

@keyframes electrode-breathe {
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
}

.zuna-electrode {
  transition: opacity 0.8s ease-in-out;
}
</style>
