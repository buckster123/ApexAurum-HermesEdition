<script setup>
/**
 * AchievementShareModal - Canvas-rendered PNG card for sharing
 *
 * Renders achievement details on an HTML5 Canvas (800x600),
 * with dark gradient bg, gold border, branding. Supports
 * Download PNG and Copy to Clipboard.
 */

import { ref, onMounted, nextTick } from 'vue'

const props = defineProps({
  achievement: { type: Object, required: true },
  stageConfig: { type: Object, default: null },
})

const emit = defineEmits(['close'])

const canvasRef = ref(null)
const copied = ref(false)

onMounted(async () => {
  await nextTick()
  renderCard()
})

function renderCard() {
  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  const W = 800
  const H = 500

  // Dark gradient background
  const grad = ctx.createLinearGradient(0, 0, 0, H)
  grad.addColorStop(0, '#0d0d1a')
  grad.addColorStop(1, '#1a1028')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, W, H)

  // Gold border
  ctx.strokeStyle = '#FFD700'
  ctx.lineWidth = 4
  ctx.strokeRect(12, 12, W - 24, H - 24)

  // Inner subtle border
  ctx.strokeStyle = 'rgba(255, 215, 0, 0.15)'
  ctx.lineWidth = 1
  ctx.strokeRect(20, 20, W - 40, H - 40)

  // Stage color accent bar at top
  const stageColor = props.stageConfig?.color || '#FFD700'
  ctx.fillStyle = stageColor
  ctx.fillRect(12, 12, W - 24, 5)

  // Achievement checkmark circle
  ctx.fillStyle = 'rgba(255, 215, 0, 0.15)'
  ctx.beginPath()
  ctx.arc(W / 2, 120, 45, 0, Math.PI * 2)
  ctx.fill()

  ctx.fillStyle = '#FFD700'
  ctx.font = 'bold 40px sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText('\u2713', W / 2, 120)

  // Stage symbol + name
  if (props.stageConfig) {
    ctx.fillStyle = stageColor
    ctx.font = 'bold 16px sans-serif'
    ctx.fillText(
      `${props.stageConfig.symbol} ${props.stageConfig.name}`,
      W / 2,
      185,
    )
  }

  // Achievement name
  ctx.fillStyle = '#FFFFFF'
  ctx.font = 'bold 32px sans-serif'
  ctx.fillText(props.achievement.name, W / 2, 230)

  // Description
  ctx.fillStyle = '#9CA3AF'
  ctx.font = '18px sans-serif'
  wrapText(ctx, props.achievement.description, W / 2, 275, W - 120, 26)

  // Feature unlocked (if quest)
  if (props.achievement.feature) {
    ctx.fillStyle = 'rgba(255, 215, 0, 0.6)'
    ctx.font = '14px sans-serif'
    const featureText = `Unlocked: ${props.achievement.feature.replace(/_/g, ' ')}`
    ctx.fillText(featureText, W / 2, 345)
  }

  // Divider line
  ctx.strokeStyle = 'rgba(255, 215, 0, 0.2)'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(200, 390)
  ctx.lineTo(600, 390)
  ctx.stroke()

  // Branding
  ctx.fillStyle = '#FFD700'
  ctx.font = 'bold 20px serif'
  ctx.fillText('ApexAurum', W / 2, 430)

  ctx.fillStyle = '#555'
  ctx.font = '12px sans-serif'
  ctx.fillText('apexaurum.com', W / 2, 460)
}

function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
  const words = text.split(' ')
  let line = ''
  for (const word of words) {
    const test = line + word + ' '
    if (ctx.measureText(test).width > maxWidth && line !== '') {
      ctx.fillText(line.trim(), x, y)
      line = word + ' '
      y += lineHeight
    } else {
      line = test
    }
  }
  ctx.fillText(line.trim(), x, y)
}

function downloadPNG() {
  const canvas = canvasRef.value
  if (!canvas) return
  const link = document.createElement('a')
  link.download = `achievement-${props.achievement.id}.png`
  link.href = canvas.toDataURL('image/png')
  link.click()
}

async function copyToClipboard() {
  const canvas = canvasRef.value
  if (!canvas) return
  try {
    const blob = await new Promise((resolve) =>
      canvas.toBlob(resolve, 'image/png'),
    )
    await navigator.clipboard.write([
      new ClipboardItem({ 'image/png': blob }),
    ])
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    // Clipboard API may not be available in all contexts
  }
}
</script>

<template>
  <div
    class="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4"
    @click.self="emit('close')"
  >
    <div class="bg-apex-dark border border-apex-border rounded-xl w-full max-w-[850px] p-6">
      <!-- Header -->
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-serif font-bold text-gold">Share Achievement</h2>
        <button
          @click="emit('close')"
          class="text-gray-500 hover:text-gray-300 transition-colors"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Canvas Preview -->
      <div class="flex justify-center mb-5 overflow-hidden rounded-lg border border-white/10">
        <canvas
          ref="canvasRef"
          width="800"
          height="500"
          class="max-w-full h-auto"
        />
      </div>

      <!-- Actions -->
      <div class="flex justify-center gap-3">
        <button
          @click="downloadPNG"
          class="px-5 py-2.5 bg-gold text-black font-medium rounded-lg hover:bg-gold/90 transition-colors text-sm"
        >
          Download PNG
        </button>
        <button
          @click="copyToClipboard"
          class="px-5 py-2.5 bg-white/10 text-white rounded-lg hover:bg-white/15 transition-colors text-sm"
        >
          {{ copied ? 'Copied!' : 'Copy to Clipboard' }}
        </button>
      </div>
    </div>
  </div>
</template>
