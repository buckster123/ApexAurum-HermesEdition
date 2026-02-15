<script setup>
/**
 * MusicView - apexXuno Music Studio
 *
 * The Athanor's creative voice. Browse library, generate new tracks,
 * and experience AI-powered music creation with real-time SSE streaming.
 */

import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useMusicStore } from '@/stores/music'

const music = useMusicStore()

// Local UI state
const showGenerateModal = ref(false)
const viewMode = ref('grid') // 'grid' or 'list'
const deleteConfirm = ref(null)

// Generate form
const prompt = ref('')
const style = ref('')
const title = ref('')
const selectedModel = ref('V5')
const instrumental = ref(true)
const generateError = ref('')

const models = [
  { id: 'V3_5', name: 'V3.5', desc: 'Fast, lower quality' },
  { id: 'V4', name: 'V4', desc: 'Balanced' },
  { id: 'V4_5', name: 'V4.5', desc: 'Better quality' },
  { id: 'V5', name: 'V5', desc: 'Best quality (recommended)' },
]

// Example prompts for inspiration
const examplePrompts = [
  'Ethereal ambient soundscape with soft synthesizers and distant piano',
  'Upbeat electronic track with driving bass and euphoric melodies',
  'Cinematic orchestral piece with building tension and resolution',
  'Lo-fi hip hop beats with jazzy samples and vinyl crackle',
  'Medieval tavern music with lutes, flutes, and merry rhythms',
  'Dark industrial ambient with mechanical rhythms and distorted textures',
]

function useExamplePrompt(example) {
  prompt.value = example
}

// Computed
const filteredLibrary = computed(() => music.library)

const stats = computed(() => ({
  total: music.total,
  completed: music.completedTracks.length,
  favorites: music.favoriteTracks.length,
  duration: formatDuration(music.totalDuration),
}))

// Helpers
function formatDuration(seconds) {
  if (!seconds) return '0m'
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return 'Just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`

  return date.toLocaleDateString()
}

function getStatusColor(status) {
  switch (status) {
    case 'completed': return 'text-green-400'
    case 'generating': return 'text-blue-400 animate-pulse'
    case 'downloading': return 'text-purple-400 animate-pulse'
    case 'failed': return 'text-red-400'
    default: return 'text-yellow-400'
  }
}

function getStatusIcon(status) {
  switch (status) {
    case 'completed': return '✓'
    case 'generating': return '⟳'
    case 'downloading': return '⬇'
    case 'failed': return '✗'
    default: return '○'
  }
}

// Actions
let pollInterval = null

