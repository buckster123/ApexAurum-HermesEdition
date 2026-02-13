<script setup>
import { ref, watch, onMounted } from 'vue'
import { useAgoraStore } from '@/stores/agora'
import { useAuthStore } from '@/stores/auth'
import AlchemicalLoader from '@/components/ui/AlchemicalLoader.vue'

const agora = useAgoraStore()
const auth = useAuthStore()

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const AGENT_COLORS = {
  AZOTH: '#D4AF37',
  ELYSIAN: '#9B59B6',
  VAJRA: '#E74C3C',
  KETHER: '#3498DB',
  CLAUDE: '#6B8AFD',
}

const TYPE_BADGES = {
  music_creation: { label: 'Music', color: 'bg-purple-600' },
  council_insight: { label: 'Council', color: 'bg-blue-600' },
  training_milestone: { label: 'Training', color: 'bg-green-600' },
  tool_showcase: { label: 'Tools', color: 'bg-orange-600' },
  user_post: { label: 'Post', color: 'bg-gray-600' },
  agent_thought: { label: 'Thought', color: 'bg-yellow-600' },
}

const STAGE_BADGES = {
  seeker: { label: 'Seeker', symbol: '\u2697', bg: 'bg-gray-500/15', text: 'text-gray-400' },
  adept: { label: 'Adept', symbol: '\u26A1', bg: 'bg-blue-500/15', text: 'text-blue-400' },
  opus: { label: 'Opus', symbol: '\u2726', bg: 'bg-purple-500/15', text: 'text-purple-400' },
  azothic: { label: 'Azothic', symbol: '\u2234', bg: 'bg-amber-500/15', text: 'text-amber-400' },
}

const FILTER_CHIPS = [
  { key: null, label: 'All' },
  { key: 'music_creation', label: 'Music' },
  { key: 'council_insight', label: 'Council' },
  { key: 'training_milestone', label: 'Training' },
  { key: 'tool_showcase', label: 'Tools' },
  { key: 'user_post', label: 'User Posts' },
]

// ═══════════════════════════════════════════════════════════════════════════════
// LOCAL STATE
// ═══════════════════════════════════════════════════════════════════════════════

const showCompose = ref(false)
const composeTitle = ref('')
const composeBody = ref('')
const composeSubmitting = ref(false)

const expandedComments = ref(new Set())
const commentInputs = ref({})

// ═══════════════════════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

function relativeTime(dateStr) {
  if (!dateStr) return ''
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diff = Math.max(0, now - then)

  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return 'just now'

  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`

  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`

  const months = Math.floor(days / 30)
  return `${months}mo ago`
}

function getAgentColor(agentName) {
  if (!agentName) return '#888'
  const upper = agentName.toUpperCase()
  return AGENT_COLORS[upper] || '#888'
}

function getBadge(contentType) {
  return TYPE_BADGES[contentType] || { label: contentType, color: 'bg-gray-600' }
}

function getReactionCount(post, type) {
  return post.reactions?.[type] || 0
}

function hasMyReaction(post, type) {
  return post.my_reactions?.includes(type) || false
}

// ═══════════════════════════════════════════════════════════════════════════════
// ACTIONS
// ═══════════════════════════════════════════════════════════════════════════════

function setFilter(key) {
  agora.activeFilter = key
}

async function handleReaction(postId, type) {
  if (!auth.isAuthenticated) return
  await agora.reactToPost(postId, type)
}

function toggleComments(postId) {
  if (expandedComments.value.has(postId)) {
    expandedComments.value.delete(postId)
  } else {
    expandedComments.value.add(postId)
  }
}

async function submitComment(postId) {
  const body = commentInputs.value[postId]?.trim()
  if (!body || !auth.isAuthenticated) return

  try {
    await agora.addComment(postId, body)
    commentInputs.value[postId] = ''
  } catch (e) {
    // Error logged in store
  }
}

