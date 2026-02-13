<script setup>
/**
 * AchievementsView - The Trophy Case
 *
 * Showcases all 35 achievements (10 E5 Village + 25 Quest milestones).
 * Cards grouped by stage path, locked/unlocked visuals, overall progress bar.
 *
 * "Where every achievement becomes a trophy, and every trophy tells a story."
 */

import { ref, computed, onMounted } from 'vue'
import { useVillageGamification, ACHIEVEMENTS } from '@/composables/useVillageGamification'

const {
  stats,
  questProgress,
  questLoading,
  fetchQuestProgress,
} = useVillageGamification()

// --- Full Quest Milestone Catalog (25 milestones across 4 stages) ---

const QUEST_MILESTONES = [
  // Seeker Path (8)
  { id: 'first_chat', name: 'First Steps', description: 'Send your first message to any agent', feature: 'basic_chat', stage: 'seeker' },
  { id: 'meet_agents', name: 'Meet the Council', description: 'Chat with 2 different agents', feature: 'all_agents', stage: 'seeker' },
  { id: 'zone_visit', name: 'Village Explorer', description: 'Complete a task at any Village zone', feature: 'village_tasks', stage: 'seeker' },
  { id: 'web_search', name: 'Knowledge Seeker', description: 'Use web search via the Library zone', feature: 'web_search', stage: 'seeker' },
  { id: 'file_upload', name: 'Archivist', description: 'Upload a file in a task dialog', feature: 'file_vault', stage: 'seeker' },
  { id: 'three_zones', name: 'Pathfinder', description: 'Complete tasks at 3 different zones', feature: 'tool_categories', stage: 'seeker' },
  { id: 'council_first', name: 'Council Convened', description: 'Run a Council deliberation', feature: 'multi_agent', stage: 'seeker' },
  { id: 'seeker_mastery', name: 'Seeker Mastery', description: 'Complete 15 total tasks', feature: 'full_seeker', stage: 'seeker' },
  // Adept Path (8)
  { id: 'music_gen', name: 'First Composition', description: 'Generate a music track at the DJ Booth', feature: 'music_gen', stage: 'adept' },
  { id: 'memory_store', name: 'Memory Keeper', description: 'Store a memory at the Memory Garden', feature: 'memory_system', stage: 'adept' },
  { id: 'bridge_connect', name: 'Bridge Builder', description: 'Use an external API via Bridge Portal', feature: 'external_integrations', stage: 'adept' },
  { id: 'agent_level_3', name: 'Agent Trainer', description: 'Get any agent to level 3', feature: 'agent_customization', stage: 'adept' },
  { id: 'opus_model', name: 'Opus Ascension', description: 'Use an Opus-tier model', feature: 'opus_model_limited', stage: 'adept' },
  { id: 'zone_master', name: 'Zone Specialist', description: 'Complete 10 tasks at one zone', feature: 'zone_specialization', stage: 'adept' },
  { id: 'council_expert', name: 'Council Expert', description: 'Run 5 Council sessions', feature: 'advanced_council', stage: 'adept' },
  { id: 'adept_mastery', name: 'Adept Mastery', description: 'Complete 50 total tasks', feature: 'full_adept', stage: 'adept' },
  // Opus Path (5)
  { id: 'dream_engine', name: 'Dream Walker', description: 'First Dream Engine session', feature: 'dream_engine', stage: 'opus' },
  { id: 'nursery_train', name: 'Model Alchemist', description: 'Train a custom model in the Nursery', feature: 'model_training', stage: 'opus' },
  { id: 'all_zones', name: 'Cartographer', description: 'Complete tasks in all 8 zones', feature: 'full_zone_mastery', stage: 'opus' },
  { id: 'agent_level_7', name: 'Agent Master', description: 'Get any agent to level 7', feature: 'enhanced_agents', stage: 'opus' },
  { id: 'full_opus', name: 'Opus Mastery', description: '100 total tasks + all prior milestones', feature: 'full_opus', stage: 'opus' },
  // Azothic Path (4)
  { id: 'all_agents_5', name: 'The Full House', description: 'All 4 agents at level 5+', feature: 'pac_mode', stage: 'azothic' },
  { id: 'council_master', name: 'Grand Council', description: '20 Council sessions', feature: 'unlimited_council', stage: 'azothic' },
  { id: 'athanor_complete', name: 'The Great Work', description: '200 total tasks + all achievements', feature: 'full_azothic', stage: 'azothic' },
  { id: 'sensorhead_earned', name: 'Azothic Alchemist', description: 'Complete the Azothic quest', feature: 'sensorhead_prize', stage: 'azothic' },
]

