<script setup>
/**
 * StatsBar - Top stats bar for Neural Space dashboard
 *
 * Shows memory counts, link counts, and view toggle.
 */

import { computed } from 'vue'
import { useNeoCortexStore, AGENT_COLORS } from '@/stores/neocortex'
import { useDreamStore } from '@/stores/dream'

const emit = defineEmits(['toggleView'])

const store = useNeoCortexStore()
const dreamStore = useDreamStore()

const totalMemories = computed(() => store.memoryCount)
const totalLinks = computed(() => store.linkCount)
const totalEpisodes = computed(() => store.episodeCount)
const activeFilters = computed(() => {
  let count = 0
  if (store.filters.layer) count++
  if (store.filters.visibility) count++
  if (store.filters.agent_id) count++
  if (store.filters.memory_type) count++
  return count
})

function setView(mode) {
  store.setViewMode(mode)
  emit('toggleView', mode)
}

function openDreamPanel() {
  store.setRightPanelMode('dream')
}
</script>

<template>
  <div class="stats-bar h-12 bg-apex-dark/80 backdrop-blur border-b border-apex-border flex items-center justify-between px-4">
    <!-- Left: Title + Stats -->
    <div class="flex items-center gap-6">
      <div class="flex items-center gap-2">
        <span class="text-lg">🧠</span>
        <span class="font-medium text-white">Neural Space</span>
      </div>

      <div class="hidden sm:flex items-center gap-4 text-xs">
        <div class="flex items-center gap-1">
          <span class="text-gray-500">Memories:</span>
          <span class="text-gold font-mono">{{ totalMemories }}</span>
        </div>

        <div class="flex items-center gap-1">
          <span class="text-gray-500">Links:</span>
          <span class="text-blue-400 font-mono">{{ totalLinks }}</span>
        </div>

        <div v-if="totalEpisodes > 0" class="flex items-center gap-1">
          <span class="text-gray-500">Episodes:</span>
          <span class="text-purple-400 font-mono">{{ totalEpisodes }}</span>
        </div>

        <div class="flex items-center gap-1">
          <span class="text-gray-500">Showing:</span>
          <span class="text-white font-mono">{{ store.filteredNodes.length }}</span>
        </div>

        <div v-if="activeFilters > 0" class="flex items-center gap-1">
          <span class="px-1.5 py-0.5 bg-gold/20 text-gold rounded text-xs">
            {{ activeFilters }} filter{{ activeFilters > 1 ? 's' : '' }}
          </span>
        </div>
      </div>
    </div>

    <!-- Center: Dream status + Agent Legend (hidden on mobile) -->
    <div class="hidden md:flex items-center gap-4">
      <!-- Dream indicator -->
      <button
        v-if="!dreamStore.isFreeTier"
        @click="openDreamPanel"
        class="flex items-center gap-1.5 text-xs px-2 py-1 rounded-md transition-colors"
        :class="dreamStore.isRunning
          ? 'bg-gold/15 text-gold border border-gold/30'
          : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'"
      >
        <span v-if="dreamStore.isRunning" class="w-1.5 h-1.5 rounded-full bg-gold animate-pulse"></span>
        <span class="font-serif text-[10px]">Au</span>
        <span class="font-mono">{{ dreamStore.cyclesUsed }}<span class="text-gray-600">/{{ dreamStore.cyclesLimit === null ? '\u221E' : dreamStore.cyclesLimit }}</span></span>
      </button>

      <!-- Divider -->
      <div class="w-px h-4 bg-gray-700"></div>

      <!-- Agent Legend -->
      <div
        v-for="(color, agent) in AGENT_COLORS"
        :key="agent"
        class="flex items-center gap-1"
      >
        <span
          class="w-2 h-2 rounded-full"
          :style="{ backgroundColor: color.hex }"
        ></span>
        <span class="text-xs text-gray-500">{{ agent }}</span>
      </div>
    </div>

    <!-- Right: View Toggle -->
    <div class="flex items-center gap-1 bg-white/5 rounded-lg p-1">
      <button
        @click="setView('3d')"
        :class="[
          'px-3 py-1 text-xs rounded transition-colors',
          store.viewMode === '3d'
            ? 'bg-gold text-black'
            : 'text-gray-400 hover:text-white'
        ]"
      >
        3D
      </button>
      <button
        @click="setView('list')"
        :class="[
          'px-3 py-1 text-xs rounded transition-colors',
          store.viewMode === 'list'
            ? 'bg-gold text-black'
            : 'text-gray-400 hover:text-white'
        ]"
      >
        List
      </button>
    </div>
  </div>
</template>
