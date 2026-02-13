<script setup>
/**
 * NeuralView - Neo-Cortex 3D Dashboard
 *
 * The main dashboard view for the Neo-Cortex memory visualization.
 * Dream Engine integrated as a right-panel mode — trigger, monitor,
 * and watch dream cycles transform the memory graph in real-time.
 *
 * "Where memories glow like stars in the vast neural cosmos"
 */

import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useNeoCortexStore } from '@/stores/neocortex'
import { useDreamStore } from '@/stores/dream'
import { useSound } from '@/composables/useSound'
import StatsBar from '@/components/neural/StatsBar.vue'
import MemoryFilters from '@/components/neural/MemoryFilters.vue'
import MemoryDetailPanel from '@/components/neural/MemoryDetailPanel.vue'
import DreamPanel from '@/components/neural/DreamPanel.vue'
import ImportPanel from '@/components/neural/ImportPanel.vue'
import NeuralSpace from '@/components/neural/NeuralSpace.vue'
import MemoryList from '@/components/neural/MemoryList.vue'

const route = useRoute()
const store = useNeoCortexStore()
const dreamStore = useDreamStore()
const { playTone } = useSound()

const neuralSpaceRef = ref(null)
const showFilters = ref(true)
const showDetails = ref(true)

// Mobile responsive
const isMobile = ref(window.innerWidth < 768)

function handleResize() {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) {
    showFilters.value = false
    showDetails.value = false
  }
}

function toggleFilters() {
  showFilters.value = !showFilters.value
  if (isMobile.value && showFilters.value) {
    showDetails.value = false
  }
}

function toggleDetails() {
  showDetails.value = !showDetails.value
  if (isMobile.value && showDetails.value) {
    showFilters.value = false
  }
}

// Handle memory selection (for mobile)
function onMemorySelect(memory) {
  if (isMobile.value && memory) {
    showDetails.value = true
    showFilters.value = false
  }
  // Switch to memory panel when selecting a node
  if (memory) {
    store.setRightPanelMode('memory')
  }
}

// Initialize
onMounted(async () => {
  window.addEventListener('resize', handleResize)
  handleResize()

  // Check for ?panel= query param (e.g. from /dream redirect or /neural?panel=import)
  if (route.query.panel === 'dream') {
    store.setRightPanelMode('dream')
    showDetails.value = true
  } else if (route.query.panel === 'import') {
    store.setRightPanelMode('import')
    showDetails.value = true
  }

  // Play startup sound
  playTone(440, 0.1, 'sine', 0.1)
  setTimeout(() => playTone(554, 0.1, 'sine', 0.1), 100)
  setTimeout(() => playTone(659, 0.15, 'sine', 0.15), 200)

  // Load data (neural + dream in parallel)
  await Promise.all([
    store.initialize(),
    dreamStore.initialize(),
  ])
})

// Watch for filter changes and reload data
watch(() => store.filters, async () => {
  await store.fetchGraphData()
}, { deep: true })

// Auto-switch to Dream panel when a dream cycle starts
watch(() => dreamStore.isRunning, (running) => {
  if (running) {
    store.setRightPanelMode('dream')
    showDetails.value = true
  }
})

// Re-fetch graph data after dream cycle completes (new nodes/links may exist)
watch(() => dreamStore.isRunning, async (running, wasRunning) => {
  if (!running && wasRunning) {
    await store.fetchGraphData()
    await store.fetchStats()
  }
})
</script>

