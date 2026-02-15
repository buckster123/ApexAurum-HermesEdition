<script setup>
import { computed, watch, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useApexJouleStore } from '@/stores/apexjoule'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  compact: { type: Boolean, default: false }
})

const router = useRouter()
const aj = useApexJouleStore()
const auth = useAuthStore()

const earnFlash = ref(false)
const earnAmount = ref(0)

// Initialize on mount if authenticated
if (auth.isAuthenticated && !aj.hasBalance) {
  aj.initialize()
}

// Watch for earn events — trigger flash animation
watch(() => aj.lastEarn, (earn) => {
  if (earn) {
    earnAmount.value = earn.earned
    earnFlash.value = true
    setTimeout(() => { earnFlash.value = false }, 2500)
  }
})

const balance = computed(() => aj.displayBalance)
const level = computed(() => aj.userLevel)
const levelName = computed(() => aj.userLevelName)
const topAgentName = computed(() => {
  const top = aj.topAgent
  return top ? top[0] : null
})

function goToEconomy() {
  router.push('/economy')
}
</script>

<template>
  <button
    v-if="auth.isAuthenticated"
    @click="goToEconomy"
    class="aj-wallet-badge group relative flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all duration-300 cursor-pointer"
    :class="[
      earnFlash
        ? 'border-gold/60 bg-gold/10'
        : 'border-gold/20 bg-apex-dark/60 hover:border-gold/40 hover:bg-apex-dark/80'
    ]"
    title="ApexJoule Economy"
  >
    <!-- Diamond symbol -->
    <span class="text-gold text-sm">&#9670;</span>

    <!-- Balance -->
    <span class="text-sm font-semibold text-gold tabular-nums">
      {{ balance }}
    </span>
    <span v-if="!compact" class="text-[10px] text-gray-500 uppercase tracking-wider">AJ</span>

    <!-- Level (hidden on compact / smaller screens) -->
    <template v-if="!compact">
      <span class="text-gray-600 text-xs hidden lg:inline">&#183;</span>
      <span class="text-xs text-gray-500 hidden lg:inline truncate max-w-[100px]">
        Lv.{{ level }} {{ levelName }}
      </span>
    </template>

    <!-- Earn flash overlay -->
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      leave-active-class="transition-all duration-500 ease-in"
      enter-from-class="opacity-0 translate-y-1"
      leave-to-class="opacity-0 -translate-y-3"
    >
      <span
        v-if="earnFlash"
        class="absolute -top-5 right-0 text-xs font-semibold text-gold pointer-events-none"
      >
        +{{ earnAmount.toFixed(1) }}
      </span>
    </Transition>
  </button>
</template>

<style scoped>
.aj-wallet-badge {
  font-variant-numeric: tabular-nums;
}
</style>
