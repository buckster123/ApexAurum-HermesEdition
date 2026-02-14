<script setup>
/**
 * SentinelPanel — Autonomous motion detection control center
 *
 * Simple mode: arm/disarm toggle + status + event count badge
 * Advanced mode: thresholds, AI config, schedule, presets
 *
 * "The guardian's command center"
 */

import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import api from '@/services/api'

const props = defineProps({
  deviceId: { type: String, required: true },
  online: { type: Boolean, default: false },
})

const emit = defineEmits(['event'])

// ─── State ──────────────────────────────────────────────────────────
const sentinel = ref(null)        // Full status from device
const loading = ref(false)
const error = ref(null)
const advancedMode = ref(false)
const configDirty = ref(false)

// Editable config (local copy)
const editConfig = ref({
  thermal_threshold_c: 2.0,
  min_changed_pixels: 10,
  scan_interval: 0.5,
  ai_confirm: true,
  ai_confidence: 0.3,
  ai_labels: ['person', 'cat', 'dog', 'bird'],
  cooldown_s: 30,
  max_alerts_per_hour: 20,
  include_snapshot: true,
  snapshot_quality: 60,
  active_start: '',
  active_end: '',
})

// Presets
const presets = ref([])
const savingPreset = ref(false)
const newPresetName = ref('')

// Events
const events = ref([])
const unackedCount = ref(0)
const eventsTotal = ref(0)
const eventsLoading = ref(false)
const eventPage = ref(0)
const EVENT_PAGE_SIZE = 20

// Auto-refresh
let pollInterval = null
const POLL_INTERVAL = 10000 // 10s when armed

// ─── Computed ───────────────────────────────────────────────────────
const armed = computed(() => sentinel.value?.armed ?? false)
const stats = computed(() => sentinel.value?.stats ?? {})
const hasEvents = computed(() => events.value.length > 0)
const hasMore = computed(() => events.value.length < eventsTotal.value)

// ─── API ────────────────────────────────────────────────────────────
async function fetchStatus() {
  if (!props.online) return
  try {
    const { data } = await api.get(`/api/v1/devices/${props.deviceId}/sentinel/status`)
    sentinel.value = data
    if (data.config) {
      // Sync edit config with device state (only if user hasn't made changes)
      if (!configDirty.value) {
        Object.assign(editConfig.value, data.config)
      }
    }
    error.value = null
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to fetch sentinel status'
  }
}

async function toggleArm() {
  loading.value = true
  try {
    const action = armed.value ? 'disarm' : 'arm'
    const { data } = await api.post(`/api/v1/devices/${props.deviceId}/sentinel/${action}`)
    sentinel.value = { ...sentinel.value, ...data }
    error.value = null
    // Start/stop polling based on armed state
    setupPolling()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Arm/disarm failed'
  } finally {
    loading.value = false
  }
}

async function applyConfig() {
  loading.value = true
  try {
    const { data } = await api.post(
      `/api/v1/devices/${props.deviceId}/sentinel/configure`,
      editConfig.value,
    )
    sentinel.value = { ...sentinel.value, ...data }
    configDirty.value = false
    error.value = null
  } catch (e) {
    error.value = e.response?.data?.detail || 'Configure failed'
  } finally {
    loading.value = false
  }
}

async function loadPreset(name) {
  loading.value = true
  try {
    const { data } = await api.post(
      `/api/v1/devices/${props.deviceId}/sentinel/presets/${name}/load`,
    )
    sentinel.value = { ...sentinel.value, ...data }
    if (data.config) Object.assign(editConfig.value, data.config)
    configDirty.value = false
    error.value = null
  } catch (e) {
    error.value = e.response?.data?.detail || 'Preset load failed'
  } finally {
    loading.value = false
  }
}

async function fetchPresets() {
  try {
    const { data } = await api.get(`/api/v1/devices/${props.deviceId}/sentinel/presets`)
    presets.value = data.presets || []
  } catch { /* non-critical */ }
}

