<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useSolanaStore } from '@/stores/solana'

const emit = defineEmits(['close'])

const solana = useSolanaStore()

const selectedToken = ref('SOL')
const selectedPack = ref('spark')
const customAmount = ref(null)
const showCustom = ref(false)

// AJ packs
const packs = [
  { id: 'spark', label: 'Spark', aj: '5,000', usd: 5 },
  { id: 'flame', label: 'Flame', aj: '11,000', usd: 10 },
  { id: 'blaze', label: 'Blaze', aj: '30,000', usd: 25 },
]

const amountUsd = computed(() => {
  if (showCustom.value && customAmount.value > 0) return customAmount.value
  const pack = packs.find(p => p.id === selectedPack.value)
  return pack?.usd || 5
})

const ajPreview = computed(() => {
  return Math.round(amountUsd.value * 1000) // AJ_PER_USD = 1000
})

const tokenAmount = computed(() => {
  if (selectedToken.value === 'USDC') return amountUsd.value.toFixed(2)
  if (solana.solPrice) return (amountUsd.value / solana.solPrice).toFixed(6)
  return '...'
})

const statusLabel = computed(() => {
  const s = solana.currentPayment?.status
  if (s === 'pending') return 'Waiting for payment...'
  if (s === 'confirmed') return 'Confirming on-chain...'
  if (s === 'credited') return 'Payment complete!'
  if (s === 'expired') return 'Payment expired'
  if (s === 'failed') return 'Payment failed'
  return ''
})

const statusColor = computed(() => {
  const s = solana.currentPayment?.status
  if (s === 'credited') return 'text-green-400'
  if (s === 'expired' || s === 'failed') return 'text-red-400'
  return 'text-gold'
})

onMounted(() => {
  solana.fetchRates()
})

onUnmounted(() => {
  solana.stopPolling()
})

async function startPayment() {
  await solana.createPayment(amountUsd.value, selectedToken.value)
}

