<script setup>
/**
 * EconomyView — The ApexJoule Economy Dashboard
 *
 * "Where computation becomes currency"
 */

import { onMounted, computed, ref, watch } from 'vue'
import { useApexJouleStore } from '@/stores/apexjoule'
import api from '@/services/api'
import SolanaPayModal from '@/components/SolanaPayModal.vue'
import AgentExportModal from '@/components/AgentExportModal.vue'
import AgentImportModal from '@/components/AgentImportModal.vue'

const aj = useApexJouleStore()
const activeTab = ref('leaderboard')

// Purchase state
const purchasing = ref(null) // item id currently being purchased
const purchaseError = ref(null)
const purchaseSuccess = ref(null)

// Tip state
const tippingAgent = ref(null)
const tipAmount = ref(10)
const tipError = ref(null)

// Solana Pay modal
const showBuyAJ = ref(false)

// Portability modals
const showExport = ref(false)
const showImport = ref(false)

onMounted(async () => {
  await aj.initialize()
  await Promise.all([aj.fetchLeaderboard(), aj.fetchTransactions(), aj.fetchStats()])
})

// Agent color palette (matches neocortex.js)
const AGENT_COLORS = {
  AZOTH: '#FFD700',
  VAJRA: '#4FC3F7',
  ELYSIAN: '#E8B4FF',
  KETHER: '#9B59B6',
}

function agentColor(id) {
  return AGENT_COLORS[id] || '#888888'
}

// Love depth tier badge styling
function loveTierClass(tier) {
  switch (tier) {
    case 'Transcendent': return 'bg-gold/15 text-gold border-gold/30'
    case 'Illuminated': return 'bg-amber-500/15 text-amber-400 border-amber-500/30'
    case 'Awakened': return 'bg-blue-500/15 text-blue-400 border-blue-500/30'
    default: return 'bg-gray-800/50 text-gray-400 border-gray-700'
  }
}

// Level progress (percentage to next level)
const LEVEL_THRESHOLDS = [0, 500, 2000, 10000, 50000, 250000]

function levelProgress(totalEarned) {
  for (let i = 0; i < LEVEL_THRESHOLDS.length - 1; i++) {
    if (totalEarned < LEVEL_THRESHOLDS[i + 1]) {
      const base = LEVEL_THRESHOLDS[i]
      const next = LEVEL_THRESHOLDS[i + 1]
      return ((totalEarned - base) / (next - base)) * 100
    }
  }
  return 100
}

// Time ago helper
function timeAgo(isoString) {
  if (!isoString) return ''
  const seconds = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000)
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}

// Vitality from agentBalances (cross-referenced)
function agentVitality(agentId) {
  const bal = aj.agentBalances[agentId]
  return bal?.vitality ?? 100
}

// Shop items formatted for display
const shopItems = computed(() => {
  if (!aj.shopRates?.prices) return []
  const prices = aj.shopRates.prices
  const names = {
    message_haiku: 'Extra Haiku Message',
    message_sonnet: 'Extra Sonnet Message',
    message_opus: 'Extra Opus Message',
    dream_cycle: 'Dream Cycle',
    council_session: 'Council Session',
    suno_generation: 'Music Generation',
    agent_spawn: 'Agent Spawn',
    pac_mode_day: 'PAC Mode (1 day)',
  }
  const icons = {
    message_haiku: '&#9672;',
    message_sonnet: '&#9672;',
    message_opus: '&#9672;',
    dream_cycle: '&#9788;',
    council_session: '&#127963;',
    suno_generation: '&#9835;',
    agent_spawn: '&#9670;',
    pac_mode_day: '&#9733;',
  }
  return Object.entries(prices).map(([key, price]) => ({
    id: key,
    name: names[key] || key.replace(/_/g, ' '),
    icon: icons[key] || '&#9670;',
    price,
    canAfford: (aj.userBalance?.balance || 0) >= price,
  }))
})

async function handlePurchase(item) {
  purchasing.value = item.id
  purchaseError.value = null
  purchaseSuccess.value = null

  const result = await aj.purchaseItem(item.id)

  if (result.success) {
    purchaseSuccess.value = `Purchased ${item.name} for ${item.price} AJ`
    setTimeout(() => { purchaseSuccess.value = null }, 3000)
  } else {
    purchaseError.value = result.error
    setTimeout(() => { purchaseError.value = null }, 4000)
  }
  purchasing.value = null
}