async function savePreset() {
  if (!newPresetName.value.trim()) return
  savingPreset.value = true
  try {
    await api.post(`/api/v1/devices/${props.deviceId}/sentinel/presets`, {
      name: newPresetName.value.trim(),
      config: editConfig.value,
    })
    newPresetName.value = ''
    await fetchPresets()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Save preset failed'
  } finally {
    savingPreset.value = false
  }
}

async function fetchEvents(append = false) {
  eventsLoading.value = true
  try {
    const offset = append ? events.value.length : 0
    const { data } = await api.get(
      `/api/v1/devices/${props.deviceId}/sentinel/events`,
      { params: { limit: EVENT_PAGE_SIZE, offset } },
    )
    if (append) {
      events.value = [...events.value, ...(data.events || [])]
    } else {
      events.value = data.events || []
    }
    eventsTotal.value = data.total || 0
    unackedCount.value = data.unacked_count || 0
  } catch { /* non-critical */ }
  finally { eventsLoading.value = false }
}

async function ackEvent(eventId) {
  try {
    await api.post(`/api/v1/devices/${props.deviceId}/sentinel/events/${eventId}/ack`)
    const ev = events.value.find(e => e.id === eventId)
    if (ev) ev.acknowledged = true
    unackedCount.value = Math.max(0, unackedCount.value - 1)
  } catch { /* silent */ }
}

async function ackAll() {
  try {
    await api.post(`/api/v1/devices/${props.deviceId}/sentinel/events/ack-all`)
    events.value.forEach(e => e.acknowledged = true)
    unackedCount.value = 0
  } catch { /* silent */ }
}

// ─── Snapshot viewer ────────────────────────────────────────────────
const viewingSnapshot = ref(null)

async function viewSnapshot(eventId) {
  try {
    const { data } = await api.get(
      `/api/v1/devices/${props.deviceId}/sentinel/events/${eventId}/snapshot`,
    )
    viewingSnapshot.value = data.image_base64
  } catch {
    viewingSnapshot.value = null
  }
}

// ─── Polling ────────────────────────────────────────────────────────
function setupPolling() {
  if (pollInterval) { clearInterval(pollInterval); pollInterval = null }
  if (armed.value && props.online) {
    pollInterval = setInterval(() => {
      fetchStatus()
      fetchEvents()
    }, POLL_INTERVAL)
  }
}

// ─── Helpers ────────────────────────────────────────────────────────
function eventIcon(type) {
  const icons = { motion: '\u26A1', person: '\uD83D\uDEB6', cat: '\uD83D\uDC31', dog: '\uD83D\uDC36', bird: '\uD83D\uDC26' }
  return icons[type] || '\u26A0'
}

function eventColor(type) {
  if (type === 'person') return 'text-red-400'
  if (type === 'motion') return 'text-yellow-400'
  return 'text-blue-400'
}