// --- Stage config ---

const STAGE_CONFIG = {
  seeker: { symbol: '\u2697', name: 'Seeker Path', color: '#9CA3AF', accent: 'gray' },
  adept: { symbol: '\u26A1', name: 'Adept Path', color: '#60A5FA', accent: 'blue' },
  opus: { symbol: '\u2726', name: 'Opus Path', color: '#A78BFA', accent: 'purple' },
  azothic: { symbol: '\u2234', name: 'Azothic Path', color: '#FFD700', accent: 'amber' },
  village: { symbol: '\u2694', name: 'Village Mastery', color: '#F59E0B', accent: 'amber' },
}

// --- Unified achievement list ---

const allAchievements = computed(() => {
  const unlocked = new Set(questProgress.features_unlocked || [])
  const earnedE5 = new Set(stats.achievements || [])
  const isQuest = questProgress.quest_active

  const items = []

  // Quest milestones (25)
  for (const m of QUEST_MILESTONES) {
    items.push({
      id: m.id,
      name: m.name,
      description: m.description,
      stage: m.stage,
      feature: m.feature,
      type: 'quest',
      unlocked: unlocked.has(m.feature),
      visible: isQuest, // Only show quest milestones to quest users
    })
  }

  // E5 Village achievements (10)
  for (const ach of ACHIEVEMENTS) {
    items.push({
      id: ach.id,
      name: ach.name,
      description: ach.description,
      stage: 'village',
      feature: null,
      type: 'e5',
      unlocked: earnedE5.has(ach.id),
      visible: true, // Everyone can see Village Mastery
    })
  }

  return items.filter(a => a.visible)
})

// --- Grouped by stage ---

const groupedAchievements = computed(() => {
  const groups = []
  const stageOrder = questProgress.quest_active
    ? ['seeker', 'adept', 'opus', 'azothic', 'village']
    : ['village']

  for (const stage of stageOrder) {
    const items = allAchievements.value.filter(a => a.stage === stage)
    if (items.length === 0) continue
    const config = STAGE_CONFIG[stage]
    const earned = items.filter(a => a.unlocked).length
    groups.push({
      stage,
      ...config,
      items,
      earned,
      total: items.length,
    })
  }
  return groups
})

// --- Progress stats ---

const totalEarned = computed(() => allAchievements.value.filter(a => a.unlocked).length)
const totalCount = computed(() => allAchievements.value.length)
const progressPercent = computed(() =>
  totalCount.value > 0 ? Math.round((totalEarned.value / totalCount.value) * 100) : 0
)

// --- Fetch data on mount ---

onMounted(() => {
  fetchQuestProgress()
})
</script>

