<script setup>
/**
 * SensorHead Dashboard — The Ouroboros View v3
 *
 * Camera-centric layout with indoor weather bar, thumbnail→big viewer,
 * composite overlay mode, AI vision panel (IMX500 on-chip inference),
 * BSEC2 deep readouts, NoIR FOV alignment, and collapsible sensor sidebar.
 *
 * "The ouroboros opens its third eye"
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

// Camera selection + composite
const selectedCamera = ref('visual')
const compositeOpacity = ref({ visual: 0.5, night: 0.3, thermal: 0.5 })

// Trend / forecast
const trend = ref(null)

// Sidebar
const showSidebar = ref(window.innerWidth >= 1024)

// AI vision
const aiResult = ref(null)
const aiRunning = ref(false)
const aiAction = ref(null)

// Night camera FOV
const nightCropMode = ref(true)

// Advanced sidebar
const showAdvanced = ref(false)

// Auto-refresh
const autoRefreshMode = ref('off')
let envInterval = null
let camInterval = null

// Camera metadata
const CAMERAS = {
  visual: { name: 'Visual', chip: 'IMX500 AI' },
  night: { name: 'Night', chip: 'IMX708 NoIR' },
  thermal: { name: 'Thermal', chip: 'MLX90640 IR' },
  composite: { name: 'Composite', chip: 'Multi-Layer' },
}

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

const bigViewerImage = computed(() => {
  if (selectedCamera.value === 'composite') return null
  return images.value[selectedCamera.value]
})

const isCapturingSelected = computed(() => {
  if (selectedCamera.value === 'composite') {
    return capturing.value.visual || capturing.value.night || capturing.value.thermal
  }
  return capturing.value[selectedCamera.value]
})

// Trend display
const trendLabel = computed(() => {
  const labels = {
    stormy: 'Stormy', rain_likely: 'Rain Likely', stable: 'Stable',
    improving: 'Improving', clear: 'Clear Skies', unknown: 'No Data',
  }
  return labels[trend.value?.trend] || 'No Data'
})

const trendIcon = computed(() => {
  const icons = {
    stormy: '\u2193\u2193', rain_likely: '\u2193', stable: '\u2192',
    improving: '\u2191', clear: '\u2191\u2191', unknown: '\u2014',
  }
  return icons[trend.value?.trend] || '\u2014'
})

const trendColor = computed(() => {
  const colors = {
    stormy: 'text-red-400', rain_likely: 'text-yellow-400', stable: 'text-green-400',
    improving: 'text-blue-400', clear: 'text-blue-300', unknown: 'text-gray-500',
  }
  return colors[trend.value?.trend] || 'text-gray-500'
})

// ─── IAQ helpers ────────────────────────────────────────────────────
function iaqLabel(iaq) {
  if (iaq == null) return '\u2014'
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

function accuracyLabel(level) {
  const labels = ['stabilizing', 'uncertain', 'calibrating', 'calibrated']
  return labels[level] ?? 'unknown'
}

function accuracyColor(level) {
  if (level >= 3) return 'text-green-400'
  if (level >= 2) return 'text-yellow-400'
  if (level >= 1) return 'text-orange-400'
  return 'text-gray-500'
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

async function fetchTrend() {
  try {
    const { data } = await api.get(`/api/v1/devices/${deviceId.value}/sensors/trend`)
    trend.value = data
  } catch {
    // Trend is non-critical
    trend.value = null
  }
}

async function readEnvironment() {
  capturing.value.environment = true
  try {
    const { data } = await api.post(`/api/v1/devices/${deviceId.value}/sensors/environment`)
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
    let endpoint
    if (camera === 'thermal') {
      endpoint = `/api/v1/devices/${deviceId.value}/sensors/thermal`
    } else {
      const cropParam = camera === 'night' && nightCropMode.value ? '?crop=true' : ''
      endpoint = `/api/v1/devices/${deviceId.value}/sensors/capture/${camera}${cropParam}`
    }
    const { data } = await api.post(endpoint)
    images.value[camera] = data.image_base64
    error.value = null
  } catch (e) {
    error.value = e.response?.data?.detail || `${camera} capture failed`
  } finally {
    capturing.value[camera] = false
  }
}

async function runAI(action) {
  aiAction.value = action
  aiRunning.value = true
  aiResult.value = null
  try {
    const { data } = await api.post(`/api/v1/devices/${deviceId.value}/sensors/ai/${action}`)
    aiResult.value = { action, ...data }
    error.value = null
  } catch (e) {
    error.value = e.response?.data?.detail || `AI ${action} failed`
  } finally {
    aiRunning.value = false
  }
}

async function captureComposite() {
  for (const cam of ['visual', 'night', 'thermal']) {
    await captureCamera(cam)
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
    if (data.environment && status.value) {
      status.value.telemetry = {
        readings: data.environment,
        timestamp: Date.now() / 1000,
        age_s: 0,
        source: 'live',
      }
    }
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
function setAutoRefreshMode(mode) {
  if (envInterval) { clearInterval(envInterval); envInterval = null }
  if (camInterval) { clearInterval(camInterval); camInterval = null }
  autoRefreshMode.value = mode

  if (mode === 'sensors' || mode === 'all') {
    envInterval = setInterval(() => {
      readEnvironment()
      fetchTrend()
    }, 30000)
  }

  if (mode === 'all') {
    camInterval = setInterval(async () => {
      for (const cam of ['visual', 'night', 'thermal']) {
        await captureCamera(cam)
      }
    }, 60000)
  }
}

// ─── Lifecycle ──────────────────────────────────────────────────────
onMounted(() => {
  fetchStatus()
  fetchTrend()
})

onUnmounted(() => {
  if (envInterval) clearInterval(envInterval)
  if (camInterval) clearInterval(camInterval)
})
</script>

<template>
  <div class="min-h-screen bg-apex-dark pt-20 pb-12 px-4">
    <div class="max-w-7xl mx-auto">

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

          <button
            @click="fullSnapshot"
            :disabled="!online || capturing.snapshot"
            class="px-4 py-1.5 bg-gold text-black rounded text-sm font-medium hover:bg-gold/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {{ capturing.snapshot ? 'Capturing...' : 'Full Snapshot' }}
          </button>
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
          SensorHead offline &mdash; showing cached data
          <span v-if="telemetryAge"> ({{ telemetryAge }})</span>
          <span v-if="telemetrySource === 'database'"> from database</span>
        </div>

        <!-- ═══ Indoor Weather Bar ═══════════════════════════════════════ -->
        <div class="grid grid-cols-3 gap-3 mb-4">
          <!-- Temperature -->
          <div class="bg-white/5 border border-apex-border rounded-lg p-4">
            <div class="text-3xl font-bold text-white">
              {{ telemetry?.temperature_c != null ? telemetry.temperature_c.toFixed(1) : '--' }}<span class="text-lg text-gray-500">&deg;C</span>
            </div>
            <div class="text-xs text-gray-500 mt-1">Temperature</div>
          </div>

          <!-- Humidity -->
          <div class="bg-white/5 border border-apex-border rounded-lg p-4">
            <div class="text-3xl font-bold text-white">
              {{ telemetry?.humidity_pct != null ? Math.round(telemetry.humidity_pct) : '--' }}<span class="text-lg text-gray-500">%</span>
            </div>
            <div class="text-xs text-gray-500 mt-1">Humidity</div>
          </div>

          <!-- Forecast -->
          <div class="bg-white/5 border border-apex-border rounded-lg p-4">
            <div class="text-2xl font-bold" :class="trendColor">
              {{ trendIcon }} {{ trendLabel }}
            </div>
            <div class="text-xs text-gray-500 mt-1 truncate">
              {{ trend?.comfort_detail || 'Awaiting sensor data' }}
            </div>
          </div>
        </div>

        <!-- ═══ Main Content Area (viewer + sidebar) ═════════════════════ -->
        <div class="flex gap-4">

          <!-- LEFT: Cameras -->
          <div class="flex-1 min-w-0">

            <!-- Camera Thumbnails (4-column) -->
            <div class="grid grid-cols-4 gap-2 mb-4">
              <button
                v-for="cam in ['visual', 'night', 'thermal', 'composite']"
                :key="cam"
                @click="selectedCamera = cam"
                :class="[
                  'relative bg-white/5 border rounded-lg overflow-hidden transition-all text-left',
                  selectedCamera === cam
                    ? 'border-gold ring-1 ring-gold/40'
                    : 'border-apex-border hover:border-white/20'
                ]"
              >
                <!-- Thumbnail image -->
                <div class="aspect-[4/3] bg-black/40 flex items-center justify-center relative">
                  <template v-if="cam !== 'composite'">
                    <img
                      v-if="images[cam]"
                      :src="'data:image/jpeg;base64,' + images[cam]"
                      class="w-full h-full object-contain"
                      :alt="CAMERAS[cam].name"
                    />
                    <span v-else class="text-gray-600 text-[10px]">No image</span>
                  </template>
                  <template v-else>
                    <!-- Composite mini-preview -->
                    <div v-if="images.visual || images.night || images.thermal" class="absolute inset-0">
                      <img v-if="images.visual" :src="'data:image/jpeg;base64,' + images.visual"
                        class="absolute inset-0 w-full h-full object-contain" style="opacity: 0.4" />
                      <img v-if="images.night" :src="'data:image/jpeg;base64,' + images.night"
                        class="absolute inset-0 w-full h-full object-contain" style="opacity: 0.3" />
                      <img v-if="images.thermal" :src="'data:image/jpeg;base64,' + images.thermal"
                        class="absolute inset-0 w-full h-full object-contain" style="opacity: 0.3" />
                    </div>
                    <span v-else class="text-gray-600 text-[10px] z-10">Layers</span>
                  </template>
                </div>
                <!-- Label -->
                <div class="p-1.5 flex items-center justify-between">
                  <span class="text-[11px] text-white truncate">{{ CAMERAS[cam].name }}</span>
                  <button
                    v-if="cam !== 'composite'"
                    @click.stop="captureCamera(cam)"
                    :disabled="!online || capturing[cam]"
                    class="text-[10px] px-1.5 py-0.5 bg-white/10 hover:bg-white/20 rounded text-gray-400 disabled:opacity-30"
                  >
                    {{ capturing[cam] ? '...' : 'Snap' }}
                  </button>
                </div>
              </button>
            </div>

            <!-- ═══ Big Viewer ═══════════════════════════════════════════ -->
            <div class="bg-white/5 border border-apex-border rounded-lg overflow-hidden mb-4">
              <!-- Viewer header -->
              <div class="p-3 border-b border-white/5 flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <span class="text-white font-medium">{{ CAMERAS[selectedCamera].name }}</span>
                  <span class="text-gray-600 text-xs">{{ CAMERAS[selectedCamera].chip }}</span>
                  <!-- Night camera FOV toggle -->
                  <div v-if="selectedCamera === 'night'" class="flex items-center gap-1 text-[10px]">
                    <button
                      @click="nightCropMode = false"
                      :class="!nightCropMode ? 'text-gold bg-gold/15' : 'text-gray-500 hover:text-gray-300'"
                      class="px-1.5 py-0.5 rounded transition-colors"
                    >Wide</button>
                    <button
                      @click="nightCropMode = true"
                      :class="nightCropMode ? 'text-gold bg-gold/15' : 'text-gray-500 hover:text-gray-300'"
                      class="px-1.5 py-0.5 rounded transition-colors"
                    >Standard</button>
                  </div>
                </div>
                <button
                  @click="selectedCamera === 'composite' ? captureComposite() : captureCamera(selectedCamera)"
                  :disabled="!online || isCapturingSelected"
                  class="text-xs px-3 py-1 bg-gold/20 text-gold hover:bg-gold/30 rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {{ isCapturingSelected ? 'Capturing...' : 'Capture' }}
                </button>
              </div>

              <!-- AI toolbar (visual camera only) -->
              <div
                v-if="selectedCamera === 'visual'"
                class="px-3 py-2 border-b border-white/5 flex items-center gap-2"
              >
                <span class="text-[10px] text-gray-600 mr-1">AI:</span>
                <button
                  v-for="ai in [
                    { key: 'detect', label: 'Detect Objects' },
                    { key: 'classify', label: 'Classify Scene' },
                    { key: 'pose', label: 'Estimate Pose' },
                  ]"
                  :key="ai.key"
                  @click="runAI(ai.key)"
                  :disabled="!online || aiRunning"
                  class="text-[11px] px-2.5 py-1 border rounded transition-colors disabled:opacity-30"
                  :class="aiAction === ai.key && aiRunning
                    ? 'border-gold/50 text-gold bg-gold/10 animate-pulse'
                    : 'border-white/10 text-gray-400 hover:text-gold hover:border-gold/30 hover:bg-gold/5'"
                >
                  {{ aiAction === ai.key && aiRunning ? 'Running...' : ai.label }}
                </button>
                <span v-if="!aiResult && !aiRunning" class="text-[9px] text-gray-600 ml-auto" title="First run loads model (~5s)">On-chip ISP</span>
              </div>

              <!-- Image area -->
              <div class="aspect-[4/3] bg-black/60 relative flex items-center justify-center">
                <!-- Normal camera view -->
                <template v-if="selectedCamera !== 'composite'">
                  <img
                    v-if="bigViewerImage"
                    :src="'data:image/jpeg;base64,' + bigViewerImage"
                    class="w-full h-full object-contain"
                    :alt="CAMERAS[selectedCamera].name"
                  />
                  <div v-else-if="isCapturingSelected" class="text-gray-500 text-sm animate-pulse">
                    Capturing...
                  </div>
                  <div v-else class="text-gray-600 text-sm">
                    Click Capture to take a photo
                  </div>
                </template>

                <!-- Composite overlay view -->
                <template v-else>
                  <div
                    v-if="images.visual || images.night || images.thermal"
                    class="absolute inset-0"
                  >
                    <img
                      v-if="images.visual"
                      :src="'data:image/jpeg;base64,' + images.visual"
                      class="absolute inset-0 w-full h-full object-contain"
                      :style="{ opacity: compositeOpacity.visual }"
                    />
                    <img
                      v-if="images.night"
                      :src="'data:image/jpeg;base64,' + images.night"
                      class="absolute inset-0 w-full h-full object-contain"
                      :style="{ opacity: compositeOpacity.night }"
                    />
                    <img
                      v-if="images.thermal"
                      :src="'data:image/jpeg;base64,' + images.thermal"
                      class="absolute inset-0 w-full h-full object-contain"
                      :style="{ opacity: compositeOpacity.thermal }"
                    />
                  </div>
                  <div v-else class="text-gray-600 text-sm z-10">
                    Capture cameras first to build a composite
                  </div>
                </template>
              </div>

              <!-- AI Results panel -->
              <div
                v-if="aiResult && selectedCamera === 'visual'"
                class="p-3 border-t border-white/5"
              >
                <div class="flex items-center justify-between mb-2">
                  <span class="text-xs text-gray-400">
                    {{ aiResult.model }}
                    <span v-if="aiResult.count != null" class="text-gold ml-1">{{ aiResult.count }} detected</span>
                    <span v-if="aiResult.people_detected != null" class="text-gold ml-1">{{ aiResult.people_detected }} person(s)</span>
                  </span>
                  <span v-if="aiResult.performance" class="text-[10px] text-gray-600">
                    DNN: {{ aiResult.performance.dnn_ms }}ms | DSP: {{ aiResult.performance.dsp_ms }}ms
                  </span>
                </div>

                <!-- Detection results -->
                <div v-if="aiResult.action === 'detect' && aiResult.detections?.length" class="flex flex-wrap gap-1.5">
                  <span
                    v-for="(det, i) in aiResult.detections"
                    :key="i"
                    class="text-[11px] px-2 py-0.5 bg-gold/10 border border-gold/20 rounded text-gold"
                  >
                    {{ det.label }} {{ Math.round(det.confidence * 100) }}%
                  </span>
                </div>
                <div v-else-if="aiResult.action === 'detect'" class="text-xs text-gray-500">No objects detected</div>

                <!-- Classification results -->
                <div v-if="aiResult.action === 'classify' && aiResult.predictions?.length" class="space-y-1">
                  <div v-for="(pred, i) in aiResult.predictions" :key="i" class="flex items-center gap-2">
                    <span class="text-[11px] text-gray-300 w-28 truncate">{{ pred.label }}</span>
                    <div class="flex-1 h-1.5 bg-white/5 rounded overflow-hidden">
                      <div class="h-full bg-gold rounded" :style="{ width: (pred.confidence * 100) + '%' }"></div>
                    </div>
                    <span class="text-[10px] text-gray-500 w-10 text-right font-mono">{{ Math.round(pred.confidence * 100) }}%</span>
                  </div>
                </div>

                <!-- Pose results -->
                <div v-if="aiResult.action === 'pose'" class="text-xs">
                  <div v-if="aiResult.poses?.length" class="text-gray-300">
                    {{ aiResult.poses[0].keypoints_detected }}/{{ aiResult.poses[0].total_keypoints }} keypoints detected
                  </div>
                  <div v-else class="text-gray-500">No pose detected</div>
                </div>
              </div>

              <!-- Composite sliders -->
              <div
                v-if="selectedCamera === 'composite'"
                class="p-3 border-t border-white/5 grid grid-cols-3 gap-4"
              >
                <div v-for="cam in ['visual', 'night', 'thermal']" :key="cam">
                  <label class="text-[11px] text-gray-400 block mb-1">
                    {{ CAMERAS[cam].name }}: {{ Math.round(compositeOpacity[cam] * 100) }}%
                  </label>
                  <input
                    type="range"
                    min="0" max="1" step="0.05"
                    v-model.number="compositeOpacity[cam]"
                    class="composite-slider w-full h-1"
                  />
                </div>
              </div>
            </div>

            <!-- Auto-refresh control -->
            <div class="flex items-center gap-3 mb-4">
              <label class="text-xs text-gray-500">Auto-refresh:</label>
              <select
                :value="autoRefreshMode"
                @change="setAutoRefreshMode($event.target.value)"
                :disabled="!online"
                class="text-xs bg-white/5 border border-apex-border text-gray-300 rounded px-2 py-1.5 disabled:opacity-40"
              >
                <option value="off">Off</option>
                <option value="sensors">Sensors only (30s)</option>
                <option value="all">Sensors + Cameras (30s / 60s)</option>
              </select>
              <span
                v-if="autoRefreshMode !== 'off'"
                class="w-2 h-2 rounded-full bg-green-400 animate-pulse"
              ></span>
              <span v-if="telemetryAge && online" class="text-[10px] text-gray-600 ml-auto">
                {{ telemetryAge }}
              </span>
            </div>

          </div>

          <!-- RIGHT: Collapsible Sidebar -->
          <transition name="slide">
            <div v-if="showSidebar" class="w-72 shrink-0">
              <div class="bg-white/5 border border-apex-border rounded-lg p-4 sticky top-24 space-y-4">
                <!-- Header -->
                <div class="flex items-center justify-between">
                  <h3 class="text-xs font-medium text-gray-400 uppercase tracking-wider">Sensor Readouts</h3>
                  <button @click="showSidebar = false" class="text-gray-600 hover:text-gray-400 text-sm transition-colors">
                    &raquo;
                  </button>
                </div>

                <!-- Environment gauges -->
                <div v-if="telemetry" class="space-y-2">
                  <!-- Temperature -->
                  <div class="flex items-center justify-between px-2 py-1.5 bg-black/20 rounded">
                    <span class="text-xs text-gray-500">Temp</span>
                    <span class="text-sm text-white font-mono">
                      {{ telemetry.temperature_c != null ? telemetry.temperature_c.toFixed(1) + '°C' : '--' }}
                    </span>
                  </div>
                  <!-- Humidity -->
                  <div class="flex items-center justify-between px-2 py-1.5 bg-black/20 rounded">
                    <span class="text-xs text-gray-500">Humidity</span>
                    <span class="text-sm text-white font-mono">
                      {{ telemetry.humidity_pct != null ? Math.round(telemetry.humidity_pct) + '%' : '--' }}
                    </span>
                  </div>
                  <!-- Pressure -->
                  <div class="flex items-center justify-between px-2 py-1.5 bg-black/20 rounded">
                    <span class="text-xs text-gray-500">Pressure</span>
                    <span class="text-sm text-white font-mono">
                      {{ telemetry.pressure_hpa != null ? Math.round(telemetry.pressure_hpa) + ' hPa' : '--' }}
                    </span>
                  </div>
                  <!-- IAQ -->
                  <div
                    class="flex items-center justify-between px-2 py-1.5 rounded border"
                    :class="[iaqBorderColor(telemetry.iaq)]"
                    style="background: rgba(0,0,0,0.2)"
                  >
                    <span class="text-xs text-gray-500">IAQ</span>
                    <span class="text-sm font-mono" :class="iaqColor(telemetry.iaq)">
                      {{ telemetry.iaq != null ? Math.round(telemetry.iaq) : '--' }}
                      <span class="text-[10px] ml-1">{{ iaqLabel(telemetry.iaq) }}</span>
                    </span>
                  </div>
                  <!-- CO2 -->
                  <div class="flex items-center justify-between px-2 py-1.5 bg-black/20 rounded">
                    <span class="text-xs text-gray-500">CO2</span>
                    <span class="text-sm text-white font-mono">
                      {{ telemetry.co2_ppm != null ? Math.round(telemetry.co2_ppm) + ' ppm' : '--' }}
                    </span>
                  </div>
                  <!-- VOC -->
                  <div class="flex items-center justify-between px-2 py-1.5 bg-black/20 rounded">
                    <span class="text-xs text-gray-500">VOC</span>
                    <span class="text-sm text-white font-mono">
                      {{ telemetry.voc_ppm != null ? telemetry.voc_ppm.toFixed(3) + ' ppm' : '--' }}
                    </span>
                  </div>

                  <!-- BSEC2 Advanced (collapsible) -->
                  <button
                    @click="showAdvanced = !showAdvanced"
                    class="w-full text-[10px] text-gray-500 hover:text-gray-300 flex items-center justify-between pt-2 transition-colors"
                  >
                    <span class="uppercase tracking-wider">Advanced</span>
                    <span>{{ showAdvanced ? '\u25B2' : '\u25BC' }}</span>
                  </button>

                  <template v-if="showAdvanced">
                    <!-- IAQ Accuracy -->
                    <div class="flex items-center justify-between px-2 py-1.5 bg-black/20 rounded">
                      <span class="text-xs text-gray-500">IAQ Acc.</span>
                      <div class="flex items-center gap-1.5">
                        <div class="flex gap-0.5">
                          <div v-for="i in 4" :key="i" class="w-2.5 h-1.5 rounded-sm" :class="(telemetry.iaq_accuracy ?? 0) >= i ? 'bg-green-400' : 'bg-white/10'"></div>
                        </div>
                        <span class="text-[10px] font-mono" :class="accuracyColor(telemetry.iaq_accuracy)">
                          {{ accuracyLabel(telemetry.iaq_accuracy) }}
                        </span>
                      </div>
                    </div>
                    <!-- CO2 Accuracy -->
                    <div v-if="telemetry.co2_accuracy != null" class="flex items-center justify-between px-2 py-1.5 bg-black/20 rounded">
                      <span class="text-xs text-gray-500">CO2 Acc.</span>
                      <div class="flex items-center gap-1.5">
                        <div class="flex gap-0.5">
                          <div v-for="i in 4" :key="i" class="w-2.5 h-1.5 rounded-sm" :class="telemetry.co2_accuracy >= i ? 'bg-green-400' : 'bg-white/10'"></div>
                        </div>
                        <span class="text-[10px] font-mono" :class="accuracyColor(telemetry.co2_accuracy)">
                          {{ accuracyLabel(telemetry.co2_accuracy) }}
                        </span>
                      </div>
                    </div>
                    <!-- VOC Accuracy -->
                    <div v-if="telemetry.breath_voc_accuracy != null" class="flex items-center justify-between px-2 py-1.5 bg-black/20 rounded">
                      <span class="text-xs text-gray-500">VOC Acc.</span>
                      <div class="flex items-center gap-1.5">
                        <div class="flex gap-0.5">
                          <div v-for="i in 4" :key="i" class="w-2.5 h-1.5 rounded-sm" :class="telemetry.breath_voc_accuracy >= i ? 'bg-green-400' : 'bg-white/10'"></div>
                        </div>
                        <span class="text-[10px] font-mono" :class="accuracyColor(telemetry.breath_voc_accuracy)">
                          {{ accuracyLabel(telemetry.breath_voc_accuracy) }}
                        </span>
                      </div>
                    </div>
                    <!-- Gas Resistance -->
                    <div v-if="telemetry.raw_gas_resistance_ohm != null" class="flex items-center justify-between px-2 py-1.5 bg-black/20 rounded">
                      <span class="text-xs text-gray-500">Gas Res.</span>
                      <span class="text-sm text-white font-mono">
                        {{ (telemetry.raw_gas_resistance_ohm / 1000).toFixed(1) }} k&Omega;
                      </span>
                    </div>
                    <!-- Gas Classification -->
                    <div v-if="telemetry.gas_percentage != null" class="flex items-center justify-between px-2 py-1.5 bg-black/20 rounded">
                      <span class="text-xs text-gray-500">Gas Class.</span>
                      <span class="text-sm text-white font-mono">{{ telemetry.gas_percentage.toFixed(1) }}%</span>
                    </div>
                    <!-- Air Quality Description -->
                    <div v-if="telemetry.air_quality_description" class="px-2 py-1.5 bg-black/20 rounded">
                      <span class="text-xs text-gray-500">Air Quality</span>
                      <div class="text-[11px] text-gray-300 mt-0.5 italic">{{ telemetry.air_quality_description }}</div>
                    </div>
                    <!-- Raw vs Compensated -->
                    <div v-if="telemetry.raw_temperature_c != null" class="flex items-center justify-between px-2 py-1.5 bg-black/20 rounded">
                      <span class="text-xs text-gray-500">Raw Temp</span>
                      <span class="text-sm text-gray-400 font-mono">{{ telemetry.raw_temperature_c.toFixed(1) }}&deg;C</span>
                    </div>
                    <div v-if="telemetry.raw_humidity_pct != null" class="flex items-center justify-between px-2 py-1.5 bg-black/20 rounded">
                      <span class="text-xs text-gray-500">Raw Humid</span>
                      <span class="text-sm text-gray-400 font-mono">{{ Math.round(telemetry.raw_humidity_pct) }}%</span>
                    </div>
                    <!-- BSEC Version -->
                    <div v-if="telemetry.bsec_version" class="flex items-center justify-between px-2 py-1.5 bg-black/20 rounded">
                      <span class="text-xs text-gray-500">BSEC</span>
                      <span class="text-[10px] text-gray-500 font-mono">v{{ telemetry.bsec_version }}</span>
                    </div>
                  </template>
                </div>
                <div v-else class="text-xs text-gray-600 text-center py-4">
                  No sensor data
                </div>

                <!-- Thermal summary -->
                <div v-if="telemetry && (telemetry.thermal_min_c != null || telemetry.thermal_max_c != null)">
                  <h4 class="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Thermal</h4>
                  <div class="grid grid-cols-3 gap-1.5 text-center text-xs">
                    <div class="bg-black/20 rounded p-1.5">
                      <div class="text-blue-400 font-mono">{{ telemetry.thermal_min_c?.toFixed(1) ?? '--' }}</div>
                      <div class="text-[9px] text-gray-600">Min</div>
                    </div>
                    <div class="bg-black/20 rounded p-1.5">
                      <div class="text-yellow-400 font-mono">{{ telemetry.thermal_avg_c?.toFixed(1) ?? '--' }}</div>
                      <div class="text-[9px] text-gray-600">Avg</div>
                    </div>
                    <div class="bg-black/20 rounded p-1.5">
                      <div class="text-red-400 font-mono">{{ telemetry.thermal_max_c?.toFixed(1) ?? '--' }}</div>
                      <div class="text-[9px] text-gray-600">Max</div>
                    </div>
                  </div>
                </div>

                <!-- Refresh button -->
                <button
                  @click="readEnvironment(); fetchTrend()"
                  :disabled="!online || capturing.environment"
                  class="w-full text-xs px-3 py-2 bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white rounded transition-colors disabled:opacity-40"
                >
                  {{ capturing.environment ? 'Reading...' : 'Refresh Sensors' }}
                </button>
              </div>
            </div>
          </transition>

        </div>

        <!-- Sidebar toggle (when collapsed) -->
        <button
          v-if="!showSidebar"
          @click="showSidebar = true"
          class="fixed right-2 top-1/2 -translate-y-1/2 bg-white/5 border border-apex-border rounded-l-lg px-1.5 py-4 text-gray-500 hover:text-white hover:bg-white/10 transition-colors z-10"
          title="Show sensor panel"
        >
          &laquo;
        </button>

      </template>
    </div>
  </div>
</template>

<style scoped>
.slide-enter-active, .slide-leave-active {
  transition: all 0.2s ease;
}
.slide-enter-from, .slide-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.composite-slider {
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  outline: none;
}
.composite-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #d4af37;
  cursor: pointer;
}
.composite-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #d4af37;
  cursor: pointer;
  border: none;
}
</style>