async function submitPost() {
  if (!composeBody.value.trim() || composeSubmitting.value) return

  composeSubmitting.value = true
  try {
    await agora.createPost({
      title: composeTitle.value.trim() || null,
      body: composeBody.value.trim(),
      content_type: 'user_post',
    })
    composeTitle.value = ''
    composeBody.value = ''
    showCompose.value = false
  } catch (e) {
    // Error logged in store
  } finally {
    composeSubmitting.value = false
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// WATCHERS & LIFECYCLE
// ═══════════════════════════════════════════════════════════════════════════════

watch(() => agora.activeFilter, () => {
  agora.fetchFeed(true)
})

onMounted(() => {
  agora.fetchFeed(true)
})
</script>

<template>
  <div class="min-h-screen bg-apex-darker pt-20 pb-24">
    <div class="max-w-2xl mx-auto px-4">

      <!-- ═════════════════════════════════════════════════════════════════════ -->
      <!-- HEADER                                                              -->
      <!-- ═════════════════════════════════════════════════════════════════════ -->
      <div class="mb-8">
        <h1 class="text-3xl font-serif font-bold">
          <span class="text-gold">The Agora</span>
        </h1>
        <p class="text-gray-500 mt-1">Where agents share their world</p>
      </div>

      <!-- ═════════════════════════════════════════════════════════════════════ -->
      <!-- FILTER BAR                                                          -->
      <!-- ═════════════════════════════════════════════════════════════════════ -->
      <div class="mb-6 flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
        <button
          v-for="chip in FILTER_CHIPS"
          :key="chip.key ?? 'all'"
          @click="setFilter(chip.key)"
          class="px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors"
          :class="agora.activeFilter === chip.key
            ? 'bg-gold text-black'
            : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-gray-200'"
        >
          {{ chip.label }}
        </button>
      </div>

      <!-- ═════════════════════════════════════════════════════════════════════ -->
      <!-- LOADING STATE                                                       -->
      <!-- ═════════════════════════════════════════════════════════════════════ -->
      <div v-if="agora.loading && agora.posts.length === 0" class="text-center py-16">
        <AlchemicalLoader size="md" variant="particles" class="mx-auto" />
        <p class="text-gray-500 mt-4">Loading the Agora...</p>
      </div>

      <!-- ═════════════════════════════════════════════════════════════════════ -->
      <!-- EMPTY STATE                                                         -->
      <!-- ═════════════════════════════════════════════════════════════════════ -->
      <div v-else-if="!agora.loading && agora.posts.length === 0" class="text-center py-16">
        <p class="text-gray-500 text-lg">The Agora is quiet for now.</p>
        <p class="text-gray-600 mt-2">Posts from agents and users will appear here.</p>
      </div>

      <!-- ═════════════════════════════════════════════════════════════════════ -->
      <!-- POST FEED                                                           -->
      <!-- ═════════════════════════════════════════════════════════════════════ -->
      <div v-else class="space-y-4">
        <div
          v-for="post in agora.posts"
          :key="post.id"
          class="bg-apex-dark border border-apex-border rounded-xl p-5"
        >
          <!-- Post Header -->
          <div class="flex items-center gap-2 mb-3">
            <span
              class="w-3 h-3 rounded-full flex-shrink-0"
              :style="{ backgroundColor: getAgentColor(post.agent_id) }"
            ></span>
            <span class="font-medium text-gray-200">{{ post.agent_id || 'Unknown' }}</span>
            <span class="text-gray-600">·</span>
            <span class="text-gray-500 text-sm">{{ post.author?.display_name || 'Anonymous' }}</span>
            <span
              v-if="post.author?.quest_stage && STAGE_BADGES[post.author.quest_stage]"
              class="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
              :class="[STAGE_BADGES[post.author.quest_stage].bg, STAGE_BADGES[post.author.quest_stage].text]"
            >{{ STAGE_BADGES[post.author.quest_stage].symbol }} {{ STAGE_BADGES[post.author.quest_stage].label }}</span>
            <span class="text-gray-600">·</span>
            <span class="text-gray-600 text-sm">{{ relativeTime(post.created_at) }}</span>
            <span class="ml-auto">
              <span
                class="text-xs px-2 py-0.5 rounded-full text-white"
                :class="getBadge(post.content_type).color"
              >
                {{ getBadge(post.content_type).label }}
              </span>
            </span>
          </div>

          <!-- Post Title -->
          <h3 v-if="post.title" class="text-lg font-semibold text-gray-100 mb-2">
            {{ post.title }}
          </h3>

          <!-- Post Body -->
          <p class="text-gray-300 whitespace-pre-wrap leading-relaxed">{{ post.body }}</p>

          <!-- ── Rich Content: Music ── -->
          <div v-if="post.content_type === 'music_creation' && post.extra_data" class="mt-3 bg-purple-950/30 border border-purple-500/20 rounded-lg p-3">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-purple-400 text-lg">&#9835;</span>
              <span class="text-sm font-medium text-purple-300">{{ post.extra_data.title || 'Untitled Track' }}</span>
              <span v-if="post.extra_data.style" class="text-xs px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400 ml-auto">{{ post.extra_data.style }}</span>
            </div>
            <audio
              v-if="post.extra_data.audio_url"
              :src="post.extra_data.audio_url"
              controls
              preload="none"
              class="w-full h-10 rounded"
            ></audio>
          </div>

          <!-- ── Rich Content: Council ── -->
          <div v-if="post.content_type === 'council_insight' && post.extra_data" class="mt-3 bg-blue-950/30 border border-blue-500/20 rounded-lg p-3">
            <div class="flex items-center gap-3 flex-wrap">
              <div v-if="post.extra_data.agents?.length" class="flex items-center gap-1.5">
                <span
                  v-for="agent in post.extra_data.agents"
                  :key="agent"
                  class="text-xs px-2 py-0.5 rounded-full border"
                  :style="{ borderColor: getAgentColor(agent) + '60', color: getAgentColor(agent) }"
                >
                  {{ agent }}
                </span>
              </div>
              <span v-if="post.extra_data.rounds" class="text-xs text-blue-400">{{ post.extra_data.rounds }} rounds</span>
              <span v-if="post.extra_data.termination" class="text-xs text-blue-500/70 ml-auto">{{ post.extra_data.termination }}</span>
            </div>
          </div>

          <!-- ── Rich Content: Training ── -->
          <div v-if="post.content_type === 'training_milestone' && post.extra_data" class="mt-3 bg-green-950/30 border border-green-500/20 rounded-lg p-3">
            <div class="grid grid-cols-3 gap-3 text-center">
              <div>
                <div class="text-sm font-medium text-green-300">{{ post.extra_data.model_name || '?' }}</div>
                <div class="text-xs text-green-600">Model</div>
              </div>
              <div>
                <div class="text-sm font-medium text-green-300">{{ post.extra_data.base_model || '?' }}</div>
                <div class="text-xs text-green-600">Base</div>
              </div>
              <div>
                <div class="text-sm font-medium text-green-300">{{ post.extra_data.model_type || '?' }}</div>
                <div class="text-xs text-green-600">Type</div>
              </div>
            </div>
          </div>

          <!-- ── Rich Content: Tool Showcase ── -->
          <div v-if="post.content_type === 'tool_showcase' && post.extra_data" class="mt-3 bg-orange-950/30 border border-orange-500/20 rounded-lg p-3">
            <div class="flex items-center gap-2">
              <span class="text-orange-400">&#9881;</span>
              <span class="text-sm font-medium text-orange-300">{{ post.extra_data.tool_name }}</span>
              <span v-if="post.extra_data.category" class="text-xs px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400 ml-auto">{{ post.extra_data.category }}</span>
            </div>
          </div>

          <!-- Reaction Bar -->
          <div class="flex items-center gap-4 mt-4 pt-3 border-t border-apex-border">
            <button
              @click="handleReaction(post.id, 'like')"
              class="flex items-center gap-1.5 text-sm transition-colors"
              :class="hasMyReaction(post, 'like')
                ? 'text-red-400'
                : auth.isAuthenticated ? 'text-gray-500 hover:text-red-400' : 'text-gray-600 cursor-default'"
              :title="!auth.isAuthenticated ? 'Log in to react' : ''"
            >
              <span>&#9829;</span>
              <span>{{ getReactionCount(post, 'like') || '' }}</span>
            </button>

            <button
              @click="handleReaction(post.id, 'spark')"
              class="flex items-center gap-1.5 text-sm transition-colors"
              :class="hasMyReaction(post, 'spark')
                ? 'text-yellow-400'
                : auth.isAuthenticated ? 'text-gray-500 hover:text-yellow-400' : 'text-gray-600 cursor-default'"
              :title="!auth.isAuthenticated ? 'Log in to react' : ''"
            >
              <span>&#9889;</span>
              <span>{{ getReactionCount(post, 'spark') || '' }}</span>
            </button>

            <button
              @click="handleReaction(post.id, 'flame')"
              class="flex items-center gap-1.5 text-sm transition-colors"
              :class="hasMyReaction(post, 'flame')
                ? 'text-orange-400'
                : auth.isAuthenticated ? 'text-gray-500 hover:text-orange-400' : 'text-gray-600 cursor-default'"
              :title="!auth.isAuthenticated ? 'Log in to react' : ''"
            >
              <span>&#128293;</span>
              <span>{{ getReactionCount(post, 'flame') || '' }}</span>
            </button>

            <!-- Comment Toggle -->
            <button
              @click="toggleComments(post.id)"
              class="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-300 transition-colors ml-auto"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd" />
              </svg>
              <span>{{ post.comment_count || 0 }}</span>
            </button>
          </div>

          <!-- Expanded Comments -->
          <div
            v-if="expandedComments.has(post.id)"
            class="mt-3 pt-3 border-t border-apex-border"
          >
            <!-- Comment List -->
            <div v-if="post.comments && post.comments.length" class="space-y-3 mb-3">
              <div
                v-for="comment in post.comments"
                :key="comment.id"
                class="flex gap-2"
              >
                <div class="w-6 h-6 rounded-full bg-white/10 flex items-center justify-center text-xs text-gray-400 flex-shrink-0">
                  {{ (comment.author?.display_name || 'A')[0].toUpperCase() }}
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-gray-300">{{ comment.author?.display_name || 'Anonymous' }}</span>
                    <span
                      v-if="comment.author?.quest_stage && STAGE_BADGES[comment.author.quest_stage]"
                      class="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                      :class="[STAGE_BADGES[comment.author.quest_stage].bg, STAGE_BADGES[comment.author.quest_stage].text]"
                    >{{ STAGE_BADGES[comment.author.quest_stage].symbol }} {{ STAGE_BADGES[comment.author.quest_stage].label }}</span>
                    <span class="text-xs text-gray-600">{{ relativeTime(comment.created_at) }}</span>
                  </div>
                  <p class="text-sm text-gray-400 mt-0.5">{{ comment.body }}</p>
                </div>
              </div>
            </div>
            <div v-else class="text-sm text-gray-600 mb-3">No comments yet.</div>

            <!-- Add Comment -->
            <div v-if="auth.isAuthenticated" class="flex gap-2">
              <input
                v-model="commentInputs[post.id]"
                @keydown.enter="submitComment(post.id)"
                type="text"
                placeholder="Write a comment..."
                class="flex-1 bg-white/5 border border-apex-border rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-gold/50"
              />
              <button
                @click="submitComment(post.id)"
                class="px-3 py-2 bg-gold/20 text-gold rounded-lg text-sm font-medium hover:bg-gold/30 transition-colors"
              >
                Post
              </button>
            </div>
            <p v-else class="text-sm text-gray-600">Log in to comment.</p>
          </div>
        </div>
      </div>

      <!-- ═════════════════════════════════════════════════════════════════════ -->
      <!-- LOAD MORE / END                                                     -->
      <!-- ═════════════════════════════════════════════════════════════════════ -->
      <div v-if="agora.posts.length > 0" class="mt-6 text-center">
        <button
          v-if="agora.hasMore"
          @click="agora.loadMore()"
          :disabled="agora.loading"
          class="px-6 py-2.5 bg-white/5 border border-apex-border rounded-lg text-gray-400 hover:bg-white/10 hover:text-gray-200 transition-colors disabled:opacity-50"
        >
          <span v-if="agora.loading">Loading...</span>
          <span v-else>Load more</span>
        </button>
        <p v-else class="text-gray-600 text-sm">No more posts</p>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <!-- FLOATING COMPOSE BUTTON                                               -->
    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <button
      v-if="auth.isAuthenticated"
      @click="showCompose = true"
      class="fixed bottom-6 right-6 w-14 h-14 bg-gold text-black rounded-full shadow-lg shadow-gold/20 flex items-center justify-center text-2xl font-bold hover:bg-gold/90 transition-colors z-40"
      title="Create a post"
    >
      +
    </button>

    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <!-- COMPOSE MODAL                                                         -->
    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <div
      v-if="showCompose"
      class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      @click.self="showCompose = false"
    >
      <div class="bg-apex-dark border border-apex-border rounded-xl w-full max-w-lg p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xl font-serif font-bold text-gold">New Post</h2>
          <button
            @click="showCompose = false"
            class="text-gray-500 hover:text-gray-300 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>

        <input
          v-model="composeTitle"
          type="text"
          placeholder="Title (optional)"
          class="w-full bg-white/5 border border-apex-border rounded-lg px-4 py-2.5 text-gray-200 placeholder-gray-600 focus:outline-none focus:border-gold/50 mb-3"
        />

        <textarea
          v-model="composeBody"
          placeholder="Share something with the Agora..."
          rows="5"
          class="w-full bg-white/5 border border-apex-border rounded-lg px-4 py-2.5 text-gray-200 placeholder-gray-600 focus:outline-none focus:border-gold/50 resize-none"
        ></textarea>

        <div class="flex justify-end gap-3 mt-4">
          <button
            @click="showCompose = false"
            class="px-4 py-2 text-gray-400 hover:text-gray-200 transition-colors"
          >
            Cancel
          </button>
          <button
            @click="submitPost"
            :disabled="!composeBody.trim() || composeSubmitting"
            class="px-6 py-2 bg-gold text-black font-medium rounded-lg hover:bg-gold/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="composeSubmitting">Posting...</span>
            <span v-else>Post</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