function timeAgo(isoStr) {
  if (!isoStr) return ''
  const diff = (Date.now() - new Date(isoStr).getTime()) / 1000
  if (diff < 60) return `${Math.round(diff)}s ago`
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`
  return `${Math.round(diff / 86400)}d ago`
}

// Track config changes
watch(editConfig, () => { configDirty.value = true }, { deep: true })

// ─── Lifecycle ──────────────────────────────────────────────────────
onMounted(() => {
  if (props.online) {
    fetchStatus()
    fetchEvents()
    fetchPresets()
    setupPolling()
  }
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

// Refetch when device comes online
watch(() => props.online, (online) => {
  if (online) {
    fetchStatus()
    fetchEvents()
    setupPolling()
  } else {
    if (pollInterval) { clearInterval(pollInterval); pollInterval = null }
  }
})
</script>

<template>
  <div class="sentinel-panel bg-white/5 border border-apex-border rounded-lg overflow-hidden">

    <!-- ═══ Header Bar ═══════════════════════════════════════════════ -->
    <div class="p-3 flex items-center justify-between border-b border-white/5">
      <div class="flex items-center gap-2">
        <!-- Shield icon -->
        <div
          class="w-8 h-8 rounded-full flex items-center justify-center text-lg transition-colors"
          :class="armed ? 'bg-red-500/20 text-red-400' : 'bg-white/5 text-gray-600'"
        >&#x1F6E1;</div>
        <div>
          <div class="text-sm font-medium text-white flex items-center gap-2">
            Sentinel
            <span
              v-if="unackedCount > 0"
              class="text-[10px] px-1.5 py-0.5 bg-red-500/20 border border-red-500/30 text-red-400 rounded-full"
            >{{ unackedCount }}</span>
          </div>
          <div class="text-[10px] text-gray-500">
            <template v-if="armed">
              Armed
              <span v-if="stats.scan_count"> &middot; {{ stats.scan_count }} scans</span>
              <span v-if="stats.alert_count"> &middot; {{ stats.alert_count }} alerts</span>
            </template>
            <template v-else>Disarmed</template>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <!-- Advanced toggle -->
        <button
          @click="advancedMode = !advancedMode"
          class="text-[10px] px-2 py-1 rounded transition-colors"
          :class="advancedMode ? 'bg-white/10 text-gray-300' : 'text-gray-600 hover:text-gray-400'"
        >{{ advancedMode ? 'Simple' : 'Config' }}</button>

        <!-- Arm/Disarm toggle -->
        <button
          @click="toggleArm"
          :disabled="!online || loading"
          class="px-3 py-1.5 rounded text-xs font-medium transition-all disabled:opacity-40"
          :class="armed
            ? 'bg-red-500/20 border border-red-500/30 text-red-400 hover:bg-red-500/30'
            : 'bg-green-500/20 border border-green-500/30 text-green-400 hover:bg-green-500/30'"
        >
          {{ loading ? '...' : armed ? 'Disarm' : 'Arm' }}
        </button>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="px-3 py-2 text-[11px] text-red-400 bg-red-500/5 border-b border-red-500/10">
      {{ error }}
    </div>

    <!-- ═══ Advanced Config Panel ═══════════════════════════════════ -->
    <transition name="config-slide">
      <div v-if="advancedMode" class="border-b border-white/5">

        <!-- Presets row -->
        <div class="px-3 py-2 border-b border-white/5 flex items-center gap-2 flex-wrap">
          <span class="text-[10px] text-gray-500">Presets:</span>
          <button
            v-for="p in presets"
            :key="p.name"
            @click="loadPreset(p.name)"
            :disabled="loading"
            class="text-[10px] px-2 py-0.5 rounded transition-colors"
            :class="sentinel?.active_preset === p.name
              ? 'bg-gold/20 text-gold border border-gold/30'
              : 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10 border border-transparent'"
            :title="p.description || p.name"
          >{{ p.name }}</button>
        </div>

        <!-- Config grid -->
        <div class="p-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
          <!-- Thermal threshold -->
          <div>
            <label class="text-gray-500 block mb-0.5">Thermal threshold</label>
            <div class="flex items-center gap-2">
              <input
                type="range" min="0.5" max="5" step="0.1"
                v-model.number="editConfig.thermal_threshold_c"
                class="config-slider flex-1"
              />
              <span class="text-white font-mono w-10 text-right">{{ editConfig.thermal_threshold_c.toFixed(1) }}&deg;C</span>
            </div>
          </div>

          <!-- Min pixels -->
          <div>
            <label class="text-gray-500 block mb-0.5">Min changed pixels</label>
            <div class="flex items-center gap-2">
              <input
                type="range" min="1" max="50" step="1"
                v-model.number="editConfig.min_changed_pixels"
                class="config-slider flex-1"
              />
              <span class="text-white font-mono w-10 text-right">{{ editConfig.min_changed_pixels }}px</span>
            </div>
          </div>

          <!-- Cooldown -->
          <div>
            <label class="text-gray-500 block mb-0.5">Alert cooldown</label>
            <div class="flex items-center gap-2">
              <input
                type="range" min="5" max="300" step="5"
                v-model.number="editConfig.cooldown_s"
                class="config-slider flex-1"
              />
              <span class="text-white font-mono w-10 text-right">{{ editConfig.cooldown_s }}s</span>
            </div>
          </div>

          <!-- Max alerts/hr -->
          <div>
            <label class="text-gray-500 block mb-0.5">Max alerts/hour</label>
            <div class="flex items-center gap-2">
              <input
                type="range" min="1" max="60" step="1"
                v-model.number="editConfig.max_alerts_per_hour"
                class="config-slider flex-1"
              />
              <span class="text-white font-mono w-10 text-right">{{ editConfig.max_alerts_per_hour }}</span>
            </div>
          </div>

          <!-- AI Confirm -->
          <div class="flex items-center gap-2">
            <label class="text-gray-500">AI confirm</label>
            <button
              @click="editConfig.ai_confirm = !editConfig.ai_confirm"
              class="w-8 h-4 rounded-full transition-colors relative"
              :class="editConfig.ai_confirm ? 'bg-green-500/40' : 'bg-white/10'"
            >
              <div
                class="absolute top-0.5 w-3 h-3 rounded-full transition-transform bg-white"
                :class="editConfig.ai_confirm ? 'translate-x-4' : 'translate-x-0.5'"
              ></div>
            </button>
          </div>

          <!-- AI Confidence -->
          <div v-if="editConfig.ai_confirm">
            <label class="text-gray-500 block mb-0.5">AI confidence</label>
            <div class="flex items-center gap-2">
              <input
                type="range" min="0.1" max="0.9" step="0.05"
                v-model.number="editConfig.ai_confidence"
                class="config-slider flex-1"
              />
              <span class="text-white font-mono w-10 text-right">{{ Math.round(editConfig.ai_confidence * 100) }}%</span>
            </div>
          </div>

          <!-- Include snapshot -->
          <div class="flex items-center gap-2">
            <label class="text-gray-500">Snapshots</label>
            <button
              @click="editConfig.include_snapshot = !editConfig.include_snapshot"
              class="w-8 h-4 rounded-full transition-colors relative"
              :class="editConfig.include_snapshot ? 'bg-green-500/40' : 'bg-white/10'"
            >
              <div
                class="absolute top-0.5 w-3 h-3 rounded-full transition-transform bg-white"
                :class="editConfig.include_snapshot ? 'translate-x-4' : 'translate-x-0.5'"
              ></div>
            </button>
          </div>

          <!-- Schedule -->
          <div class="col-span-2 flex items-center gap-3">
            <label class="text-gray-500">Schedule:</label>
            <input
              v-model="editConfig.active_start"
              type="time"
              class="bg-white/5 border border-apex-border text-white text-xs rounded px-2 py-1"
              placeholder="22:00"
            />
            <span class="text-gray-500">to</span>
            <input
              v-model="editConfig.active_end"
              type="time"
              class="bg-white/5 border border-apex-border text-white text-xs rounded px-2 py-1"
              placeholder="07:00"
            />
            <span v-if="!editConfig.active_start && !editConfig.active_end" class="text-[10px] text-gray-600">Always active</span>
          </div>
        </div>

        <!-- Apply / Save preset -->
        <div class="px-3 py-2 border-t border-white/5 flex items-center gap-2">
          <button
            @click="applyConfig"
            :disabled="!configDirty || loading"
            class="text-xs px-3 py-1.5 bg-gold/20 text-gold rounded hover:bg-gold/30 transition-colors disabled:opacity-30"
          >Apply</button>
          <div class="flex-1"></div>
          <input
            v-model="newPresetName"
            placeholder="Preset name..."
            class="text-xs bg-white/5 border border-apex-border text-gray-300 rounded px-2 py-1 w-32"
          />
          <button
            @click="savePreset"
            :disabled="!newPresetName.trim() || savingPreset"
            class="text-xs px-2 py-1 bg-white/5 text-gray-400 hover:text-white rounded transition-colors disabled:opacity-30"
          >Save</button>
        </div>
      </div>
    </transition>

    <!-- ═══ Event Timeline ═══════════════════════════════════════════ -->
    <div v-if="hasEvents || eventsLoading" class="max-h-80 overflow-y-auto">
      <!-- Timeline header -->
      <div class="px-3 py-2 flex items-center justify-between border-b border-white/5 sticky top-0 bg-apex-dark/95 backdrop-blur z-10">
        <span class="text-[10px] text-gray-500 uppercase tracking-wider">Events</span>
        <div class="flex items-center gap-2">
          <button
            v-if="unackedCount > 0"
            @click="ackAll"
            class="text-[10px] text-gray-500 hover:text-white transition-colors"
          >Ack all</button>
          <button
            @click="fetchEvents()"
            class="text-[10px] text-gray-500 hover:text-white transition-colors"
          >Refresh</button>
        </div>
      </div>

      <!-- Event rows -->
      <div
        v-for="ev in events"
        :key="ev.id"
        class="px-3 py-2 border-b border-white/5 flex items-start gap-2 hover:bg-white/5 transition-colors"
        :class="!ev.acknowledged ? 'bg-white/[0.02]' : ''"
      >
        <!-- Icon -->
        <span class="text-sm mt-0.5" :class="eventColor(ev.type)">{{ eventIcon(ev.type) }}</span>

        <!-- Content -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-xs text-white font-medium capitalize">{{ ev.type }}</span>
            <span v-if="ev.data?.changed_pixels" class="text-[10px] text-gray-500">
              {{ ev.data.changed_pixels }}px &middot; {{ ev.data.thermal_delta }}&deg;C
            </span>
            <span v-if="ev.data?.ai_detections?.length" class="text-[10px] text-blue-400">
              {{ ev.data.ai_detections.length }} AI
            </span>
          </div>
          <!-- AI detection labels -->
          <div v-if="ev.data?.ai_detections?.length" class="flex flex-wrap gap-1 mt-1">
            <span
              v-for="(det, i) in ev.data.ai_detections.slice(0, 5)"
              :key="i"
              class="text-[9px] px-1.5 py-0.5 bg-blue-500/10 border border-blue-500/20 rounded text-blue-400"
            >{{ det.label }} {{ Math.round(det.confidence * 100) }}%</span>
          </div>
          <div class="text-[10px] text-gray-600 mt-0.5">{{ timeAgo(ev.created_at) }}</div>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-1 shrink-0">
          <button
            v-if="ev.has_snapshot"
            @click="viewSnapshot(ev.id)"
            class="text-[10px] px-1.5 py-0.5 text-gray-500 hover:text-white rounded transition-colors"
            title="View snapshot"
          >&#x1F4F7;</button>
          <button
            v-if="!ev.acknowledged"
            @click="ackEvent(ev.id)"
            class="text-[10px] px-1.5 py-0.5 text-gray-500 hover:text-green-400 rounded transition-colors"
            title="Acknowledge"
          >&#x2713;</button>
          <span v-else class="text-[10px] text-gray-700">&#x2713;</span>
        </div>
      </div>

      <!-- Load more -->
      <div v-if="hasMore" class="p-2 text-center">
        <button
          @click="fetchEvents(true)"
          :disabled="eventsLoading"
          class="text-[10px] text-gray-500 hover:text-white transition-colors"
        >{{ eventsLoading ? 'Loading...' : 'Load more' }}</button>
      </div>
    </div>

    <!-- Empty state (only when armed with no events yet) -->
    <div
      v-else-if="armed && !eventsLoading"
      class="px-3 py-4 text-center text-[11px] text-gray-600"
    >
      Sentinel armed &mdash; monitoring for motion...
    </div>

    <!-- Snapshot lightbox -->
    <teleport to="body">
      <div
        v-if="viewingSnapshot"
        class="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-8"
        @click="viewingSnapshot = null"
      >
        <img
          :src="'data:image/jpeg;base64,' + viewingSnapshot"
          class="max-w-full max-h-full rounded-lg shadow-2xl"
          @click.stop
        />
        <button
          @click="viewingSnapshot = null"
          class="absolute top-4 right-4 text-white/50 hover:text-white text-2xl transition-colors"
        >&times;</button>
      </div>
    </teleport>
  </div>
</template>

<style scoped>
.config-slide-enter-active, .config-slide-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.config-slide-enter-from, .config-slide-leave-to {
  max-height: 0;
  opacity: 0;
}
.config-slide-enter-to, .config-slide-leave-from {
  max-height: 500px;
  opacity: 1;
}

.config-slider {
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  outline: none;
}
.config-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #d4af37;
  cursor: pointer;
}
.config-slider::-moz-range-thumb {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #d4af37;
  cursor: pointer;
  border: none;
}
</style>
</script>