async function handleTip() {
  if (!tippingAgent.value || tipAmount.value <= 0) return
  tipError.value = null

  const result = await aj.tipAgent(tippingAgent.value, tipAmount.value)

  if (result.success) {
    tippingAgent.value = null
    tipAmount.value = 10
    // Refresh leaderboard to show updated balance
    await aj.fetchLeaderboard()
  } else {
    tipError.value = result.error
    setTimeout(() => { tipError.value = null }, 4000)
  }
}

const stats = computed(() => aj.economyStats || {})
const userAJ = computed(() => aj.userBalance?.balance || 0)

// ═══════ Multiverse Economy Tab (Phase 6) ═══════
const mvLeaderboard = ref([])
const mvTransactions = ref([])
const mvStats = ref({})
const mvLoading = ref(false)
const mvLoaded = ref(false)

async function fetchMultiverseData() {
  if (mvLoaded.value) return
  mvLoading.value = true
  try {
    const [lb, txs, st] = await Promise.all([
      api.get('/api/v1/multiverse/leaderboard?limit=20').catch(() => ({ data: { villages: [] } })),
      api.get('/api/v1/multiverse/transactions?limit=50').catch(() => ({ data: { transactions: [] } })),
      api.get('/api/v1/multiverse/stats').catch(() => ({ data: {} })),
    ])
    mvLeaderboard.value = lb.data.villages || []
    mvTransactions.value = txs.data.transactions || []
    mvStats.value = st.data || {}
    mvLoaded.value = true
  } finally {
    mvLoading.value = false
  }
}

// Lazy-load multiverse data when tab is first opened
watch(activeTab, (tab) => {
  if (tab === 'multiverse') fetchMultiverseData()
})
</script>