<template>
  <div class="min-h-screen bg-apex-dark pt-20 pb-12 px-4">
    <div class="max-w-5xl mx-auto">

      <!-- Header -->
      <div class="text-center mb-10">
        <h1 class="text-3xl font-serif font-bold text-gold mb-2">Achievement Gallery</h1>
        <p class="text-gray-400 text-sm">Every milestone tells a story</p>
      </div>

      <!-- Loading -->
      <div v-if="questLoading" class="text-center py-12">
        <div class="inline-block w-6 h-6 border-2 border-gold/30 border-t-gold rounded-full animate-spin" />
        <p class="text-gray-400 text-sm mt-3">Loading achievements...</p>
      </div>

      <template v-else>
        <!-- Overall Progress Bar -->
        <div class="mb-10 bg-white/5 rounded-xl p-5 border border-apex-border">
          <div class="flex items-center justify-between mb-3">
            <span class="text-white font-medium">{{ totalEarned }}/{{ totalCount }} Achievements</span>
            <span class="text-gold font-bold text-lg">{{ progressPercent }}%</span>
          </div>
          <div class="h-3 bg-white/10 rounded-full overflow-hidden">
            <div
              class="h-full bg-gradient-to-r from-amber-600 to-gold rounded-full transition-all duration-700"
              :style="{ width: progressPercent + '%' }"
            />
          </div>
        </div>

        <!-- Stage Groups -->
        <div v-for="group in groupedAchievements" :key="group.stage" class="mb-10">
          <!-- Stage Header -->
          <div class="flex items-center gap-3 mb-5">
            <span class="text-2xl" :style="{ color: group.color }">{{ group.symbol }}</span>
            <h2 class="text-xl font-bold text-white">{{ group.name }}</h2>
            <span class="text-sm text-gray-400 ml-auto">{{ group.earned }}/{{ group.total }}</span>
          </div>

          <!-- Card Grid -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            <div
              v-for="ach in group.items"
              :key="ach.id"
              class="achievement-card rounded-xl p-4 border transition-all duration-300"
              :class="ach.unlocked
                ? 'bg-white/5 border-gold/30 hover:border-gold/60 hover:shadow-lg hover:shadow-gold/5'
                : 'bg-white/[0.02] border-white/5 opacity-50'"
            >
              <!-- Card Header -->
              <div class="flex items-start justify-between mb-3">
                <div
                  class="w-10 h-10 rounded-lg flex items-center justify-center text-lg"
                  :class="ach.unlocked ? 'bg-gold/15' : 'bg-white/5'"
                >
                  <span v-if="ach.unlocked" class="text-gold">&#10003;</span>
                  <span v-else class="text-gray-600">&#128274;</span>
                </div>
                <span
                  v-if="ach.type === 'quest'"
                  class="text-[10px] px-2 py-0.5 rounded-full font-medium"
                  :style="{
                    backgroundColor: STAGE_CONFIG[ach.stage]?.color + '15',
                    color: STAGE_CONFIG[ach.stage]?.color,
                  }"
                >
                  {{ STAGE_CONFIG[ach.stage]?.name?.replace(' Path', '') }}
                </span>
                <span
                  v-else
                  class="text-[10px] px-2 py-0.5 rounded-full font-medium bg-amber-500/10 text-amber-400"
                >
                  Village
                </span>
              </div>

              <!-- Name -->
              <h3
                class="font-semibold mb-1 text-sm"
                :class="ach.unlocked ? 'text-white' : 'text-gray-500'"
              >
                {{ ach.name }}
              </h3>

              <!-- Description -->
              <p class="text-xs text-gray-500 leading-relaxed">{{ ach.description }}</p>

              <!-- Feature unlocked badge (quest milestones only) -->
              <div
                v-if="ach.feature && ach.unlocked"
                class="mt-3 text-[10px] text-gold/70 flex items-center gap-1"
              >
                <span>&#9889;</span>
                <span>{{ ach.feature.replace(/_/g, ' ') }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Empty state for non-quest users with no E5 achievements -->
        <div v-if="totalCount === 0" class="text-center py-16">
          <div class="text-4xl mb-4">&#127942;</div>
          <h3 class="text-xl font-bold text-white mb-2">No achievements yet</h3>
          <p class="text-gray-400">Complete tasks in the Village to earn achievements!</p>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.achievement-card {
  backdrop-filter: blur(8px);
}

.achievement-card:hover {
  transform: translateY(-1px);
}
</style>
