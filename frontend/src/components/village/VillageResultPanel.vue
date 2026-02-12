<script setup>
/**
 * VillageResultPanel - Slide-out Result Display
 *
 * Shows task results from the Village interface. Slides in from the right.
 * Displays streaming content during execution, final result on completion.
 * Supports markdown-like formatting for code blocks.
 *
 * "The scroll unfurls to reveal the agent's work"
 */

import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  result: { type: Object, default: null },
  error: { type: String, default: null },
  streamingContent: { type: String, default: '' },
  streamingAgent: { type: String, default: null },
  isExecuting: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'open-in-chat', 'cancel'])

const contentRef = ref(null)
const copied = ref(false)

const AGENT_COLORS = {
  AZOTH: '#FFD700',
  VAJRA: '#4FC3F7',
  ELYSIAN: '#ff69b4',
  KETHER: '#9370db',
}

// Display content — streaming or final
const displayContent = computed(() => {
  if (props.isExecuting && props.streamingContent) {
    return props.streamingContent
  }
  if (props.result?.content) {
    return props.result.content
  }
  if (props.error) {
    return props.error
  }
  return ''
})

const agentColor = computed(() =>
  AGENT_COLORS[props.streamingAgent || props.result?.agent] || '#888'
)

const agentName = computed(() =>
  props.streamingAgent || props.result?.agent || 'Agent'
)

const isShort = computed(() => displayContent.value.length < 200)

const conversationId = computed(() => props.result?.conversationId)

// Auto-scroll content during streaming
watch(() => props.streamingContent, async () => {
  if (props.isExecuting && contentRef.value) {
    await nextTick()
    contentRef.value.scrollTop = contentRef.value.scrollHeight
  }
})

// --- Actions ---
async function copyContent() {
  try {
    await navigator.clipboard.writeText(displayContent.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    // Fallback for older browsers
    const ta = document.createElement('textarea')
    ta.value = displayContent.value
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  }
}

function downloadContent() {
  const blob = new Blob([displayContent.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `village-task-${Date.now()}.txt`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <transition name="slide-panel">
    <div
      v-if="show"
      class="fixed inset-y-0 right-0 z-40 w-full sm:w-96 max-w-full flex flex-col bg-apex-dark/95 backdrop-blur-xl border-l border-apex-border shadow-2xl"
    >
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-apex-border">
        <div class="flex items-center gap-3">
          <span
            class="w-3 h-3 rounded-full"
            :class="isExecuting ? 'animate-pulse' : ''"
            :style="{ backgroundColor: agentColor }"
          ></span>
          <div>
            <span class="text-sm font-medium text-white">{{ agentName }}</span>
            <span v-if="result?.isCouncil" class="text-xs text-gray-500 ml-2">Council</span>
          </div>
          <div v-if="isExecuting" class="flex items-center gap-1.5 text-xs text-gold">
            <div class="w-3 h-3 border border-gold/30 border-t-gold rounded-full animate-spin"></div>
            Working...
          </div>
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

      <!-- Content -->
      <div
        ref="contentRef"
        class="flex-1 overflow-y-auto p-4"
      >
        <!-- Error display -->
        <div v-if="error && !isExecuting" class="bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-4">
          <div class="flex items-center gap-2 mb-2">
            <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <span class="text-red-400 text-sm font-medium">Task Failed</span>
          </div>
          <p class="text-red-300 text-sm">{{ error }}</p>
        </div>

        <!-- Content display -->
        <div
          v-if="displayContent"
          class="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap break-words font-mono"
        >{{ displayContent }}</div>

        <!-- Empty state (executing, no content yet) -->
        <div
          v-else-if="isExecuting"
          class="flex flex-col items-center justify-center h-32 text-gray-500"
        >
          <div class="w-6 h-6 border-2 border-gold/30 border-t-gold rounded-full animate-spin mb-3"></div>
          <span class="text-sm">Agent is thinking...</span>
        </div>
      </div>

      <!-- Footer Actions -->
      <div class="px-4 py-3 border-t border-apex-border flex items-center gap-2">
        <template v-if="isExecuting">
          <button
            @click="$emit('cancel')"
            class="flex-1 text-xs px-3 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"
          >
            Cancel
          </button>
        </template>
        <template v-else>
          <button
            @click="copyContent"
            class="text-xs px-3 py-2 bg-white/5 hover:bg-white/10 text-gray-300 rounded-lg transition-colors"
          >
            {{ copied ? 'Copied!' : 'Copy' }}
          </button>
          <button
            @click="downloadContent"
            class="text-xs px-3 py-2 bg-white/5 hover:bg-white/10 text-gray-300 rounded-lg transition-colors"
          >
            Download
          </button>
          <button
            v-if="conversationId"
            @click="$emit('open-in-chat', conversationId)"
            class="flex-1 text-xs px-3 py-2 bg-gold/10 hover:bg-gold/20 text-gold rounded-lg transition-colors text-center"
          >
            Open in Chat
          </button>
        </template>
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
