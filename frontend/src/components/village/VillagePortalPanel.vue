<script setup>
/**
 * VillagePortalPanel — Multiverse Portal System UI
 *
 * Slides in from the right when the portal arch is clicked.
 * Three tabs: My Portals, Discover Villages, Requests.
 *
 * "Step through the arch and into another world"
 */

import { ref, computed, watch, onMounted } from 'vue'
import api from '@/services/api'

const props = defineProps({
  show: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'visit-village', 'enter-portal'])

const activeTab = ref('portals')
const loading = ref(false)
const error = ref(null)

// Data
const portals = ref([])
const directory = ref([])
const myProfile = ref(null)
const searchQuery = ref('')

// ── Data Fetching ──────────────────────────

async function loadPortals() {
  try {
    const { data } = await api.get('/api/v1/multiverse/portals')
    portals.value = data.portals || []
  } catch (e) {
    console.warn('[Portal] Failed to load portals:', e)
  }
}

async function loadDirectory() {
  try {
    loading.value = true
    const params = {}
    if (searchQuery.value) params.search = searchQuery.value
    const { data } = await api.get('/api/v1/multiverse/directory', { params })
    directory.value = data.villages || []
  } catch (e) {
    console.warn('[Portal] Failed to load directory:', e)
  } finally {
    loading.value = false
  }
}

async function loadProfile() {
  try {
    const { data } = await api.get('/api/v1/multiverse/profile')
    myProfile.value = data
  } catch (e) {
    console.warn('[Portal] Failed to load profile:', e)
  }
}

// ── Actions ────────────────────────────────

async function sendPortalRequest(targetUserId) {
  try {
    error.value = null
    await api.post('/api/v1/multiverse/portals/request', {
      target_user_id: targetUserId,
    })
    await loadPortals()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to send request'
  }
}

async function respondToPortal(portalId, accept) {
  try {
    error.value = null
    await api.post(`/api/v1/multiverse/portals/${portalId}/respond`, { accept })
    await loadPortals()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to respond'
  }
}

async function enterPortal(portal) {
  emit('enter-portal', portal)
}

function visitVillage(userId) {
  emit('visit-village', userId)
}

// ── Computed ───────────────────────────────

const activePortals = computed(() =>
  portals.value.filter(p => p.status === 'active')
)

const pendingRequests = computed(() =>
  portals.value.filter(p => p.status === 'pending' && !p.is_requester)
)

const pendingOutgoing = computed(() =>
  portals.value.filter(p => p.status === 'pending' && p.is_requester)
)

const requestCount = computed(() => pendingRequests.value.length)

// ── Lifecycle ──────────────────────────────

watch(() => props.show, (val) => {
  if (val) {
    loadProfile()
    loadPortals()
    if (activeTab.value === 'discover') loadDirectory()
  }
})

watch(activeTab, (tab) => {
  if (tab === 'discover') loadDirectory()
})
</script>

