<script setup>
import { ref } from 'vue'
import api from '@/services/api'

const emit = defineEmits(['close', 'imported'])

const bundle = ref(null)
const fileName = ref('')
const preview = ref(null)
const importing = ref(false)
const validating = ref(false)
const error = ref(null)
const result = ref(null)
const targetAgentId = ref('')

function handleFileSelect(event) {
  const file = event.target.files[0]
  if (!file) return

  fileName.value = file.name
  error.value = null
  preview.value = null
  result.value = null

  const reader = new FileReader()
  reader.onload = async (e) => {
    try {
      bundle.value = JSON.parse(e.target.result)
      await validateBundle()
    } catch (err) {
      error.value = 'Invalid JSON file'
      bundle.value = null
    }
  }
  reader.readAsText(file)
}

async function validateBundle() {
  if (!bundle.value) return
  validating.value = true
  error.value = null

  try {
    const res = await api.post('/api/v1/portability/validate', {
      bundle: bundle.value,
      target_agent_id: targetAgentId.value || null,
    })
    if (res.data.valid) {
      preview.value = res.data.preview
    } else {
      error.value = res.data.errors?.join(', ') || 'Invalid bundle'
    }
  } catch (e) {
    const detail = e.response?.data?.detail
    error.value = typeof detail === 'object' ? detail.errors?.join(', ') : (detail || 'Validation failed')
  } finally {
    validating.value = false
  }
}

async function doImport() {
  if (!bundle.value) return
  importing.value = true
  error.value = null

  try {
    const res = await api.post('/api/v1/portability/import', {
      bundle: bundle.value,
      target_agent_id: targetAgentId.value || null,
    })
    result.value = res.data
    emit('imported', res.data)
  } catch (e) {
    const detail = e.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : (detail?.errors?.join(', ') || 'Import failed')
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" @click.self="emit('close')">
      <div class="bg-apex-dark border border-gold/20 rounded-xl w-full max-w-md mx-4 p-6 shadow-2xl">
        <div class="flex items-center justify-between mb-5">
          <h2 class="text-lg font-semibold text-gold">Import Agent</h2>
          <button @click="emit('close')" class="text-gray-500 hover:text-white text-xl">&times;</button>
        </div>

        <!-- File Upload -->
        <div class="mb-4">
          <label class="block w-full cursor-pointer">
            <div class="border-2 border-dashed border-gray-700 hover:border-gold/40 rounded-lg p-6 text-center transition-colors">
              <div class="text-gray-400 text-sm">
                {{ fileName || 'Drop a bundle JSON file or click to browse' }}
              </div>
            </div>
            <input type="file" accept=".json" @change="handleFileSelect" class="hidden" />
          </label>
        </div>

        <!-- Optional: Override agent ID -->
        <div class="mb-4">
          <label class="text-xs text-gray-400 uppercase tracking-wider mb-1 block">Override Agent ID (optional)</label>
          <input
            v-model="targetAgentId"
            placeholder="e.g., custom_agent_1"
            class="w-full bg-black/30 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-gold/40 focus:outline-none"
          />
        </div>

        <!-- Validation Preview -->
        <div v-if="preview" class="mb-4 p-4 rounded-lg bg-black/30 border border-gray-800">
          <h3 class="text-sm font-medium text-gold mb-2">Bundle Preview</h3>
          <div class="space-y-1 text-xs text-gray-400">
            <div class="flex justify-between">
              <span>Agent</span>
              <span class="text-white capitalize">{{ preview.agent_id }}</span>
            </div>
            <div class="flex justify-between">
              <span>Memories</span>
              <span class="text-white">{{ preview.memory_count }}</span>
            </div>
            <div class="flex justify-between">
              <span>Memory types</span>
              <span class="text-white">{{ preview.memory_types?.join(', ') }}</span>
            </div>
            <div class="flex justify-between">
              <span>AJ Balance</span>
              <span class="text-gold">{{ preview.economy_balance }}</span>
            </div>
            <div class="flex justify-between">
              <span>Level</span>
              <span class="text-white">{{ preview.economy_level }}</span>
            </div>
            <div class="flex justify-between">
              <span>Love entries</span>
              <span class="text-white">{{ preview.love_entries }}</span>
            </div>
            <div v-if="preview.has_system_prompt" class="text-green-400 text-[10px] mt-1">
              Includes system prompt
            </div>
          </div>
        </div>

        <!-- Import Result -->
        <div v-if="result" class="mb-4 p-4 rounded-lg bg-green-500/10 border border-green-500/30">
          <div class="text-sm text-green-400 font-medium mb-1">{{ result.message }}</div>
          <div class="space-y-0.5 text-xs text-gray-400">
            <div>Memories imported: <span class="text-white">{{ result.memories_imported }}</span></div>
            <div v-if="result.memories_skipped">Skipped (duplicates): <span class="text-gray-500">{{ result.memories_skipped }}</span></div>
            <div>Economy: <span class="text-white">{{ result.economy_restored ? 'Restored' : 'N/A' }}</span></div>
            <div>Love: <span class="text-white">{{ result.love_seeded ? 'Seeded' : 'N/A' }}</span></div>
          </div>
        </div>

        <!-- Error -->
        <div v-if="error" class="mb-4 px-4 py-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">
          {{ error }}
        </div>

        <!-- Import Button -->
        <button
          v-if="preview && !result"
          @click="doImport"
          :disabled="importing"
          class="w-full py-3 rounded-lg font-semibold text-sm transition-all"
          :class="importing
            ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
            : 'bg-gold/20 border border-gold/40 text-gold hover:bg-gold/30'"
        >
          {{ importing ? 'Importing...' : `Import ${preview.agent_id}` }}
        </button>

        <!-- Done button -->
        <button
          v-if="result"
          @click="emit('close')"
          class="w-full py-2.5 rounded-lg border border-gray-700 text-gray-300 text-sm hover:border-gray-500 transition-all"
        >
          Done
        </button>
      </div>
    </div>
  </Teleport>
</template>
