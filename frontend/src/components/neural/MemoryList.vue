<script setup>
/**
 * MemoryList - List view fallback for Neural Space
 *
 * A table-based list view of memories (2D/List mode).
 * Shows memory type, salience, valence alongside layer and agent.
 */

import { computed } from 'vue'
import { useNeoCortexStore, AGENT_COLORS, MEMORY_TYPES } from '@/stores/neocortex'
import { useDreamStore } from '@/stores/dream'
import { useSound } from '@/composables/useSound'

const store = useNeoCortexStore()
const dreamStore = useDreamStore()
const { playTone } = useSound()

const memories = computed(() => store.filteredNodes)

function selectMemory(memory) {
  store.selectMemory(memory)
}

function toggleQueue(memory, event) {
  event.stopPropagation()
  dreamStore.toggleQueueMembership(memory.id)
  playTone(dreamStore.isInQueue(memory.id) ? 330 : 770, 0.1, 'sine', 0.15)
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function truncate(text, length = 100) {
  if (!text) return ''
  return text.length > length ? text.slice(0, length) + '...' : text
}

function typeColor(type) {
  return MEMORY_TYPES[type]?.color || '#888'
}

function typeLabel(type) {
  return MEMORY_TYPES[type]?.label || type || 'unknown'
}

function valenceIcon(v) {
  if (v === 'positive') return '+'
  if (v === 'negative') return '-'
  if (v === 'mixed') return '~'
  return 'o'
}

function valenceColor(v) {
  if (v === 'positive') return '#66BB6A'
  if (v === 'negative') return '#EF5350'
  if (v === 'mixed') return '#FFA726'
  return '#9E9E9E'
}
</script>

<template>
  <div class="memory-list h-full overflow-auto bg-apex-dark">
    <!-- Empty state -->
    <div
      v-if="memories.length === 0"
      class="h-full flex items-center justify-center"
    >
      <div class="text-center text-gray-500">
        <div class="text-4xl mb-4 opacity-50">🧠</div>
        <p>No memories match your filters</p>
      </div>
    </div>

    <!-- Table -->
    <table v-else class="w-full text-sm">
      <thead class="sticky top-0 bg-apex-dark border-b border-apex-border">
        <tr class="text-left text-xs text-gray-500 uppercase tracking-wider">
          <th class="p-3 w-24">Agent</th>
          <th class="p-3 w-24">Type</th>
          <th class="p-3 w-24">Layer</th>
          <th class="p-3">Content</th>
          <th class="p-3 w-16 text-right">Sal.</th>
          <th class="p-3 w-10 text-center">Val.</th>
          <th class="p-3 w-36">Created</th>
          <th v-if="!dreamStore.isFreeTier" class="p-3 w-10 text-center" title="Athanor Queue"></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="memory in memories"
          :key="memory.id"
          @click="selectMemory(memory)"
          :class="[
            'border-b border-apex-border/50 cursor-pointer transition-colors',
            store.selectedMemory?.id === memory.id
              ? 'bg-gold/10'
              : 'hover:bg-white/5'
          ]"
        >
          <td class="p-3">
            <div class="flex items-center gap-2">
              <span
                class="w-2 h-2 rounded-full"
                :style="{ backgroundColor: AGENT_COLORS[memory.agent_id]?.hex || '#888' }"
              ></span>
              <span class="text-xs text-gray-400">{{ memory.agent_id || 'AZOTH' }}</span>
            </div>
          </td>
          <td class="p-3">
            <span
              class="px-1.5 py-0.5 text-xs rounded text-black font-medium"
              :style="{ backgroundColor: typeColor(memory.memory_type) }"
            >
              {{ typeLabel(memory.memory_type) }}
            </span>
          </td>
          <td class="p-3">
            <span
              class="px-2 py-0.5 text-xs rounded"
              :class="{
                'bg-white/20 text-white': memory.layer === 'cortex',
                'bg-white/15 text-gray-300': memory.layer === 'long_term',
                'bg-white/10 text-gray-400': memory.layer === 'working',
                'bg-white/5 text-gray-500': memory.layer === 'sensory',
              }"
            >
              {{ memory.layer }}
            </span>
          </td>
          <td class="p-3">
            <p class="text-gray-300 line-clamp-2">{{ truncate(memory.content, 150) }}</p>
          </td>
          <td class="p-3 text-right">
            <span class="text-gold font-mono text-xs">
              {{ (memory.salience || 0).toFixed(2) }}
            </span>
          </td>
          <td class="p-3 text-center">
            <span class="font-mono text-xs" :style="{ color: valenceColor(memory.valence) }">
              {{ valenceIcon(memory.valence) }}
            </span>
          </td>
          <td class="p-3 text-xs text-gray-500">
            {{ formatDate(memory.created_at) }}
          </td>
          <td v-if="!dreamStore.isFreeTier" class="p-3 text-center">
            <button
              @click="toggleQueue(memory, $event)"
              class="w-6 h-6 rounded transition-colors flex items-center justify-center text-sm"
              :class="dreamStore.isInQueue(memory.id)
                ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                : 'text-gray-600 hover:text-purple-400 hover:bg-purple-500/10'"
              :title="dreamStore.isInQueue(memory.id) ? 'Remove from Athanor' : 'Mark for Transmutation'"
            >&#x2697;</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