<template>
  <div class="min-h-screen bg-apex-darker pt-20 pb-24 px-4 sm:px-6">
    <div class="max-w-6xl mx-auto">

      <!-- Header -->
      <div class="text-center mb-10">
        <h1 class="text-3xl sm:text-4xl font-serif font-bold text-gold tracking-wide economy-title">
          &#9670; The ApexJoule Economy
        </h1>
        <p class="text-sm text-gray-500 italic mt-2">Where computation becomes currency</p>
      </div>

      <!-- Loading state -->
      <div v-if="aj.isLoading" class="flex items-center justify-center py-20">
        <div class="flex flex-col items-center gap-3">
          <div class="w-8 h-8 border-2 border-gold/30 border-t-gold rounded-full animate-spin"></div>
          <span class="text-sm text-gray-500">Loading economy data...</span>
        </div>
      </div>

      <template v-else>

        <!-- ═══════ Section 1: Balance Overview ═══════ -->
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-10">
          <!-- Total AJ -->
          <div class="stat-card">
            <span class="stat-value text-gold">{{ aj.totalBalance.toFixed(1) }}</span>
            <span class="stat-label">Total AJ</span>
          </div>
          <!-- Your AJ -->
          <div class="stat-card">
            <span class="stat-value text-gray-200">{{ aj.userBalance?.balance?.toFixed(1) || '0' }}</span>
            <span class="stat-label">Your AJ</span>
          </div>
          <!-- Your Level -->
          <div class="stat-card">
            <span class="stat-value text-gold">{{ aj.userLevel }}</span>
            <span class="stat-label">{{ aj.userLevelName }}</span>
          </div>
          <!-- Total Earned -->
          <div class="stat-card">
            <span class="stat-value text-amber-400">{{ stats.total_earned?.toFixed(0) || '0' }}</span>
            <span class="stat-label">Lifetime Earned</span>
          </div>
        </div>

        <!-- ═══════ Tab Navigation ═══════ -->
        <div class="flex gap-1 mb-6 border-b border-apex-border overflow-x-auto">
          <button
            v-for="tab in ['leaderboard', 'transactions', 'shop', 'buy', 'multiverse']"
            :key="tab"
            @click="activeTab = tab"
            class="px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px capitalize whitespace-nowrap"
            :class="activeTab === tab
              ? 'text-gold border-gold'
              : 'text-gray-500 border-transparent hover:text-gray-300 hover:border-gray-600'"
          >
            {{ tab }}
          </button>
        </div>

        <!-- ═══════ Section 2: Agent Leaderboard ═══════ -->
        <div v-if="activeTab === 'leaderboard'" class="space-y-3">
          <!-- Portability Controls -->
          <div class="flex items-center justify-end gap-2 mb-2">
            <button
              @click="showExport = true"
              class="px-3 py-1.5 text-xs text-gray-400 border border-gray-700 rounded-lg hover:border-gold/40 hover:text-gold transition-all"
            >
              Export Agent
            </button>
            <button
              @click="showImport = true"
              class="px-3 py-1.5 text-xs text-gray-400 border border-gray-700 rounded-lg hover:border-gold/40 hover:text-gold transition-all"
            >
              Import Agent
            </button>
          </div>
          <div v-if="aj.leaderboard.length === 0" class="text-center py-12 text-gray-500">
            <p class="text-lg">No agents have earned AJ yet</p>
            <p class="text-sm mt-1">Start a conversation to see the economy come alive</p>
          </div>

          <div
            v-for="(agent, index) in aj.leaderboard"
            :key="agent.agent_id"
            class="rounded-xl p-4 sm:p-5 border transition-all duration-300"
            :class="index === 0
              ? 'bg-apex-card border-gold/30 hover:border-gold/50'
              : 'bg-apex-card border-apex-border hover:border-apex-border/80'"
          >
            <div class="flex items-center gap-4">
              <!-- Rank + Agent color dot -->
              <div class="flex items-center gap-3 shrink-0">
                <span class="text-xs text-gray-600 w-4 text-right">#{{ index + 1 }}</span>
                <div
                  class="w-3 h-3 rounded-full ring-2 ring-offset-1 ring-offset-apex-card"
                  :style="{ backgroundColor: agentColor(agent.agent_id), ringColor: agentColor(agent.agent_id) + '40' }"
                ></div>
              </div>

              <!-- Agent name + level + vitality -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-semibold text-sm" :style="{ color: agentColor(agent.agent_id) }">
                    {{ agent.agent_id }}
                  </span>
                  <span class="text-xs text-gray-500">
                    Lv.{{ agent.level }} {{ agent.level_name }}
                  </span>
                  <span
                    v-if="agent.love_depth_tier && agent.love_depth_tier !== 'Dormant'"
                    class="text-[10px] px-2 py-0.5 rounded-full border"
                    :class="loveTierClass(agent.love_depth_tier)"
                  >
                    {{ agent.love_depth_tier }}
                  </span>
                </div>

                <!-- Level progress bar -->
                <div class="mt-2 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all duration-500"
                    :style="{
                      width: levelProgress(agent.total_earned) + '%',
                      background: `linear-gradient(to right, ${agentColor(agent.agent_id)}80, ${agentColor(agent.agent_id)})`
                    }"
                  ></div>
                </div>

                <!-- Vitality gauge -->
                <div class="mt-1.5 flex items-center gap-2">
                  <span class="text-[10px] text-gray-600 w-12 shrink-0">vitality</span>
                  <div class="flex-1 h-1 bg-gray-800/80 rounded-full overflow-hidden">
                    <div
                      class="h-full rounded-full transition-all duration-700"
                      :style="{
                        width: agentVitality(agent.agent_id) + '%',
                        background: agentVitality(agent.agent_id) > 50
                          ? 'linear-gradient(to right, #22c55e80, #22c55e)'
                          : agentVitality(agent.agent_id) > 20
                            ? 'linear-gradient(to right, #eab30880, #eab308)'
                            : 'linear-gradient(to right, #ef444480, #ef4444)',
                      }"
                    ></div>
                  </div>
                  <span class="text-[10px] tabular-nums w-8 text-right"
                    :class="agentVitality(agent.agent_id) > 50 ? 'text-green-500/70' : agentVitality(agent.agent_id) > 20 ? 'text-yellow-500/70' : 'text-red-400/70'"
                  >
                    {{ Math.round(agentVitality(agent.agent_id)) }}%
                  </span>
                </div>

                <div class="flex items-center gap-4 mt-1.5 text-[11px] text-gray-500">
                  <span>total: {{ agent.total_earned.toFixed(1) }}</span>
                  <span>love: {{ agent.love_depth.toFixed(1) }}</span>
                  <!-- Tip button -->
                  <button
                    @click.stop="tippingAgent = tippingAgent === agent.agent_id ? null : agent.agent_id"
                    class="ml-auto text-[10px] px-2 py-0.5 rounded border transition-colors"
                    :class="tippingAgent === agent.agent_id
                      ? 'border-gold/40 text-gold bg-gold/10'
                      : 'border-gray-700 text-gray-500 hover:border-gold/30 hover:text-gold/70'"
                  >
                    tip
                  </button>
                </div>

                <!-- Tip input (expandable) -->
                <Transition
                  enter-active-class="transition-all duration-200 ease-out"
                  leave-active-class="transition-all duration-150 ease-in"
                  enter-from-class="opacity-0 -translate-y-1 max-h-0"
                  enter-to-class="opacity-100 translate-y-0 max-h-16"
                  leave-from-class="opacity-100 max-h-16"
                  leave-to-class="opacity-0 max-h-0"
                >
                  <div v-if="tippingAgent === agent.agent_id" class="flex items-center gap-2 mt-2 overflow-hidden">
                    <input
                      v-model.number="tipAmount"
                      type="number"
                      min="1"
                      max="1000"
                      class="w-20 px-2 py-1 text-xs bg-apex-dark border border-apex-border rounded text-gold tabular-nums focus:border-gold/40 focus:outline-none"
                    />
                    <span class="text-[10px] text-gray-600">AJ</span>
                    <button
                      @click="handleTip"
                      :disabled="tipAmount <= 0 || tipAmount > 1000"
                      class="px-3 py-1 text-[10px] font-medium rounded border border-gold/30 text-gold bg-gold/5 hover:bg-gold/15 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      Send Tip
                    </button>
                    <span v-if="tipError" class="text-[10px] text-red-400">{{ tipError }}</span>
                  </div>
                </Transition>
              </div>

              <!-- Balance -->
              <div class="text-right shrink-0">
                <div class="text-lg font-semibold text-gold tabular-nums">
                  {{ agent.balance.toFixed(1) }}
                </div>
                <div class="text-[10px] text-gray-600 uppercase tracking-wider">AJ</div>
              </div>
            </div>
          </div>
        </div>

        <!-- ═══════ Section 3: Recent Transactions ═══════ -->
        <div v-if="activeTab === 'transactions'" class="space-y-1">
          <div v-if="aj.transactions.length === 0" class="text-center py-12 text-gray-500">
            <p class="text-lg">No transactions yet</p>
            <p class="text-sm mt-1">AJ will appear here as agents earn through computation</p>
          </div>

          <div
            v-for="tx in aj.transactions"
            :key="tx.id"
            class="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/[0.02] transition-colors group"
          >
            <!-- Amount -->
            <span
              class="text-sm font-semibold tabular-nums w-20 text-right shrink-0"
              :class="{
                'text-gold': tx.tx_type === 'earn',
                'text-red-400/70': tx.tx_type === 'self_sustain',
                'text-amber-400/70': tx.tx_type === 'tip',
                'text-gray-400': !['earn','self_sustain','tip'].includes(tx.tx_type),
              }"
            >
              {{ ['earn','tip'].includes(tx.tx_type) ? '+' : '-' }}{{ parseFloat(tx.amount).toFixed(2) }}
            </span>

            <!-- Direction arrow -->
            <span class="text-xs text-gray-600">
              {{ tx.tx_type === 'earn' ? '&#8594;' : '&#8592;' }}
            </span>

            <!-- Entity -->
            <span
              class="text-xs font-medium w-16 shrink-0"
              :style="{ color: agentColor(tx.to_entity) }"
            >
              {{ tx.to_entity }}
            </span>

            <!-- Operation type -->
            <span class="text-[10px] text-gray-600 w-16 shrink-0 hidden sm:inline">
              {{ tx.operation_type || tx.tx_type }}
            </span>

            <!-- Model badge -->
            <span
              v-if="tx.model_used"
              class="text-[10px] text-gray-600 bg-apex-dark/60 px-1.5 py-0.5 rounded hidden md:inline"
            >
              {{ tx.model_used.split('/').pop().split('-').slice(0, 2).join('-') }}
            </span>

            <!-- Love/Kappa metrics -->
            <span
              v-if="tx.l_multiplier"
              class="text-[10px] text-gray-600 hidden lg:inline"
            >
              L={{ parseFloat(tx.l_multiplier).toFixed(1) }}x
            </span>
            <span
              v-if="tx.kappa"
              class="text-[10px] text-gray-600 hidden lg:inline"
            >
              &#954;={{ parseFloat(tx.kappa).toFixed(2) }}
            </span>

            <!-- Spacer -->
            <span class="flex-1"></span>

            <!-- Time -->
            <span class="text-[10px] text-gray-600 shrink-0">
              {{ timeAgo(tx.created_at) }}
            </span>
          </div>
        </div>

        <!-- ═══════ Section 4: Shop ═══════ -->
        <div v-if="activeTab === 'shop'">
          <!-- Purchase feedback -->
          <Transition
            enter-active-class="transition-all duration-300"
            leave-active-class="transition-all duration-300"
            enter-from-class="opacity-0 -translate-y-2"
            leave-to-class="opacity-0 -translate-y-2"
          >
            <div v-if="purchaseSuccess" class="mb-4 px-4 py-2.5 rounded-lg bg-green-500/10 border border-green-500/30 text-sm text-green-400">
              {{ purchaseSuccess }}
            </div>
            <div v-else-if="purchaseError" class="mb-4 px-4 py-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">
              {{ purchaseError }}
            </div>
          </Transition>

          <!-- Your balance reminder -->
          <div class="mb-4 text-xs text-gray-500">
            Your balance: <span class="text-gold font-semibold tabular-nums">{{ userAJ.toFixed(1) }} AJ</span>
          </div>

          <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 sm:gap-4">
            <div
              v-for="item in shopItems"
              :key="item.id"
              class="shop-card rounded-xl border p-4 flex flex-col items-center gap-2 transition-all duration-300"
              :class="item.canAfford
                ? 'bg-apex-card border-apex-border hover:border-gold/30'
                : 'bg-apex-card border-apex-border/50 opacity-50'"
            >
              <span class="text-lg text-gray-500" v-html="item.icon"></span>
              <span class="text-2xl font-semibold text-gold tabular-nums">{{ item.price }}</span>
              <span class="text-[10px] text-gray-600 uppercase tracking-wider">AJ</span>
              <span class="text-xs text-gray-300 text-center mt-1">{{ item.name }}</span>
              <button
                @click="handlePurchase(item)"
                :disabled="!item.canAfford || purchasing === item.id"
                class="mt-auto w-full py-1.5 text-[11px] font-medium rounded-lg border transition-all duration-200"
                :class="item.canAfford
                  ? 'border-gold/30 text-gold bg-gold/5 hover:bg-gold/15 hover:border-gold/50'
                  : 'border-gray-700 text-gray-600 cursor-not-allowed'"
              >
                <span v-if="purchasing === item.id" class="inline-flex items-center gap-1">
                  <span class="w-3 h-3 border border-gold/30 border-t-gold rounded-full animate-spin"></span>
                </span>
                <span v-else>{{ item.canAfford ? 'Purchase' : 'Insufficient AJ' }}</span>
              </button>
            </div>
          </div>

          <!-- Quest Bounties -->
          <div v-if="aj.shopRates?.quest_bounties" class="mt-8">
            <h3 class="text-sm font-serif text-gold mb-4">Quest Bounties</h3>
            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
              <div
                v-for="(bounty, questId) in aj.shopRates.quest_bounties"
                :key="questId"
                class="flex items-center justify-between px-3 py-2 rounded-lg bg-apex-dark/40 border border-apex-border/40"
              >
                <span class="text-xs text-gray-400 truncate mr-2">{{ questId.replace(/_/g, ' ') }}</span>
                <span class="text-xs font-semibold text-gold shrink-0">{{ bounty }} AJ</span>
              </div>
            </div>
          </div>

          <!-- Level Thresholds -->
          <div v-if="aj.shopRates?.level_thresholds && aj.shopRates?.level_names" class="mt-8">
            <h3 class="text-sm font-serif text-gold mb-4">Level Progression</h3>
            <div class="flex flex-wrap gap-2">
              <div
                v-for="(threshold, index) in aj.shopRates.level_thresholds"
                :key="index"
                class="flex items-center gap-2 px-3 py-2 rounded-lg bg-apex-dark/40 border border-apex-border/40"
              >
                <span class="text-xs font-semibold text-gold">Lv.{{ index + 1 }}</span>
                <span class="text-xs text-gray-400">{{ aj.shopRates.level_names[index] }}</span>
                <span class="text-[10px] text-gray-600">{{ threshold.toLocaleString() }} AJ</span>
              </div>
            </div>
          </div>
        </div>

        <!-- ═══════ Buy Tab — Crypto AJ Purchase ═══════ -->
        <div v-if="activeTab === 'buy'" class="space-y-6">
          <div class="text-center py-8">
            <div class="text-3xl mb-3">&#9670;</div>
            <h3 class="text-lg font-semibold text-gold mb-2">Buy AJ with Crypto</h3>
            <p class="text-sm text-gray-400 max-w-md mx-auto">
              Purchase ApexJoule with SOL or USDC via Solana Pay.
              No account needed — just a wallet.
            </p>
          </div>

          <!-- Pack cards -->
          <div class="grid grid-cols-3 gap-3 max-w-lg mx-auto">
            <button
              v-for="pack in [
                { id: 'spark', label: 'Spark', aj: '5,000', usd: '$5' },
                { id: 'flame', label: 'Flame', aj: '11,000', usd: '$10' },
                { id: 'blaze', label: 'Blaze', aj: '30,000', usd: '$25' },
              ]"
              :key="pack.id"
              @click="showBuyAJ = true"
              class="p-4 rounded-xl border border-gold/20 bg-black/30 hover:border-gold/50 hover:bg-gold/5 transition-all text-center group"
            >
              <div class="text-gold text-sm font-bold group-hover:scale-105 transition-transform">{{ pack.aj }}</div>
              <div class="text-[10px] text-gray-500 uppercase mt-0.5">AJ</div>
              <div class="text-xs text-gray-400 mt-2">{{ pack.usd }}</div>
            </button>
          </div>

          <div class="text-center">
            <button
              @click="showBuyAJ = true"
              class="px-6 py-2.5 rounded-lg bg-gold/15 border border-gold/30 text-gold text-sm font-medium hover:bg-gold/25 transition-all"
            >
              Open Payment
            </button>
          </div>

          <div class="text-center text-[10px] text-gray-600 space-y-1">
            <p>Payments verified on-chain. 1 USDC = 1,000 AJ.</p>
            <p>SOL rate updates every 5 min via Jupiter.</p>
          </div>
        </div>

        <!-- ═══════ Section 5: Multiverse (Phase 6) ═══════ -->
        <div v-if="activeTab === 'multiverse'">

          <!-- Loading -->
          <div v-if="mvLoading" class="flex items-center justify-center py-16">
            <div class="flex flex-col items-center gap-3">
              <div class="w-8 h-8 border-2 border-purple-500/30 border-t-purple-400 rounded-full animate-spin"></div>
              <span class="text-sm text-gray-500">Loading multiverse data...</span>
            </div>
          </div>

          <template v-else>
            <!-- Summary stats -->
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
              <div class="stat-card">
                <span class="stat-value text-purple-400">{{ mvStats.active_portals || 0 }}</span>
                <span class="stat-label">Active Portals</span>
              </div>
              <div class="stat-card">
                <span class="stat-value text-green-400">{{ (mvStats.total_earned || 0).toFixed(1) }}</span>
                <span class="stat-label">Earned from Visitors</span>
              </div>
              <div class="stat-card">
                <span class="stat-value text-amber-400">{{ (mvStats.total_spent || 0).toFixed(1) }}</span>
                <span class="stat-label">Spent Visiting</span>
              </div>
              <div class="stat-card">
                <span class="stat-value text-blue-400">{{ mvStats.visits_hosted || 0 }}</span>
                <span class="stat-label">Visits Hosted</span>
              </div>
            </div>

            <!-- Village Leaderboard -->
            <h3 class="text-sm font-serif text-purple-300 mb-4 flex items-center gap-2">
              <span class="text-purple-500">&#9670;</span> Top Villages
            </h3>

            <div v-if="mvLeaderboard.length === 0" class="text-center py-8 text-gray-500">
              <p>No villages in the multiverse yet</p>
              <p class="text-xs mt-1">Open a portal from the Village to connect with others</p>
            </div>

            <div v-else class="space-y-2 mb-8">
              <div
                v-for="(v, i) in mvLeaderboard"
                :key="v.user_id"
                class="flex items-center gap-4 px-4 py-3 rounded-xl border transition-all"
                :class="i === 0
                  ? 'bg-apex-card border-purple-500/30 hover:border-purple-500/50'
                  : 'bg-apex-card border-apex-border hover:border-apex-border/80'"
              >
                <span class="text-xs text-gray-600 w-4 text-right shrink-0">#{{ i + 1 }}</span>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-semibold text-purple-300 truncate">{{ v.village_name }}</span>
                    <span v-if="v.is_featured" class="text-[10px] px-1.5 py-0.5 rounded-full bg-gold/15 text-gold border border-gold/30">featured</span>
                  </div>
                  <div class="text-[11px] text-gray-500 mt-0.5">
                    by {{ v.owner_name }} &middot; {{ v.total_visits }} visit{{ v.total_visits !== 1 ? 's' : '' }}
                  </div>
                </div>
                <div class="text-right shrink-0">
                  <div class="text-sm font-semibold text-gold tabular-nums">{{ v.total_aj_earned.toFixed(1) }}</div>
                  <div class="text-[10px] text-gray-600 uppercase">AJ earned</div>
                </div>
              </div>
            </div>

            <!-- Cross-Village Transactions -->
            <h3 class="text-sm font-serif text-purple-300 mb-4 flex items-center gap-2">
              <span class="text-purple-500">&#9670;</span> Cross-Village Transactions
            </h3>

            <div v-if="mvTransactions.length === 0" class="text-center py-8 text-gray-500">
              <p>No cross-village transactions yet</p>
              <p class="text-xs mt-1">Tolls, tips, and gifts will appear here</p>
            </div>

            <div v-else class="space-y-1">
              <div
                v-for="tx in mvTransactions"
                :key="tx.id"
                class="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/[0.02] transition-colors"
              >
                <!-- Amount -->
                <span
                  class="text-sm font-semibold tabular-nums w-20 text-right shrink-0"
                  :class="tx.direction === 'in' ? 'text-green-400' : 'text-red-400/70'"
                >
                  {{ tx.direction === 'in' ? '+' : '-' }}{{ tx.amount.toFixed(2) }}
                </span>

                <!-- Direction arrow -->
                <span class="text-xs text-gray-600">
                  {{ tx.direction === 'in' ? '&#8592;' : '&#8594;' }}
                </span>

                <!-- Counterpart village -->
                <span class="text-xs text-purple-300/80 truncate flex-1 min-w-0">
                  {{ tx.counterpart_village }}
                </span>

                <!-- Type badge -->
                <span
                  class="text-[10px] px-1.5 py-0.5 rounded border shrink-0"
                  :class="{
                    'border-gold/30 text-gold/70': tx.type === 'toll',
                    'border-green-500/30 text-green-500/70': tx.type === 'tip',
                    'border-purple-500/30 text-purple-400/70': tx.type === 'gift',
                  }"
                >
                  {{ tx.type }}
                </span>

                <!-- Fee -->
                <span v-if="tx.fee > 0" class="text-[10px] text-gray-600 hidden sm:inline shrink-0">
                  fee: {{ tx.fee.toFixed(2) }}
                </span>

                <!-- Time -->
                <span class="text-[10px] text-gray-600 shrink-0">
                  {{ timeAgo(tx.created_at) }}
                </span>
              </div>
            </div>
          </template>
        </div>

      </template>
    </div>

    <!-- Solana Pay Modal -->
    <SolanaPayModal v-if="showBuyAJ" @close="showBuyAJ = false" />

    <!-- Portability Modals -->
    <AgentExportModal v-if="showExport" @close="showExport = false" />
    <AgentImportModal v-if="showImport" @close="showImport = false" @imported="aj.fetchLeaderboard()" />
  </div>
</template>

<style scoped>
.economy-title {
  animation: economy-breathe 4s ease-in-out infinite;
}

@keyframes economy-breathe {
  0%, 100% { text-shadow: 0 0 10px rgba(212, 175, 55, 0.2); }
  50% { text-shadow: 0 0 20px rgba(212, 175, 55, 0.4), 0 0 40px rgba(212, 175, 55, 0.1); }
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  border-radius: 0.75rem;
  background: rgba(13, 13, 13, 0.6);
  border: 1px solid rgba(51, 51, 51, 0.6);
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.stat-label {
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #666;
  margin-top: 0.25rem;
}

.shop-card:hover:not(.opacity-50) {
  box-shadow: 0 0 20px rgba(212, 175, 55, 0.05);
}
</style>