<template>
  <div class="neural-view h-screen flex flex-col bg-apex-dark overflow-hidden pt-16">
    <!-- Stats Bar -->
    <StatsBar />

    <!-- Main Content -->
    <div class="flex-1 flex overflow-hidden relative">
      <!-- Mobile Toggle Buttons -->
      <div class="md:hidden absolute top-2 left-2 z-20 flex gap-2">
        <button
          @click="toggleFilters"
          :class="[
            'p-2 rounded-lg transition-colors',
            showFilters ? 'bg-gold text-black' : 'bg-white/10 text-gray-400'
          ]"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
          </svg>
        </button>
      </div>

      <div class="md:hidden absolute top-2 right-2 z-20">
        <button
          @click="toggleDetails"
          :class="[
            'p-2 rounded-lg transition-colors',
            showDetails ? 'bg-gold text-black' : 'bg-white/10 text-gray-400'
          ]"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>
      </div>

      <!-- Left: Filters Panel -->
      <transition name="slide-left">
        <div
          v-show="showFilters"
          :class="[
            'w-64 flex-shrink-0 z-10',
            isMobile ? 'absolute inset-y-0 left-0 shadow-2xl' : ''
          ]"
        >
          <MemoryFilters />
        </div>
      </transition>

      <!-- Center: Visualization -->
      <div class="flex-1 relative">
        <!-- WebGL fallback notice -->
        <div
          v-if="!store.webglSupported"
          class="absolute top-4 left-1/2 -translate-x-1/2 z-10 bg-gold/10 border border-gold/30 text-gold px-4 py-2 rounded-lg text-sm flex items-center gap-2"
        >
          <span>🖥️</span>
          <span>3D mode unavailable (no GPU) - using list view</span>
        </div>

        <!-- 3D View - Only mount if WebGL is supported -->
        <NeuralSpace
          v-if="store.webglSupported && store.viewMode === '3d'"
          ref="neuralSpaceRef"
          :auto-rotate="store.autoRotate"
          :show-connections="store.showConnections"
          @select="onMemorySelect"
        />

        <!-- List View (fallback when no WebGL or list mode) -->
        <MemoryList v-else />

        <!-- Error display -->
        <div
          v-if="store.error"
          class="absolute bottom-4 left-1/2 -translate-x-1/2 bg-red-500/20 border border-red-500/50 text-red-300 px-4 py-2 rounded-lg text-sm"
        >
          {{ store.error }}
        </div>
      </div>

      <!-- Right: Details / Dream Panel -->
      <transition name="slide-right">
        <div
          v-show="showDetails"
          :class="[
            'w-80 flex-shrink-0 z-10 flex flex-col bg-apex-dark border-l border-apex-border',
            isMobile ? 'absolute inset-y-0 right-0 shadow-2xl' : ''
          ]"
        >
          <!-- Panel mode tabs -->
          <div class="flex items-center border-b border-apex-border shrink-0">
            <button
              @click="store.setRightPanelMode('memory')"
              :class="[
                'flex-1 px-4 py-2.5 text-xs font-medium transition-colors relative',
                store.rightPanelMode === 'memory'
                  ? 'text-white'
                  : 'text-gray-500 hover:text-gray-300'
              ]"
            >
              Memory
              <div
                v-if="store.rightPanelMode === 'memory'"
                class="absolute bottom-0 left-2 right-2 h-0.5 bg-gold rounded-full"
              ></div>
            </button>
            <button
              @click="store.setRightPanelMode('dream')"
              :class="[
                'flex-1 px-4 py-2.5 text-xs font-medium transition-colors relative',
                store.rightPanelMode === 'dream'
                  ? 'text-white'
                  : 'text-gray-500 hover:text-gray-300'
              ]"
            >
              <span class="flex items-center justify-center gap-1.5">
                Dream
                <span
                  v-if="dreamStore.isRunning"
                  class="w-1.5 h-1.5 rounded-full bg-gold animate-pulse"
                ></span>
                <span
                  v-else-if="dreamStore.unconsolidatedEpisodes > 0"
                  class="w-1.5 h-1.5 rounded-full bg-amber-400"
                ></span>
              </span>
              <div
                v-if="store.rightPanelMode === 'dream'"
                class="absolute bottom-0 left-2 right-2 h-0.5 bg-gold rounded-full"
              ></div>
            </button>
            <button
              @click="store.setRightPanelMode('import')"
              :class="[
                'flex-1 px-4 py-2.5 text-xs font-medium transition-colors relative',
                store.rightPanelMode === 'import'
                  ? 'text-white'
                  : 'text-gray-500 hover:text-gray-300'
              ]"
            >
              Import
              <div
                v-if="store.rightPanelMode === 'import'"
                class="absolute bottom-0 left-2 right-2 h-0.5 bg-gold rounded-full"
              ></div>
            </button>
          </div>

          <!-- Panel content -->
          <div class="flex-1 overflow-hidden">
            <MemoryDetailPanel v-if="store.rightPanelMode === 'memory'" />
            <DreamPanel v-else-if="store.rightPanelMode === 'dream'" />
            <ImportPanel v-else-if="store.rightPanelMode === 'import'" />
          </div>
        </div>
      </transition>
    </div>

    <!-- Mobile backdrop -->
    <div
      v-if="isMobile && (showFilters || showDetails)"
      @click="showFilters = false; showDetails = false"
      class="absolute inset-0 bg-black/50 z-5"
    ></div>
  </div>
</template>

<style scoped>
.neural-view {
  background: radial-gradient(ellipse at center, #1a1a2e 0%, #0a0a0f 100%);
}

.slide-left-enter-active,
.slide-left-leave-active,
.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.3s ease;
}

.slide-left-enter-from,
.slide-left-leave-to {
  transform: translateX(-100%);
}

.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
}
</style>
