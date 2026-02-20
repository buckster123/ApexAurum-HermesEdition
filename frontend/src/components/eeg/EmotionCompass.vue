<script setup>
/**
 * EmotionCompass — Russell's Circumplex Model
 *
 * 2D emotion space plotting valence (x) against arousal (y).
 * Current state shown as a glowing gold dot with trailing history.
 *
 * Quadrants:
 *   Top-Right:    Excited / Happy
 *   Bottom-Right: Calm / Content
 *   Bottom-Left:  Bored / Sad
 *   Top-Left:     Tense / Anxious
 *
 * "The cartography of feeling"
 */

import { computed } from 'vue'

const props = defineProps({
  valence: { type: Number, default: null },    // -1 to +1
  arousal: { type: Number, default: null },    // 0 to 1 (from API)
  history: { type: Array, default: () => [] }, // [{valence, arousal}]
  streaming: { type: Boolean, default: false },
})

// SVG dimensions
const SIZE = 250
const CENTER = SIZE / 2
const RADIUS = 105

// Map emotion values to SVG coordinates
function mapX(v) { return CENTER + (v || 0) * (RADIUS - 10) }
function mapY(a) {
  // Remap arousal from 0..1 to -1..+1, then invert for SVG (y increases downward)
  const mapped = ((a ?? 0.5) - 0.5) * 2
  return CENTER - mapped * (RADIUS - 10)
}

// Current dot position
const dotX = computed(() => mapX(props.valence))
const dotY = computed(() => mapY(props.arousal))

// Emotion interpretation based on quadrant
const interpretation = computed(() => {
  if (props.valence == null || props.arousal == null) return null
  const v = props.valence
  const a = (props.arousal - 0.5) * 2 // remap
  if (v > 0.15 && a > 0.15) return 'Excited / Happy'
  if (v > 0.15 && a <= 0.15 && a >= -0.15) return 'Pleasant'
  if (v > 0.15 && a < -0.15) return 'Calm / Content'
  if (v < -0.15 && a > 0.15) return 'Tense / Anxious'
  if (v < -0.15 && a <= 0.15 && a >= -0.15) return 'Unpleasant'
  if (v < -0.15 && a < -0.15) return 'Bored / Sad'
  if (a > 0.15) return 'Activated'
  if (a < -0.15) return 'Deactivated'
  return 'Neutral'
})
</script>

<template>
  <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-xs font-mono text-gray-400 uppercase tracking-wider">Emotion Space</h3>
      <span v-if="streaming && interpretation" class="text-xs font-mono text-gold">
        {{ interpretation }}
      </span>
    </div>

    <div class="flex justify-center">
      <svg
        :viewBox="`0 0 ${SIZE} ${SIZE}`"
        :width="SIZE"
        :height="SIZE"
        class="max-w-full"
      >
        <!-- Filters -->
        <defs>
          <filter id="compass-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="trail-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2" />
          </filter>
        </defs>

        <!-- Quadrant shading -->
        <rect :x="CENTER" y="5" :width="RADIUS" :height="RADIUS - 5"
              fill="#4CAF50" opacity="0.03" rx="4" />
        <rect x="5" y="5" :width="RADIUS - 5" :height="RADIUS - 5"
              fill="#EF5350" opacity="0.03" rx="4" />
        <rect x="5" :y="CENTER" :width="RADIUS - 5" :height="RADIUS"
              fill="#607D8B" opacity="0.03" rx="4" />
        <rect :x="CENTER" :y="CENTER" :width="RADIUS" :height="RADIUS"
              fill="#4FC3F7" opacity="0.03" rx="4" />

        <!-- Outer circle -->
        <circle :cx="CENTER" :cy="CENTER" :r="RADIUS"
                fill="none" stroke="#333" stroke-width="1.5" />

        <!-- Crosshair lines -->
        <line :x1="CENTER - RADIUS" :y1="CENTER" :x2="CENTER + RADIUS" :y2="CENTER"
              stroke="#282828" stroke-width="1" />
        <line :x1="CENTER" :y1="CENTER - RADIUS" :x2="CENTER" :y2="CENTER + RADIUS"
              stroke="#282828" stroke-width="1" />

        <!-- Axis tick marks -->
        <line v-for="t in [-0.5, 0.5]" :key="'xtick'+t"
              :x1="mapX(t)" :y1="CENTER - 3" :x2="mapX(t)" :y2="CENTER + 3"
              stroke="#444" stroke-width="1" />
        <line v-for="t in [0.25, 0.75]" :key="'ytick'+t"
              :x1="CENTER - 3" :y1="mapY(t)" :x2="CENTER + 3" :y2="mapY(t)"
              stroke="#444" stroke-width="1" />

        <!-- Axis labels -->
        <text :x="CENTER" :y="20" text-anchor="middle"
              class="compass-label" fill="#666" font-size="10">
          Excited
        </text>
        <text :x="CENTER" :y="SIZE - 8" text-anchor="middle"
              class="compass-label" fill="#666" font-size="10">
          Calm
        </text>
        <text :x="SIZE - 10" :y="CENTER + 4" text-anchor="end"
              class="compass-label" fill="#666" font-size="10">
          Positive
        </text>
        <text x="12" :y="CENTER + 4" text-anchor="start"
              class="compass-label" fill="#666" font-size="10">
          Negative
        </text>

        <!-- Center dot (origin) -->
        <circle :cx="CENTER" :cy="CENTER" r="2" fill="#444" />

        <!-- Trail dots (history) -->
        <circle
          v-for="(point, i) in history"
          :key="'trail-' + i"
          :cx="mapX(point.valence)"
          :cy="mapY(point.arousal)"
          r="3"
          fill="#D4AF37"
          :opacity="0.08 + (i / Math.max(1, history.length)) * 0.35"
          filter="url(#trail-glow)"
        />

        <!-- Current position dot -->
        <template v-if="streaming && valence != null">
          <circle
            :cx="dotX"
            :cy="dotY"
            r="7"
            fill="#FFD700"
            opacity="0.9"
            filter="url(#compass-glow)"
            class="compass-dot"
          />
          <circle
            :cx="dotX"
            :cy="dotY"
            r="3"
            fill="#FFF"
            opacity="0.8"
          />
        </template>

        <!-- Not streaming indicator -->
        <template v-if="!streaming">
          <circle :cx="CENTER" :cy="CENTER" r="5" fill="#555" />
          <text :x="CENTER" :y="CENTER + 25" text-anchor="middle"
                fill="#555" font-size="11" class="compass-label">
            Awaiting data
          </text>
        </template>
      </svg>
    </div>
  </div>
</template>

<style scoped>
.text-gold { color: #FFD700; }
.compass-label { font-family: 'JetBrains Mono', 'Fira Code', monospace; }
.compass-dot {
  transition: cx 0.5s ease-out, cy 0.5s ease-out;
}
</style>
