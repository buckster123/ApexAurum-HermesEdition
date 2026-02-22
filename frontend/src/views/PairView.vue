<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const SAFE_CHARS = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'

const code = ref('')
const loading = ref(false)
const success = ref(false)
const error = ref('')
const pairedEmail = ref('')
const codeInput = ref(null)

onMounted(() => {
  codeInput.value?.focus()
})

function onCodeInput() {
  // Filter to safe chars, uppercase
  code.value = code.value
    .toUpperCase()
    .split('')
    .filter(c => SAFE_CHARS.includes(c))
    .join('')
    .slice(0, 4)

  // Auto-submit on 4 chars
  if (code.value.length === 4) {
    handleConfirm()
  }
}

async function handleConfirm() {
  if (code.value.length < 4 || loading.value) return
  error.value = ''
  loading.value = true

  try {
    const res = await api.post('/api/v1/auth/device-confirm', {
      device_code: code.value
    })
    success.value = true
    pairedEmail.value = res.data.user_email || ''
  } catch (e) {
    const status = e.response?.status
    const detail = e.response?.data?.detail || ''

    if (status === 404) {
      error.value = 'Code not found. Check the code on your headset and try again.'
    } else if (status === 410) {
      error.value = 'Code expired. Your headset will show a new code shortly.'
    } else if (status === 409) {
      error.value = 'This code has already been used.'
    } else {
      error.value = detail || 'Pairing failed. Please try again.'
    }
    code.value = ''
    codeInput.value?.focus()
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center px-4">
    <div class="w-full max-w-md">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center gap-3 mb-4">
          <span class="text-5xl font-serif font-bold text-gold">Au</span>
        </div>
        <h1 class="text-2xl font-bold">Pair Your Quest</h1>
        <p class="text-gray-400 mt-2">Enter the code shown on your VR headset</p>
      </div>

      <div class="card">
        <!-- Success state -->
        <div v-if="success" class="text-center py-6">
          <div class="text-gold text-6xl mb-4">&#10003;</div>
          <h2 class="text-xl font-bold text-gold mb-2">Device Paired!</h2>
          <p class="text-gray-400">Your Quest is now connected.</p>
          <p v-if="pairedEmail" class="text-gray-500 text-sm mt-1">{{ pairedEmail }}</p>
          <p class="text-gray-500 text-sm mt-4">You can close this page and return to VR.</p>
        </div>

        <!-- Input state -->
        <form v-else @submit.prevent="handleConfirm" class="space-y-6">
          <div v-if="error" class="bg-red-500/10 border border-red-500/50 rounded-lg p-3 text-red-400 text-sm">
            {{ error }}
          </div>

          <div>
            <input
              ref="codeInput"
              v-model="code"
              type="text"
              maxlength="4"
              autocomplete="off"
              autocapitalize="characters"
              spellcheck="false"
              class="input text-center text-4xl font-mono tracking-[0.5em] uppercase"
              placeholder="----"
              :disabled="loading"
              @input="onCodeInput"
            />
          </div>

          <button
            type="submit"
            class="btn-primary w-full"
            :disabled="loading || code.length < 4"
          >
            <span v-if="loading" class="flex items-center justify-center gap-2">
              <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Pairing...
            </span>
            <span v-else>Pair Device</span>
          </button>
        </form>
      </div>

      <p class="text-center text-gray-500 text-xs mt-8">
        The forge binds all realms.
      </p>
    </div>
  </div>
</template>