<template>
  <transition name="slide-panel">
    <div
      v-if="show"
      class="fixed inset-y-0 right-0 z-40 w-full sm:w-[420px] max-w-full flex flex-col bg-apex-dark/95 backdrop-blur-xl border-l border-apex-border shadow-2xl"
    >
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-apex-border">
        <div class="flex items-center gap-3">
          <span class="w-3 h-3 rounded-full bg-purple-400 animate-pulse"></span>
          <span class="text-sm font-medium text-white">Multiverse Portal</span>
        </div>
        <button
          @click="$emit('close')"
          class="w-8 h-8 flex items-center justify-center text-gray-500 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Tabs -->
      <div class="flex border-b border-apex-border">
        <button
          v-for="tab in [
            { id: 'portals', label: 'My Portals' },
            { id: 'discover', label: 'Discover' },
            { id: 'requests', label: 'Requests' },
          ]"
          :key="tab.id"
          @click="activeTab = tab.id"
          class="flex-1 px-3 py-2.5 text-xs font-medium transition-colors relative"
          :class="activeTab === tab.id
            ? 'text-purple-300 border-b-2 border-purple-400'
            : 'text-gray-500 hover:text-gray-300'"
        >
          {{ tab.label }}
          <span
            v-if="tab.id === 'requests' && requestCount > 0"
            class="absolute -top-0.5 right-2 w-4 h-4 bg-purple-500 rounded-full text-[10px] text-white flex items-center justify-center"
          >{{ requestCount }}</span>
        </button>
      </div>

      <!-- Error banner -->
      <div v-if="error" class="mx-4 mt-3 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-xs">
        {{ error }}
        <button @click="error = null" class="ml-2 text-red-300 hover:text-white">&times;</button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-4 space-y-3">

        <!-- ═══ MY PORTALS TAB ═══ -->
        <template v-if="activeTab === 'portals'">
          <div v-if="activePortals.length === 0" class="text-center py-8 text-gray-500">
            <div class="text-3xl mb-3">&#x1F573;</div>
            <p class="text-sm">No active portals yet</p>
            <p class="text-xs mt-1 text-gray-600">Click "Discover" to find villages to connect with</p>
          </div>

          <div
            v-for="portal in activePortals"
            :key="portal.portal_id"
            class="bg-white/5 rounded-xl p-3 border border-white/5 hover:border-purple-500/30 transition-colors"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-medium text-white">{{ portal.other_village_name }}</span>
              <span class="text-[10px] px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">Active</span>
            </div>
            <div class="flex items-center gap-2 text-xs text-gray-400 mb-3">
              <span v-if="portal.toll_to_visit > 0">Toll: {{ portal.toll_to_visit }} AJ</span>
              <span v-else>Free entry</span>
            </div>
            <div class="flex gap-2">
              <button
                @click="enterPortal(portal)"
                class="flex-1 text-xs px-3 py-1.5 bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 rounded-lg transition-colors"
              >
                Enter Portal
              </button>
              <button
                @click="visitVillage(portal.other_user_id)"
                class="text-xs px-3 py-1.5 bg-white/5 hover:bg-white/10 text-gray-400 rounded-lg transition-colors"
              >
                Preview
              </button>
            </div>
          </div>

          <!-- Pending outgoing -->
          <div v-if="pendingOutgoing.length > 0" class="mt-4">
            <h3 class="text-xs text-gray-500 font-medium mb-2 uppercase tracking-wider">Pending Sent</h3>
            <div
              v-for="portal in pendingOutgoing"
              :key="portal.portal_id"
              class="bg-white/3 rounded-lg p-3 border border-white/5 mb-2"
            >
              <div class="flex items-center justify-between">
                <span class="text-sm text-gray-300">{{ portal.other_village_name }}</span>
                <span class="text-[10px] px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-400">Pending</span>
              </div>
            </div>
          </div>
        </template>

        <!-- ═══ DISCOVER TAB ═══ -->
        <template v-if="activeTab === 'discover'">
          <!-- Search -->
          <div class="relative mb-3">
            <input
              v-model="searchQuery"
              @input="loadDirectory"
              placeholder="Search villages..."
              class="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-purple-500/50"
            />
          </div>

          <div v-if="loading" class="flex items-center justify-center py-8">
            <div class="w-5 h-5 border-2 border-purple-500/30 border-t-purple-400 rounded-full animate-spin"></div>
          </div>

          <div v-else-if="directory.length === 0" class="text-center py-8 text-gray-500">
            <p class="text-sm">No public villages found</p>
          </div>

          <div
            v-for="village in directory"
            :key="village.user_id"
            class="bg-white/5 rounded-xl p-3 border border-white/5 hover:border-purple-500/30 transition-colors"
          >
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-medium text-white">{{ village.name }}</span>
              <span v-if="village.is_featured" class="text-[10px] px-2 py-0.5 rounded-full bg-gold/20 text-gold">Featured</span>
            </div>
            <p v-if="village.description" class="text-xs text-gray-400 mb-2 line-clamp-2">{{ village.description }}</p>
            <div class="flex items-center gap-3 text-[10px] text-gray-500 mb-3">
              <span>{{ village.total_visits }} visits</span>
              <span>{{ village.total_aj_earned.toFixed(0) }} AJ earned</span>
            </div>
            <div class="flex gap-2">
              <button
                @click="sendPortalRequest(village.user_id)"
                class="flex-1 text-xs px-3 py-1.5 bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 rounded-lg transition-colors"
              >
                Request Portal
              </button>
              <button
                @click="visitVillage(village.user_id)"
                class="text-xs px-3 py-1.5 bg-white/5 hover:bg-white/10 text-gray-400 rounded-lg transition-colors"
              >
                Preview
              </button>
            </div>
          </div>
        </template>

        <!-- ═══ REQUESTS TAB ═══ -->
        <template v-if="activeTab === 'requests'">
          <div v-if="pendingRequests.length === 0" class="text-center py-8 text-gray-500">
            <p class="text-sm">No pending requests</p>
          </div>

          <div
            v-for="portal in pendingRequests"
            :key="portal.portal_id"
            class="bg-white/5 rounded-xl p-3 border border-white/5"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-medium text-white">{{ portal.other_village_name }}</span>
              <span class="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300">Incoming</span>
            </div>
            <div class="flex gap-2 mt-3">
              <button
                @click="respondToPortal(portal.portal_id, true)"
                class="flex-1 text-xs px-3 py-1.5 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-lg transition-colors"
              >
                Accept
              </button>
              <button
                @click="respondToPortal(portal.portal_id, false)"
                class="flex-1 text-xs px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"
              >
                Decline
              </button>
            </div>
          </div>
        </template>
      </div>

      <!-- Footer: My Village Info -->
      <div v-if="myProfile" class="px-4 py-3 border-t border-apex-border">
        <div class="flex items-center justify-between text-xs">
          <div class="text-gray-400">
            <span class="text-white font-medium">{{ myProfile.name }}</span>
            <span class="mx-1">&middot;</span>
            <span>{{ myProfile.portal_access }}</span>
          </div>
          <div class="text-gray-500">
            {{ myProfile.total_visits }} visits
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.slide-panel-enter-active,
.slide-panel-leave-active {
  transition: transform 0.3s ease;
}

.slide-panel-enter-from,
.slide-panel-leave-to {
  transform: translateX(100%);
}
</style>