function handleClose() {
  solana.dismiss()
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" @click.self="handleClose">
      <div class="bg-apex-dark border border-gold/20 rounded-xl w-full max-w-md mx-4 p-6 shadow-2xl">
        <!-- Header -->
        <div class="flex items-center justify-between mb-5">
          <h2 class="text-lg font-semibold text-gold">Buy AJ with Crypto</h2>
          <button @click="handleClose" class="text-gray-500 hover:text-white text-xl">&times;</button>
        </div>

        <!-- Step 1: Select Pack & Token (before payment created) -->
        <template v-if="!solana.currentPayment">
          <!-- Pack Selection -->
          <div class="mb-4">
            <label class="text-xs text-gray-400 uppercase tracking-wider mb-2 block">Select Pack</label>
            <div class="grid grid-cols-3 gap-2">
              <button
                v-for="pack in packs"
                :key="pack.id"
                @click="selectedPack = pack.id; showCustom = false"
                class="p-3 rounded-lg border text-center transition-all"
                :class="selectedPack === pack.id && !showCustom
                  ? 'border-gold/60 bg-gold/10 text-gold'
                  : 'border-gray-700 hover:border-gray-500 text-gray-300'"
              >
                <div class="text-xs font-medium">{{ pack.label }}</div>
                <div class="text-sm font-bold mt-0.5">{{ pack.aj }} AJ</div>
                <div class="text-[10px] text-gray-500">${{ pack.usd }}</div>
              </button>
            </div>
            <button
              @click="showCustom = !showCustom"
              class="mt-2 text-xs text-gray-500 hover:text-gold transition-colors"
            >
              {{ showCustom ? 'Use packs' : 'Custom amount' }}
            </button>
            <input
              v-if="showCustom"
              v-model.number="customAmount"
              type="number"
              min="1"
              max="1000"
              placeholder="USD amount"
              class="mt-2 w-full bg-black/30 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-gold/40 focus:outline-none"
            />
          </div>

          <!-- Token Selection -->
          <div class="mb-5">
            <label class="text-xs text-gray-400 uppercase tracking-wider mb-2 block">Pay With</label>
            <div class="flex gap-2">
              <button
                v-for="token in ['SOL', 'USDC']"
                :key="token"
                @click="selectedToken = token"
                class="flex-1 py-2 rounded-lg border text-sm font-medium transition-all"
                :class="selectedToken === token
                  ? 'border-gold/60 bg-gold/10 text-gold'
                  : 'border-gray-700 hover:border-gray-500 text-gray-300'"
              >
                {{ token }}
              </button>
            </div>
          </div>

          <!-- Preview -->
          <div class="bg-black/30 rounded-lg p-3 mb-5 border border-gray-800">
            <div class="flex justify-between text-sm">
              <span class="text-gray-400">You pay</span>
              <span class="text-white font-medium">{{ tokenAmount }} {{ selectedToken }}</span>
            </div>
            <div class="flex justify-between text-sm mt-1">
              <span class="text-gray-400">You receive</span>
              <span class="text-gold font-semibold">{{ ajPreview.toLocaleString() }} AJ</span>
            </div>
            <div v-if="solana.solPrice && selectedToken === 'SOL'" class="text-[10px] text-gray-600 mt-1">
              SOL = ${{ solana.solPrice.toFixed(2) }} (cached 5 min)
            </div>
          </div>

          <!-- Pay Button -->
          <button
            @click="startPayment"
            :disabled="solana.isLoading || amountUsd <= 0"
            class="w-full py-3 rounded-lg font-semibold text-sm transition-all"
            :class="solana.isLoading
              ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
              : 'bg-gold/20 border border-gold/40 text-gold hover:bg-gold/30'"
          >
            {{ solana.isLoading ? 'Creating...' : `Pay ${tokenAmount} ${selectedToken}` }}
          </button>

          <p v-if="solana.error" class="mt-2 text-xs text-red-400">{{ solana.error }}</p>
        </template>

        <!-- Step 2: Payment in progress -->
        <template v-else>
          <div class="text-center space-y-4">
            <!-- Status -->
            <div :class="statusColor" class="text-sm font-medium">
              {{ statusLabel }}
            </div>

            <!-- Solana Pay URL (for Phantom deep link) -->
            <template v-if="solana.isPaymentPending">
              <a
                :href="solana.currentPayment.solana_url"
                class="block w-full py-3 rounded-lg bg-purple-900/30 border border-purple-500/30 text-purple-300 text-sm font-medium hover:bg-purple-900/50 transition-all text-center"
              >
                Open in Phantom / Solflare
              </a>

              <!-- QR placeholder (URL for manual wallets) -->
              <div class="bg-black/40 rounded-lg p-4 border border-gray-800">
                <p class="text-xs text-gray-400 mb-2">Or scan / copy this payment URL:</p>
                <div class="bg-black/50 rounded p-2 text-[10px] text-gray-500 break-all font-mono select-all">
                  {{ solana.currentPayment.solana_url }}
                </div>
              </div>

              <!-- Amount summary -->
              <div class="text-sm text-gray-400">
                <span class="text-gold font-semibold">{{ solana.currentPayment.aj_amount?.toLocaleString() }} AJ</span>
                for {{ solana.currentPayment.amount_token?.toFixed(6) }} {{ solana.currentPayment.token }}
              </div>

              <!-- Spinner -->
              <div class="flex justify-center">
                <div class="w-5 h-5 border-2 border-gold/30 border-t-gold rounded-full animate-spin"></div>
              </div>
            </template>

            <!-- Success -->
            <template v-if="solana.isPaymentCredited">
              <div class="text-3xl">&#9670;</div>
              <div class="text-gold text-2xl font-bold">
                +{{ solana.currentPayment.aj_credited?.toLocaleString() }} AJ
              </div>
              <div class="text-xs text-gray-500">
                tx: {{ solana.currentPayment.tx_signature?.slice(0, 16) }}...
              </div>
              <button
                @click="handleClose"
                class="w-full py-2 rounded-lg bg-gold/20 border border-gold/40 text-gold text-sm hover:bg-gold/30 transition-all"
              >
                Done
              </button>
            </template>

            <!-- Expired / Failed -->
            <template v-if="solana.currentPayment?.status === 'expired' || solana.currentPayment?.status === 'failed'">
              <button
                @click="solana.dismiss()"
                class="w-full py-2 rounded-lg border border-gray-700 text-gray-300 text-sm hover:border-gray-500 transition-all"
              >
                Try Again
              </button>
            </template>
          </div>
        </template>
      </div>
    </div>
  </Teleport>
</template>
