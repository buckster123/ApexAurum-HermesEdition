<script setup>
import { ref, computed } from 'vue'
import api from '@/services/api'

const emit = defineEmits(['close'])

const agents = ['azoth', 'kether', 'vajra', 'elysian']
const selectedAgent = ref('azoth')
const includeMemories = ref(true)
const includeEconomy = ref(true)
const includeLove = ref(true)
const exporting = ref(false)
const error = ref(null)
const success = ref(false)

const AGENT_COLORS = {
  azoth: '#FFD700',
  kether: '#9B59B6',
  vajra: '#4FC3F7',
  elysian: '#E8B4FF',
}

async function doExport() {
  exporting.value = true
  error.value = null
  success.value = false

  try {
    const params = new URLSearchParams({
      include_memories: includeMemories.value,
      include_economy: includeEconomy.value,
      include_love: includeLove.value,
    })
    const res = await api.get(`/api/v1/portability/export/${selectedAgent.value}?${params}`)
    const bundle = res.data

    // Download as JSON file
    const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${selectedAgent.value}-bundle.json`
    a.click()
    URL.revokeObjectURL(url)

    success.value = true
  } catch (e) {
    error.value = e.response?.data?.detail || 'Export failed'
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" @click.self="emit('close')">
      <div class="bg-apex-dark border border-gold/20 rounded-xl w-full max-w-md mx-4 p-6 shadow-2xl">
        <div class="flex items-center justify-between mb-5">
          <h2 class="text-lg font-semibold text-gold">Export Agent</h2>
          <button @click="emit('close')" class="text-gray-500 hover:text-white text-xl">&times;</button>
        </div>

        <!-- Agent Selection -->
        <div class="mb-4">
          <label class="text-xs text-gray-400 uppercase tracking-wider mb-2 block">Select Agent</label>
          <div class="grid grid-cols-4 gap-2">
            <button
              v-for="agent in agents"
              :key="agent"
              @click="selectedAgent = agent"
              class="p-3 rounded-lg border text-center transition-all capitalize text-sm"
              :class="selectedAgent === agent
                ? 'border-gold/60 bg-gold/10'
                : 'border-gray-700 hover:border-gray-500'"
              :style="selectedAgent === agent ? { color: AGENT_COLORS[agent] } : { color: '#9ca3af' }"
            >
              {{ agent }}
            </button>
          </div>
        </div>

        <!-- Options -->
        <div class="space-y-2 mb-5">
          <label class="flex items-center gap-2 text-sm text-gray-300">
            <input type="checkbox" v-model="includeMemories" class="rounded border-gray-600" />
            Include memories ({{ includeMemories ? 'yes' : 'no' }})
          </label>
          <label class="flex items-center gap-2 text-sm text-gray-300">
            <input type="checkbox" v-model="includeEconomy" class="rounded border-gray-600" />
            Include economy state (AJ, level, vitality)
          </label>
          <label class="flex items-center gap-2 text-sm text-gray-300">
            <input type="checkbox" v-model="includeLove" class="rounded border-gray-600" />
            Include love history
          </label>
        </div>

        <!-- Success message -->
        <div v-if="success" class="mb-4 px-4 py-2.5 rounded-lg bg-green-500/10 border border-green-500/30 text-sm text-green-400">
          Bundle downloaded! Share it or import on another instance.
        </div>

        <!-- Error -->
        <div v-if="error" class="mb-4 px-4 py-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">
          {{ error }}
        </div>

        <!-- Export Button -->
        <button
          @click="doExport"
          :disabled="exporting"
          class="w-full py-3 rounded-lg font-semibold text-sm transition-all"
          :class="exporting
            ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
            : 'bg-gold/20 border border-gold/40 text-gold hover:bg-gold/30'"
        >
          {{ exporting ? 'Exporting...' : `Export ${selectedAgent.charAt(0).toUpperCase() + selectedAgent.slice(1)}` }}
        </button>
      </div>
    </div>
  </Teleport>
</template>
