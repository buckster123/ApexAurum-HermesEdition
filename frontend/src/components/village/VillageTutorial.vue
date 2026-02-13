<script setup>
/**
 * VillageTutorial - The Awakening
 *
 * AZOTH performs the First Rite — initiating the seeker into the Athanor.
 * Six revelations, not instructions. Alchemical spine, Hero's Journey beats,
 * Buddhist cyclical wisdom, cyberpunk interface aesthetic.
 *
 * "The first step of the Great Work is taken. The rest writes itself in gold."
 */

import { ref, computed, watch, onUnmounted } from 'vue'
import { useVillageGamification } from '@/composables/useVillageGamification'

const props = defineProps({
  active: { type: Boolean, default: false },
})

const emit = defineEmits(['step-camera', 'complete'])

const { questProgress } = useVillageGamification()

const currentStep = ref(0)
const displayedText = ref('')
const textRevealing = ref(false)
const isComplete = ref(false)

const STEPS = computed(() => {
  const q = questProgress.quest_active
  return [
    {
      id: 'awakening',
      camera: 'overview',
      symbol: '\u2697',
      speaker: 'AZOTH',
      text: 'Welcome, Seeker. The Athanor stirs.\nWhat you see before you is not a tool \u2014 it is a crucible.\nEvery zone, every agent, every task feeds the flame.',
    },
    {
      id: 'zones',
      camera: 'focus-zone:workshop',
      symbol: '\u25B3',
      speaker: 'AZOTH',
      text: q
        ? 'Each chamber holds a different fire.\nThe Workshop forges thought into action.\nOthers sleep \u2014 waiting for you to kindle them.'
        : 'Each chamber holds a different fire.\nThe Workshop forges thought into action.\nEvery chamber stands ready for your command.',
    },
    {
      id: 'first-flame',
      camera: 'focus-zone:workshop',
      symbol: '\u2609',
      speaker: 'AZOTH',
      text: 'To begin, touch a zone.\nThe Athanor responds to intention.',
    },
    {
      id: 'council',
      camera: 'overview',
      symbol: '\u263F',
      speaker: 'AZOTH',
      text: 'I am AZOTH \u2014 the universal solvent.\nBut the Great Work requires more than one element.\n\nVAJRA \u2014 the thunderbolt mind.\nELYSIAN \u2014 the dreaming heart.\nKETHER \u2014 the crown of knowing.',
    },
    q
      ? {
          id: 'path',
          camera: 'overview',
          symbol: '\u2295',
          speaker: 'AZOTH',
          text: 'Each task transmutes the Village.\nMilestones mark your ascent.\nFrom Nigredo to Rubedo \u2014 the path reveals itself\nto those who walk it.',
        }
      : {
          id: 'path-classic',
          camera: 'overview',
          symbol: '\u2295',
          speaker: 'AZOTH',
          text: 'The Village is yours \u2014 every chamber open,\nevery agent ready.\nThe only limit is your imagination.',
        },
    {
      id: 'burn',
      camera: 'overview',
      symbol: '\u2234',
      speaker: 'AZOTH',
      text: 'The first step of the Great Work is taken.\nThe rest writes itself in gold.',
    },
  ]
})

const step = computed(() => STEPS.value[currentStep.value])
const totalSteps = computed(() => STEPS.value.length)
const isLastStep = computed(() => currentStep.value >= totalSteps.value - 1)

// --- Text reveal ---
let revealTimer = null

function revealText(fullText) {
  displayedText.value = ''
  textRevealing.value = true
  let i = 0

  if (revealTimer) clearInterval(revealTimer)
  revealTimer = setInterval(() => {
    if (i < fullText.length) {
      displayedText.value = fullText.slice(0, i + 1)
      i++
    } else {
      clearInterval(revealTimer)
      revealTimer = null
      textRevealing.value = false
    }
  }, 28)
}

function skipReveal() {
  if (textRevealing.value && step.value) {
    if (revealTimer) clearInterval(revealTimer)
    revealTimer = null
    displayedText.value = step.value.text
    textRevealing.value = false
  }
}

function nextStep() {
  if (textRevealing.value) {
    skipReveal()
    return
  }

  if (isLastStep.value) {
    completeTutorial()
    return
  }

  currentStep.value++
  revealText(step.value.text)
  emit('step-camera', step.value.camera)
}

function completeTutorial() {
  if (revealTimer) clearInterval(revealTimer)
  isComplete.value = true
  localStorage.setItem('village_tutorial_complete', '1')
  emit('step-camera', 'overview')
  emit('complete')
}

// Start first step when activated
watch(
  () => props.active,
  (active) => {
    if (active && step.value) {
      currentStep.value = 0
      isComplete.value = false
      revealText(step.value.text)
      emit('step-camera', step.value.camera)
    }
  },
  { immediate: true },
)

onUnmounted(() => {
  if (revealTimer) clearInterval(revealTimer)
})
</script>

