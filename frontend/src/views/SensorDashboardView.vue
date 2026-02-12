<script setup>
/**
 * SensorHead Dashboard — The Ouroboros View
 *
 * Live sensor data from SensorHead hardware via the Bridge WebSocket tunnel.
 * Direct REST access — zero LLM tokens burned.
 *
 * "The ouroboros sees itself"
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/services/api'

const route = useRoute()
const router = useRouter()
const deviceId = computed(() => route.params.id)

// ─── State ──────────────────────────────────────────────────────────
const status = ref(null)
const loading = ref(true)
const error = ref(null)

// Camera images (base64 JPEG)
const images = ref({ visual: null, night: null, thermal: null })
const capturing = ref({ visual: false, night: false, thermal: false, environment: false, snapshot: false })

// Auto-refresh
const autoRefresh = ref(false)
let refreshInterval = null

// ─── Computed ───────────────────────────────────────────────────────
const online = computed(() => status.value?.online ?? false)
const deviceName = computed(() => status.value?.device_name ?? 'SensorHead')
const telemetry = computed(() => status.value?.telemetry?.readings ?? null)
const telemetryAge = computed(() => {
  const age = status.value?.telemetry?.age_s
  if (age == null) return null
  if (age < 60) return `${Math.round(age)}s ago`
  if (age < 3600) return `${Math.round(age / 60)}m ago`
  return `${Math.round(age / 3600)}h ago`
})
const telemetrySource = computed(() => status.value?.telemetry?.source ?? 'live')
const uptimeText = computed(() => {
  const s = status.value?.uptime_s
  if (s == null) return null
  if (s < 60) return `${Math.round(s)}s`
  if (s < 3600) return `${Math.round(s / 60)}m`
  const h = Math.floor(s / 3600)
  const m = Math.round((s % 3600) / 60)
  return `${h}h ${m}m`
})

// ─── IAQ helpers ────────────────────────────────────────────────────
function iaqLabel(iaq) {
  if (iaq == null) return '—'
  if (iaq <= 50) return 'Excellent'
  if (iaq <= 100) return 'Good'
  if (iaq <= 150) return 'Moderate'
  if (iaq <= 200) return 'Poor'
  if (iaq <= 300) return 'Bad'
  return 'Hazardous'
}

function iaqColor(iaq) {
  if (iaq == null) return 'text-gray-500'
  if (iaq <= 50) return 'text-green-400'
  if (iaq <= 100) return 'text-green-300'
  if (iaq <= 150) return 'text-yellow-400'
  if (iaq <= 200) return 'text-orange-400'
  return 'text-red-400'
}

function iaqBorderColor(iaq) {
  if (iaq == null) return 'border-gray-700'
  if (iaq <= 50) return 'border-green-500/40'
  if (iaq <= 100) return 'border-green-400/30'
  if (iaq <= 150) return 'border-yellow-500/30'
  if (iaq <= 200) return 'border-orange-500/30'
  return 'border-red-500/30'
}

// ─── API calls ──────────────────────────────────────────────────────
async function fetchStatus() {
  try {
    const { data } = await api.get(`/api/v1/devices/${deviceId.value}/sensors`)
    status.value = data
    error.value = null
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to fetch sensor status'
  } finally {
    loading.value = false
  }
}

async function readEnvironment() {
  capturing.value.environment = true
  try {
    const { data } = await api.post(`/api/v1/devices/${deviceId.value}/sensors/environment`)
    // Merge fresh readings into telemetry
    if (status.value) {
      status.value.telemetry = {
        readings: data.data,
        timestamp: Date.now() / 1000,
        age_s: 0,
        source: 'live',
      }
    }
    error.value = null
  } catch (e) {
    error.value = e.response?.data?.detail || 'Environment read failed'
  } finally {
    capturing.value.environment = false
  }
}

async function captureCamera(camera) {
  capturing.value[camera] = true
  try {
    const endpoint = camera === 'thermal'
      ? `/api/v1/devices/${deviceId.value}/sensors/thermal`
      : `/api/v1/devices/${deviceId.value}/sensors/capture/${camera}`
    const { data } = await api.post(endpoint)
    images.value[camera] = data.image_base64
    error.value = null
  } catch (e) {
    error.value = e.response?.data?.detail || `${camera} capture failed`
  } finally {
    capturing.value[camera] = false
  }
}

async function fullSnapshot() {
  capturing.value.snapshot = true
  capturing.value.environment = true
  capturing.value.visual = true
  capturing.value.night = true
  capturing.value.thermal = true
  try {
    const { data } = await api.post(`/api/v1/devices/${deviceId.value}/sensors/snapshot`)
    // Update environment
    if (data.environment && status.value) {
      status.value.telemetry = {
        readings: data.environment,
        timestamp: Date.now() / 1000,
        age_s: 0,
        source: 'live',
      }
    }
    // Update images
    if (data.visual_base64) images.value.visual = data.visual_base64
    if (data.night_base64) images.value.night = data.night_base64
    if (data.thermal_base64) images.value.thermal = data.thermal_base64

    if (data.errors?.length) {
      error.value = `Partial snapshot: ${data.errors.join(', ')}`
    } else {
      error.value = null
    }
  } catch (e) {
    error.value = e.response?.data?.detail || 'Snapshot failed'
  } finally {
    capturing.value.snapshot = false
    capturing.value.environment = false
    capturing.value.visual = false
    capturing.value.night = false
    capturing.value.thermal = false
  }
}

// ─── Auto-refresh ───────────────────────────────────────────────────
function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    refreshInterval = setInterval(() => {
      readEnvironment()
    }, 30000)
  } else {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}

// ─── Lifecycle ──────────────────────────────────────────────────────
onMounted(() => {
  fetchStatus()
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})
</script>

<template>
  <div class="min-h-screen bg-apex-dark pt-20 pb-12 px-4">
    <div class="max-w-5xl mx-auto">

      <!-- Back button -->
      <button
        @click="router.push('/devices')"
        class="text-gray-500 hover:text-gray-300 text-sm mb-4 flex items-center gap-1 transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Devices
      </button>

      <!-- Loading -->
      <div v-if="loading" class="text-center py-20 text-gray-400">
        Connecting to SensorHead...
      </div>

      <template v-else>
        <!-- Header -->
        <div class="flex items-center justify-between mb-6">
          <div class="flex items-center gap-3">
            <span
              class="w-3 h-3 rounded-full"
              :class="online ? 'bg-green-400 animate-pulse' : 'bg-gray-500'"
            ></span>
            <div>
              <h1 class="text-xl font-bold text-white">{{ deviceName }}</h1>
              <p class="text-gray-500 text-xs">
                <template v-if="online">
                  Online
                  <span v-if="uptimeText"> &middot; uptime {{ uptimeText }}</span>
                </template>
                <template v-else>Offline</template>
              </p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <!-- Auto-refresh toggle -->
            <button
              @click="toggleAutoRefresh"
              :class="[
                'text-xs px-3 py-1.5 rounded transition-colors',
                autoRefresh
                  ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                  : 'bg-white/5 text-gray-400 hover:bg-white/10'
              ]"
              :disabled="!online"
            >
              {{ autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh' }}
            </button>

            <!-- Full snapshot -->
            <button
              @click="fullSnapshot"
              :disabled="!online || capturing.snapshot"
              class="px-4 py-1.5 bg-gold text-black rounded text-sm font-medium hover:bg-gold/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {{ capturing.snapshot ? 'Capturing...' : 'Full Snapshot' }}
            </button>
          </div>
        </div>

        <!-- Error -->
        <div
          v-if="error"
          class="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm"
        >
          {{ error }}
        </div>

        <!-- Stale data badge -->
        <div
          v-if="!online && telemetry"
          class="mb-4 p-2 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-yellow-400 text-xs text-center"
        >
          SensorHead offline — showing cached data
          <span v-if="telemetryAge"> ({{ telemetryAge }})</span>
          <span v-if="telemetrySource === 'database'"> from database</span>
        </div>

        <!-- ═══ Environment Gauges ══════════════════════════════════════ -->
        <div class="mb-6">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-sm font-medium text-gray-400 uppercase tracking-wider">Environment</h2>
            <div class="flex items-center gap-2">
              <span v-if="telemetryAge && online" class="text-xs text-gray-600">{{ telemetryAge }}</span>
              <button
                @click="readEnvironment"
                :disabled="!online || capturing.environment"
                class="text-xs px-2 py-1 bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white rounded transition-colors disabled:opacity-40"
              >
                {{ capturing.environment ? 'Reading...' : 'Refresh' }}
              </button>
            </div>
          </div>

          <div v-if="telemetry" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <!-- Temperature -->
            <div class="bg-white/5 border border-apex-border rounded-lg p-3 text-center">
              <div class="text-2xl font-bold text-white">
                {{ telemetry.temperature_c != null ? telemetry.temperature_c.toFixed(1) : '—' }}
              </div>
              <div class="text-xs text-gray-500 mt-1">Temperature &deg;C</div>
            </div>

            <!-- Humidity -->
            <div class="bg-white/5 border border-apex-border rounded-lg p-3 text-center">
              <div class="text-2xl font-bold text-white">
                {{ telemetry.humidity_pct != null ? Math.round(telemetry.humidity_pct) : '—' }}
              </div>
              <div class="text-xs text-gray-500 mt-1">Humidity %</div>
            </div>

            <!-- Pressure -->
            <div class="bg-white/5 border border-apex-border rounded-lg p-3 text-center">
              <div class="text-2xl font-bold text-white">
                {{ telemetry.pressure_hpa != null ? Math.round(telemetry.pressure_hpa) : '—' }}
              </div>
              <div class="text-xs text-gray-500 mt-1">Pressure hPa</div>
            </div>

            <!-- IAQ -->
            <div
              class="bg-white/5 border rounded-lg p-3 text-center"
              :class="iaqBorderColor(telemetry.iaq)"
            >
              <div class="text-2xl font-bold" :class="iaqColor(telemetry.iaq)">
                {{ telemetry.iaq != null ? Math.round(telemetry.iaq) : '—' }}
              </div>
              <div class="text-xs text-gray-500 mt-1">
                IAQ
                <span v-if="telemetry.iaq != null" :class="iaqColor(telemetry.iaq)">
                  &middot; {{ iaqLabel(telemetry.iaq) }}
                </span>
              </div>
            </div>

            <!-- CO2 -->
            <div class="bg-white/5 border border-apex-border rounded-lg p-3 text-center">
              <div class="text-2xl font-bold text-white">
                {{ telemetry.co2_ppm != null ? Math.round(telemetry.co2_ppm) : '—' }}
              </div>
              <div class="text-xs text-gray-500 mt-1">CO2 ppm</div>
            </div>

            <!-- VOC -->
            <div class="bg-white/5 border border-apex-border rounded-lg p-3 text-center">
              <div class="text-2xl font-bold text-white">
                {{ telemetry.voc_ppm != null ? telemetry.voc_ppm.toFixed(2) : '—' }}
              </div>
              <div class="text-xs text-gray-500 mt-1">VOC ppm</div>
            </div>
          </div>

          <!-- No telemetry -->
          <div v-else class="bg-white/5 border border-apex-border rounded-lg p-6 text-center text-gray-500 text-sm">
            No telemetry data available
            <span v-if="online"> — click Refresh to read sensors</span>
          </div>
        </div>

        <!-- ═══ Thermal Summary ═════════════════════════════════════════ -->
        <div
          v-if="telemetry && (telemetry.thermal_min_c != null || telemetry.thermal_max_c != null)"
          class="mb-6"
        >
          <h2 class="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Thermal Summary</h2>
          <div class="grid grid-cols-3 gap-3">
            <div class="bg-white/5 border border-blue-500/20 rounded-lg p-3 text-center">
              <div class="text-xl font-bold text-blue-400">
                {{ telemetry.thermal_min_c != null ? telemetry.thermal_min_c.toFixed(1) : '—' }}
              </div>
              <div class="text-xs text-gray-500 mt-1">Min &deg;C</div>
            </div>
            <div class="bg-white/5 border border-yellow-500/20 rounded-lg p-3 text-center">
              <div class="text-xl font-bold text-yellow-400">
                {{ telemetry.thermal_avg_c != null ? telemetry.thermal_avg_c.toFixed(1) : '—' }}
              </div>
              <div class="text-xs text-gray-500 mt-1">Avg &deg;C</div>
            </div>
            <div class="bg-white/5 border border-red-500/20 rounded-lg p-3 text-center">
              <div class="text-xl font-bold text-red-400">
                {{ telemetry.thermal_max_c != null ? telemetry.thermal_max_c.toFixed(1) : '—' }}
              </div>
              <div class="text-xs text-gray-500 mt-1">Max &deg;C</div>
            </div>
          </div>
        </div>

        <!-- ═══ Camera Panels ═══════════════════════════════════════════ -->
        <div class="mb-6">
          <h2 class="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Cameras</h2>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">

            <!-- Visual Camera -->
            <div class="bg-white/5 border border-apex-border rounded-lg overflow-hidden">
              <div class="p-3 border-b border-white/5 flex items-center justify-between">
                <div>
                  <span class="text-white text-sm font-medium">Visual</span>
                  <span class="text-gray-600 text-xs ml-2">IMX500 AI</span>
                </div>
                <button
                  @click="captureCamera('visual')"
                  :disabled="!online || capturing.visual"
                  class="text-xs px-2 py-1 bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white rounded transition-colors disabled:opacity-40"
                >
                  {{ capturing.visual ? 'Capturing...' : 'Capture' }}
                </button>
              </div>
              <div class="aspect-[4/3] bg-black/40 flex items-center justify-center">
                <img
                  v-if="images.visual"
                  :src="'data:image/jpeg;base64,' + images.visual"
                  class="w-full h-full object-contain"
                  alt="Visual camera"
                />
                <div v-else-if="capturing.visual" class="text-gray-500 text-sm animate-pulse">
                  Capturing...
                </div>
                <div v-else class="text-gray-600 text-sm">
                  No capture yet
                </div>
              </div>
            </div>

            <!-- Night Camera -->
            <div class="bg-white/5 border border-apex-border rounded-lg overflow-hidden">
              <div class="p-3 border-b border-white/5 flex items-center justify-between">
                <div>
                  <span class="text-white text-sm font-medium">Night</span>
                  <span class="text-gray-600 text-xs ml-2">IMX708 NoIR</span>
                </div>
                <button
                  @click="captureCamera('night')"
                  :disabled="!online || capturing.night"
                  class="text-xs px-2 py-1 bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white rounded transition-colors disabled:opacity-40"
                >
                  {{ capturing.night ? 'Capturing...' : 'Capture' }}
                </button>
              </div>
              <div class="aspect-[4/3] bg-black/40 flex items-center justify-center">
                <img
                  v-if="images.night"
                  :src="'data:image/jpeg;base64,' + images.night"
                  class="w-full h-full object-contain"
                  alt="Night camera"
                />
                <div v-else-if="capturing.night" class="text-gray-500 text-sm animate-pulse">
                  Capturing...
                </div>
                <div v-else class="text-gray-600 text-sm">
                  No capture yet
                </div>
              </div>
            </div>

            <!-- Thermal Camera -->
            <div class="bg-white/5 border border-apex-border rounded-lg overflow-hidden">
              <div class="p-3 border-b border-white/5 flex items-center justify-between">
                <div>
                  <span class="text-white text-sm font-medium">Thermal</span>
                  <span class="text-gray-600 text-xs ml-2">MLX90640 IR</span>
                </div>
                <button
                  @click="captureCamera('thermal')"
                  :disabled="!online || capturing.thermal"
                  class="text-xs px-2 py-1 bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white rounded transition-colors disabled:opacity-40"
                >
                  {{ capturing.thermal ? 'Capturing...' : 'Capture' }}
                </button>
              </div>
              <div class="aspect-[4/3] bg-black/40 flex items-center justify-center">
                <img
                  v-if="images.thermal"
                  :src="'data:image/jpeg;base64,' + images.thermal"
                  class="w-full h-full object-contain"
                  alt="Thermal heatmap"
                />
                <div v-else-if="capturing.thermal" class="text-gray-500 text-sm animate-pulse">
                  Capturing...
                </div>
                <div v-else class="text-gray-600 text-sm">
                  No capture yet
                </div>
              </div>
            </div>

          </div>
        </div>

      </template>
    </div>
  </div>
</template>