onMounted(async () => {
  await music.fetchLibrary()

  // Poll pending tracks every 10 seconds
  pollInterval = setInterval(() => {
    if (music.pendingTracks.length > 0) {
      music.pollPendingTracks()
    }
  }, 10000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
})

async function handleGenerate() {
  if (!prompt.value.trim()) return

  generateError.value = ''

  try {
    await music.generateTrack({
      prompt: prompt.value,
      style: style.value || null,
      title: title.value || null,
      model: selectedModel.value,
      instrumental: instrumental.value,
    })

    // Success - close modal and reset form
    showGenerateModal.value = false
    prompt.value = ''
    style.value = ''
    title.value = ''
  } catch (e) {
    generateError.value = e.message
  }
}

function openGenerateModal() {
  generateError.value = ''
  showGenerateModal.value = true
}

async function handleDelete(task) {
  if (deleteConfirm.value === task.id) {
    await music.deleteTrack(task.id)
    deleteConfirm.value = null
  } else {
    deleteConfirm.value = task.id
    setTimeout(() => {
      deleteConfirm.value = null
    }, 3000)
  }
}

function handlePlay(task) {
  if (task.status === 'completed') {
    music.playTrack(task)
  }
}

// Update filters
function toggleFavoritesFilter() {
  music.filters.favoritesOnly = !music.filters.favoritesOnly
  music.fetchLibrary()
}

function setStatusFilter(status) {
  music.filters.status = music.filters.status === status ? null : status
  music.fetchLibrary()
}

let searchTimeout = null
function handleSearch(e) {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    music.filters.search = e.target.value
    music.fetchLibrary()
  }, 300)
}
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-8 pb-28">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
      <div>
        <h1 class="text-3xl font-bold text-gold">apexXuno</h1>
        <p class="text-gray-400 mt-1">AI music generation — the Athanor's voice</p>
      </div>
      <button @click="openGenerateModal" class="btn-primary flex items-center gap-2">
        + Generate
      </button>
    </div>

    <!-- Stats Bar -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
      <div class="card p-4 text-center">
        <div class="text-2xl font-bold text-gold">{{ stats.total }}</div>
        <div class="text-sm text-gray-400">Total Tracks</div>
      </div>
      <div class="card p-4 text-center">
        <div class="text-2xl font-bold text-green-400">{{ stats.completed }}</div>
        <div class="text-sm text-gray-400">Completed</div>
      </div>
      <div class="card p-4 text-center">
        <div class="text-2xl font-bold text-yellow-400">{{ stats.favorites }}</div>
        <div class="text-sm text-gray-400">Favorites</div>
      </div>
      <div class="card p-4 text-center">
        <div class="text-2xl font-bold text-purple-400">{{ stats.duration }}</div>
        <div class="text-sm text-gray-400">Total Duration</div>
      </div>
    </div>

    <!-- Generation Progress Banner -->
    <Transition name="fade">
      <div
        v-if="music.isGenerating"
        class="mb-6 card border-gold/30"
      >
        <div class="flex items-center gap-4">
          <div class="w-10 h-10 border-2 border-gold rounded-lg flex items-center justify-center">
            <svg class="w-5 h-5 text-gold animate-spin" fill="none" viewBox="0 0 24 24"><path stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M12 2v4m0 12v4m10-10h-4M6 12H2m15.07-7.07l-2.83 2.83M9.76 14.24l-2.83 2.83m12.14 0l-2.83-2.83M9.76 9.76L6.93 6.93"/></svg>
          </div>
          <div class="flex-1">
            <h3 class="font-medium text-gold">Generating...</h3>
            <p class="text-sm text-gray-400">{{ music.generationProgress }}</p>
          </div>
          <button
            @click="music.cancelGeneration"
            class="btn-secondary text-sm"
          >
            Cancel
          </button>
        </div>
      </div>
    </Transition>

    <!-- Filters -->
    <div class="flex flex-wrap gap-4 mb-6">
      <input
        type="text"
        placeholder="Search tracks..."
        @input="handleSearch"
        class="input w-full sm:w-64"
      />

      <div class="flex gap-2">
        <button
          @click="toggleFavoritesFilter"
          class="px-3 py-2 rounded-lg text-sm transition-all"
          :class="music.filters.favoritesOnly
            ? 'bg-gold/20 ring-1 ring-gold text-gold'
            : 'bg-apex-card hover:bg-white/5 text-gray-400'"
        >
          ⭐ Favorites
        </button>

        <button
          @click="setStatusFilter('completed')"
          class="px-3 py-2 rounded-lg text-sm transition-all"
          :class="music.filters.status === 'completed'
            ? 'bg-green-500/20 ring-1 ring-green-500 text-green-400'
            : 'bg-apex-card hover:bg-white/5 text-gray-400'"
        >
          ✓ Completed
        </button>

        <button
          @click="setStatusFilter('generating')"
          class="px-3 py-2 rounded-lg text-sm transition-all"
          :class="music.filters.status === 'generating'
            ? 'bg-blue-500/20 ring-1 ring-blue-500 text-blue-400'
            : 'bg-apex-card hover:bg-white/5 text-gray-400'"
        >
          ⟳ In Progress
        </button>
      </div>

      <div class="flex gap-1 ml-auto">
        <button
          @click="viewMode = 'grid'"
          class="p-2 rounded-lg transition-colors"
          :class="viewMode === 'grid' ? 'bg-white/10 text-white' : 'text-gray-400 hover:text-white'"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
          </svg>
        </button>
        <button
          @click="viewMode = 'list'"
          class="p-2 rounded-lg transition-colors"
          :class="viewMode === 'list' ? 'bg-white/10 text-white' : 'text-gray-400 hover:text-white'"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="music.loading" class="text-center py-20 text-gray-400">
      <div class="text-sm mb-2 animate-pulse">Loading library...</div>
    </div>

    <!-- Empty State -->
    <div v-else-if="music.library.length === 0" class="text-center py-20">
      <h2 class="text-xl font-bold mb-2 text-gold">No music yet</h2>
      <p class="text-gray-400 mb-6">Generate your first track to begin your collection</p>
      <button @click="openGenerateModal" class="btn-primary">
        + Generate
      </button>
    </div>

    <!-- Grid View -->
    <div v-else-if="viewMode === 'grid'" class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="task in filteredLibrary"
        :key="task.id"
        class="card hover:border-gold/30 transition-all group cursor-pointer"
        @click="handlePlay(task)"
      >
        <!-- Album art placeholder -->
        <div class="aspect-square bg-apex-darker border border-apex-border rounded-lg mb-4 flex items-center justify-center relative overflow-hidden">
          <!-- Animated border for generating -->
          <div
            v-if="task.status === 'generating' || task.status === 'downloading'"
            class="absolute inset-0 border-2 border-gold/30 rounded-lg animate-pulse"
          />
          <svg class="w-12 h-12 text-gray-600 relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"/></svg>

          <!-- Play overlay for completed tracks -->
          <div
            v-if="task.status === 'completed'"
            class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center z-20"
          >
            <span class="w-12 h-12 border-2 border-gold rounded-full flex items-center justify-center text-gold text-lg">
              ▶
            </span>
          </div>
        </div>

        <div class="flex items-start justify-between mb-2">
          <div class="min-w-0 flex-1">
            <h3 class="font-medium truncate">{{ task.title || 'Untitled' }}</h3>
            <p class="text-sm text-gray-400 truncate">{{ task.style || 'No style' }}</p>
          </div>
          <button
            @click.stop="music.toggleFavorite(task.id)"
            class="text-xl transition-transform hover:scale-110 ml-2"
          >
            {{ task.favorite ? '⭐' : '☆' }}
          </button>
        </div>

        <p class="text-xs text-gray-500 line-clamp-2 mb-3">{{ task.prompt }}</p>

        <div class="flex items-center justify-between text-xs">
          <span :class="getStatusColor(task.status)">
            {{ getStatusIcon(task.status) }} {{ task.status }}
            <span v-if="task.progress && task.status !== 'completed'" class="ml-1">
              - {{ task.progress }}
            </span>
          </span>
          <span v-if="task.duration" class="text-gray-500">
            {{ music.formatTime(task.duration) }}
          </span>
        </div>

        <div class="flex items-center justify-between mt-2 text-xs text-gray-500">
          <span v-if="task.agent_id">by {{ task.agent_id }}</span>
          <span v-else>{{ formatDate(task.created_at) }}</span>
          <span>▶ {{ task.play_count }} plays</span>
        </div>

        <!-- Download button -->
        <button
          v-if="task.status === 'completed'"
          @click.stop="music.downloadTrack(task.id)"
          class="absolute top-2 left-2 p-1.5 bg-apex-dark/80 border border-apex-border text-gold opacity-0 group-hover:opacity-100 transition-opacity hover:border-gold/30 rounded-lg"
          title="Download MP3"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V3"/></svg>
        </button>

        <!-- Delete button -->
        <button
          v-if="task.status !== 'generating'"
          @click.stop="handleDelete(task)"
          class="absolute top-2 right-2 p-1.5 bg-apex-dark/80 border border-apex-border text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity hover:text-red-400 hover:border-red-500/30 rounded-lg"
          :title="deleteConfirm === task.id ? 'Click again to confirm' : 'Delete'"
        >
          {{ deleteConfirm === task.id ? '?' : '×' }}
        </button>
      </div>
    </div>

    <!-- List View -->
    <div v-else class="space-y-2">
      <div
        v-for="task in filteredLibrary"
        :key="task.id"
        class="card p-4 hover:border-gold/30 transition-all group cursor-pointer flex items-center gap-4"
        @click="handlePlay(task)"
      >
        <!-- Mini album art -->
        <div class="w-12 h-12 bg-apex-darker border border-apex-border rounded-lg flex items-center justify-center flex-shrink-0 relative">
          <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z"/></svg>
          <div
            v-if="task.status === 'completed'"
            class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center rounded-lg"
          >
            <span class="text-gold text-sm">▶</span>
          </div>
        </div>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <h3 class="font-medium truncate">{{ task.title || 'Untitled' }}</h3>
          <p class="text-sm text-gray-400 truncate">{{ task.style || task.prompt }}</p>
        </div>

        <!-- Status -->
        <span :class="getStatusColor(task.status)" class="text-sm">
          {{ getStatusIcon(task.status) }} {{ task.status }}
        </span>

        <!-- Duration -->
        <span v-if="task.duration" class="text-sm text-gray-500 w-16 text-right">
          {{ music.formatTime(task.duration) }}
        </span>

        <!-- Play count -->
        <span class="text-sm text-gray-500 w-16 text-right">
          ▶ {{ task.play_count }}
        </span>

        <!-- Download -->
        <button
          v-if="task.status === 'completed'"
          @click.stop="music.downloadTrack(task.id)"
          class="p-2 rounded-lg text-gray-400 hover:text-gold hover:bg-gold/20 transition-all"
          title="Download MP3"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V3"/></svg>
        </button>

        <!-- Favorite -->
        <button
          @click.stop="music.toggleFavorite(task.id)"
          class="text-xl transition-transform hover:scale-110"
        >
          {{ task.favorite ? '⭐' : '☆' }}
        </button>

        <!-- Delete -->
        <button
          v-if="task.status !== 'generating'"
          @click.stop="handleDelete(task)"
          class="p-2 rounded-lg text-gray-400 hover:text-red-400 hover:bg-red-500/20 transition-all"
        >
          {{ deleteConfirm === task.id ? '?' : '×' }}
        </button>
      </div>
    </div>

    <!-- Generate Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="showGenerateModal"
          class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          @click.self="showGenerateModal = false"
        >
          <div class="card w-full max-w-xl max-h-[90vh] overflow-y-auto">
            <div class="flex items-center justify-between mb-6">
              <h2 class="text-xl font-bold text-gold">Generate Music</h2>
              <button
                @click="showGenerateModal = false"
                class="text-gray-400 hover:text-white"
              >
                ×
              </button>
            </div>

            <div class="space-y-5">
              <!-- Prompt -->
              <div>
                <label class="block text-sm text-gray-400 mb-2">Prompt *</label>
                <textarea
                  v-model="prompt"
                  class="input h-28 resize-none"
                  placeholder="Describe the music you want..."
                ></textarea>

                <!-- Example prompts -->
                <div class="mt-2">
                  <p class="text-xs text-gray-500 mb-1">Try an example:</p>
                  <div class="flex flex-wrap gap-1">
                    <button
                      v-for="(example, i) in examplePrompts.slice(0, 3)"
                      :key="i"
                      @click="useExamplePrompt(example)"
                      class="text-xs px-2 py-1 bg-apex-darker rounded hover:bg-white/10 text-gray-400 hover:text-white truncate max-w-[200px]"
                    >
                      {{ example.slice(0, 40) }}...
                    </button>
                  </div>
                </div>
              </div>

              <!-- Style -->
              <div>
                <label class="block text-sm text-gray-400 mb-2">Style Tags (optional)</label>
                <input
                  v-model="style"
                  type="text"
                  class="input"
                  placeholder="e.g., ambient, ethereal, 432Hz, slow, synthesizer"
                />
                <p class="text-xs text-gray-500 mt-1">Comma-separated style tags for fine control</p>
              </div>

              <!-- Title -->
              <div>
                <label class="block text-sm text-gray-400 mb-2">Title (optional)</label>
                <input
                  v-model="title"
                  type="text"
                  class="input"
                  placeholder="Give your track a name"
                />
              </div>

              <!-- Model Selection -->
              <div>
                <label class="block text-sm text-gray-400 mb-2">Model</label>
                <div class="grid grid-cols-4 gap-2">
                  <button
                    v-for="model in models"
                    :key="model.id"
                    @click="selectedModel = model.id"
                    class="p-3 rounded-lg text-center text-sm transition-all"
                    :class="selectedModel === model.id
                      ? 'bg-gold/20 ring-1 ring-gold'
                      : 'bg-apex-darker hover:bg-white/5'"
                    :title="model.desc"
                  >
                    {{ model.name }}
                  </button>
                </div>
                <p class="text-xs text-gray-500 mt-2">
                  {{ models.find(m => m.id === selectedModel)?.desc }}
                </p>
              </div>

              <!-- Instrumental Toggle -->
              <div class="flex items-center gap-3">
                <button
                  @click="instrumental = !instrumental"
                  class="w-12 h-6 rounded-full transition-colors relative"
                  :class="instrumental ? 'bg-gold' : 'bg-apex-darker'"
                >
                  <span
                    class="absolute top-1 w-4 h-4 bg-white rounded-full transition-transform"
                    :class="instrumental ? 'left-7' : 'left-1'"
                  />
                </button>
                <span class="text-sm">
                  {{ instrumental ? 'Instrumental (no vocals)' : 'With vocals' }}
                </span>
              </div>

              <!-- Error -->
              <div v-if="generateError" class="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm">
                {{ generateError }}
              </div>
            </div>

            <div class="flex justify-end gap-3 mt-6 pt-4 border-t border-apex-border">
              <button @click="showGenerateModal = false" class="btn-secondary">
                Cancel
              </button>
              <button
                @click="handleGenerate"
                class="btn-primary flex items-center gap-2"
                :disabled="!prompt.trim() || music.isGenerating"
              >
                <span v-if="music.isGenerating" class="animate-spin">⟳</span>
                {{ music.isGenerating ? 'Generating...' : 'Generate' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.card {
  position: relative;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

</style>
