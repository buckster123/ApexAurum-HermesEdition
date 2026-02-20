<script setup>
/**
 * BandPowerBars — EEG Frequency Band Visualization
 *
 * Animated horizontal bars for Theta, Alpha, Beta, Gamma power levels.
 * Color-coded to match the BrainMap electrode visualization.
 *
 * "The spectrum of thought made visible"
 */

import { computed } from 'vue'

const props = defineProps({
  bandPowers: { type: Object, default: null },
  // Expected: { theta: 0.35, alpha: 0.45, beta: 0.15, gamma: 0.05 }
  streaming: { type: Boolean, default: false },
})

const BANDS = [
  { key: 'theta', label: 'Theta', range: '4-8 Hz', color: '#4FC3F7', desc: 'Relaxation, meditation' },
  { key: 'alpha', label: 'Alpha', range: '8-13 Hz', color: '#4CAF50', desc: 'Calm focus, flow' },
  { key: 'beta',  label: 'Beta',  range: '13-30 Hz', color: '#FFD700', desc: 'Active thinking' },
  { key: 'gamma', label: 'Gamma', range: '30-45 Hz', color: '#FF69B4', desc: 'Peak awareness' },
]

function bandValue(key) {
  if (!props.bandPowers || !props.streaming) return 0
  return Math.min(1, props.bandPowers[key] || 0)
}

function bandPercent(key) {
  return Math.round(bandValue(key) * 100)
}
</script>

<template>
  <div class="bg-gray-900 border border-gray-800 rounded-lg p-4">
    <h3 class="text-xs font-mono text-gray-400 uppercase tracking-wider mb-3">
      Band Powers
    </h3>

    <div class="space-y-3">
      <div v-for="band in BANDS" :key="band.key" class="group">
        <div class="flex items-center gap-3">
          <!-- Label -->
          <div class="w-20 shrink-0">
            <span class="text-xs font-mono font-medium" :style="{ color: streaming ? band.color : '#6b7280' }">
              {{ band.label }}
            </span>
            <span class="text-[10px] font-mono text-gray-600 block">{{ band.range }}</span>
          </div>

          <!-- Bar track -->
          <div class="flex-1 h-3 bg-white/5 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-700 ease-out"
              :style="{
                width: `${bandPercent(band.key)}%`,
                backgroundColor: streaming ? band.color : '#374151',
                boxShadow: streaming && bandValue(band.key) > 0.1
                  ? `0 0 8px ${band.color}40`
                  : 'none',
              }"
            />
          </div>

          <!-- Value -->
          <span
            class="w-10 text-right text-xs font-mono tabular-nums"
            :style="{ color: streaming ? band.color : '#6b7280' }"
          >
            {{ streaming ? bandPercent(band.key) + '%' : '--' }}
          </span>
        </div>
      </div>
    </div>

    <div v-if="!streaming" class="text-center mt-3">
      <span class="text-[10px] font-mono text-gray-600">Start streaming to see band powers</span>
    </div>
  </div>
</template>