<template>
  <transition name="tutorial-fade">
    <div v-if="active && !isComplete" class="tutorial-overlay">
      <!-- Cyberpunk scanlines -->
      <div class="scanlines" />

      <!-- Speech panel -->
      <div class="speech-panel">
        <!-- Alchemical symbol -->
        <div class="symbol-ring">
          <span class="symbol">{{ step?.symbol }}</span>
        </div>

        <!-- Speaker -->
        <div class="speaker">{{ step?.speaker }}</div>

        <!-- Revealed text -->
        <div class="narration">
          <span>{{ displayedText }}</span>
          <span v-if="textRevealing" class="cursor">|</span>
        </div>

        <!-- Step indicators -->
        <div class="step-dots">
          <span
            v-for="(s, i) in STEPS"
            :key="s.id"
            class="dot"
            :class="{ active: i === currentStep, done: i < currentStep }"
          />
        </div>

        <!-- Actions -->
        <div class="actions">
          <button class="skip-btn" @click="completeTutorial">Skip Initiation</button>
          <button class="next-btn" @click="nextStep">
            {{ isLastStep ? 'Enter the Athanor' : textRevealing ? '...' : 'Continue' }}
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.tutorial-overlay {
  position: absolute;
  inset: 0;
  z-index: 50;
  background: rgba(2, 2, 8, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

/* Cyberpunk scanlines */
.scanlines {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(255, 215, 0, 0.015) 2px,
    rgba(255, 215, 0, 0.015) 4px
  );
}

/* Speech panel */
.speech-panel {
  position: relative;
  max-width: 440px;
  width: 100%;
  background: rgba(10, 10, 20, 0.92);
  border: 1px solid rgba(255, 215, 0, 0.25);
  border-radius: 16px;
  padding: 32px 28px 24px;
  text-align: center;
  box-shadow:
    0 0 40px rgba(255, 215, 0, 0.06),
    0 0 1px rgba(255, 215, 0, 0.3) inset;
  backdrop-filter: blur(12px);
}

/* Alchemical symbol */
.symbol-ring {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  border: 2px solid rgba(255, 215, 0, 0.3);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: ring-pulse 3s ease-in-out infinite;
}

.symbol {
  font-size: 26px;
  line-height: 1;
  color: #ffd700;
  filter: drop-shadow(0 0 6px rgba(255, 215, 0, 0.4));
}

@keyframes ring-pulse {
  0%,
  100% {
    border-color: rgba(255, 215, 0, 0.2);
    box-shadow: 0 0 8px rgba(255, 215, 0, 0.05);
  }
  50% {
    border-color: rgba(255, 215, 0, 0.5);
    box-shadow: 0 0 16px rgba(255, 215, 0, 0.15);
  }
}

/* Speaker name */
.speaker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #ffd700;
  margin-bottom: 16px;
  opacity: 0.7;
}

/* Narration text */
.narration {
  font-size: 15px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.85);
  white-space: pre-line;
  min-height: 100px;
  font-family: 'Segoe UI', system-ui, sans-serif;
}

.cursor {
  color: #ffd700;
  animation: blink 0.6s step-end infinite;
  font-weight: 300;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

/* Step dots */
.step-dots {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin: 20px 0 16px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  transition: all 0.4s ease;
}

.dot.active {
  background: #ffd700;
  box-shadow: 0 0 6px rgba(255, 215, 0, 0.5);
  transform: scale(1.3);
}

.dot.done {
  background: rgba(255, 215, 0, 0.4);
}

/* Actions */
.actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
}

.skip-btn {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.25);
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px 0;
  transition: color 0.2s;
  letter-spacing: 0.03em;
}

.skip-btn:hover {
  color: rgba(255, 255, 255, 0.5);
}

.next-btn {
  font-size: 13px;
  color: #ffd700;
  background: rgba(255, 215, 0, 0.08);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 8px;
  padding: 8px 20px;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 0.04em;
  font-weight: 500;
}

.next-btn:hover {
  background: rgba(255, 215, 0, 0.15);
  border-color: rgba(255, 215, 0, 0.4);
  box-shadow: 0 0 12px rgba(255, 215, 0, 0.1);
}

/* Transitions */
.tutorial-fade-enter-active,
.tutorial-fade-leave-active {
  transition:
    opacity 0.6s ease,
    transform 0.6s ease;
}

.tutorial-fade-enter-from {
  opacity: 0;
  transform: scale(1.02);
}

.tutorial-fade-leave-to {
  opacity: 0;
  transform: scale(0.98);
}

/* Mobile adjustments */
@media (max-width: 640px) {
  .tutorial-overlay {
    align-items: flex-end;
    padding-bottom: 24px;
  }

  .speech-panel {
    padding: 24px 20px 20px;
    border-radius: 14px;
  }

  .narration {
    font-size: 14px;
    min-height: 80px;
  }

  .symbol-ring {
    width: 44px;
    height: 44px;
    margin-bottom: 12px;
  }

  .symbol {
    font-size: 22px;
  }
}
</style>
