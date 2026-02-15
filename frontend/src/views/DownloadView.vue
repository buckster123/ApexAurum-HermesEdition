<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const qrDataUrl = ref('')
const downloadUrl = ref('')
const appVersion = ref(null)
const loading = ref(true)

onMounted(async () => {
  let apiUrl = import.meta.env.VITE_API_URL || ''
  if (apiUrl && !apiUrl.startsWith('http://') && !apiUrl.startsWith('https://')) {
    apiUrl = 'https://' + apiUrl
  }

  // Fetch version info from backend
  try {
    const res = await fetch(`${apiUrl}/api/v1/app/latest`)
    if (res.ok) {
      appVersion.value = await res.json()
      downloadUrl.value = appVersion.value.download_url || `${apiUrl}/api/v1/app/download`
    }
  } catch (e) {
    downloadUrl.value = `${apiUrl}/api/v1/app/download`
  }
  loading.value = false

  // Generate QR code using the qrcode package (v1.5.4 in package.json)
  if (downloadUrl.value) {
    try {
      const QRCode = await import('qrcode')
      qrDataUrl.value = await QRCode.toDataURL(downloadUrl.value, {
        width: 200,
        margin: 2,
        color: { dark: '#FFD700', light: '#0a0a0a' }
      })
    } catch (e) {
      // QR generation failed — hide that section gracefully
    }
  }
})

const features = [
  {
    title: 'Four AI Agents',
    description: 'Switch between AZOTH, ELYSIAN, VAJRA, and KETHER instantly. Each brings a different mind to the conversation.',
    icon: '&#9775;',
    colors: ['#FFD700', '#E8B4FF', '#4FC3F7', '#FFFFFF'],
  },
  {
    title: 'Soul Face',
    description: 'Animated mood expressions that react to conversation flow. Your agent\'s emotional state, visualized.',
    icon: '&#128171;',
    accent: '#FFD700',
  },
  {
    title: 'SensorHead Dashboard',
    description: 'Cameras, thermal, environment sensors on your Raspberry Pi — controlled from your phone.',
    icon: '&#128225;',
    accent: '#4FC3F7',
  },
  {
    title: 'Council Deliberation',
    description: 'Watch four minds debate in real-time. Interrupt, redirect, or let them reach consensus.',
    icon: '&#127981;',
    accent: '#E8B4FF',
  },
  {
    title: 'CerebroCortex Memory',
    description: 'Graph visualization of AI memory constellations. Search, explore, and connect the dots.',
    icon: '&#129504;',
    accent: '#FFD700',
  },
  {
    title: 'Village Pulse',
    description: 'Live WebSocket feed of agent activity. See every tool call, every result, as it happens.',
    icon: '&#128301;',
    accent: '#4FC3F7',
  },
]

const screenshots = [
  { label: 'Chat with AZOTH', color: '#FFD700' },
  { label: 'Soul Face', color: '#E8B4FF' },
  { label: 'Sensor Dashboard', color: '#4FC3F7' },
  { label: 'Council View', color: '#FFFFFF' },
  { label: 'Memory Graph', color: '#FFD700' },
]
</script>

<template>
  <div class="min-h-screen bg-apex-darker text-white overflow-hidden">

    <!-- ════ Hero ═══════════════════════════════════════════════════════ -->
    <section class="relative min-h-[90vh] flex flex-col items-center justify-center px-4 text-center">
      <!-- Radial glow background -->
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(212,175,55,0.06)_0%,transparent_60%)]"></div>
      <!-- Subtle grid overlay -->
      <div class="absolute inset-0 opacity-[0.03]" style="background-image: linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px); background-size: 40px 40px;"></div>

      <div class="relative z-10 max-w-3xl mx-auto">
        <div class="text-8xl sm:text-9xl font-serif font-bold text-gold mb-4 tracking-tight">Au</div>
        <h1 class="text-4xl sm:text-5xl lg:text-6xl font-bold mb-4 leading-tight">
          ApexPocket
        </h1>
        <p class="text-lg sm:text-xl text-gray-400 max-w-xl mx-auto mb-10 leading-relaxed">
          Your Village, in your pocket.<br />
          Four AI minds on your phone.
        </p>

        <div class="flex flex-col sm:flex-row gap-4 justify-center">
          <a
            :href="downloadUrl || '#'"
            :class="[
              'px-8 py-3 bg-gold text-black font-bold rounded-lg text-lg transition-all hover:scale-105 inline-flex items-center gap-2',
              !downloadUrl ? 'opacity-50 pointer-events-none' : 'hover:bg-gold/90'
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
            Download APK
          </a>
          <button
            @click="router.push('/devices/build-guide')"
            class="px-8 py-3 border border-white/20 text-white rounded-lg text-lg hover:border-gold/50 hover:text-gold transition-all inline-flex items-center gap-2"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0015.414 6L12 2.586A2 2 0 0010.586 2H6zm5 6a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V8z" clip-rule="evenodd" />
            </svg>
            Build Guide
          </button>
        </div>
      </div>

      <!-- Scroll hint -->
      <div class="absolute bottom-8 animate-bounce text-gray-600">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
      </div>
    </section>

    <!-- ════ QR Code + Version Info ═════════════════════════════════════ -->
    <section class="py-20 px-4 bg-apex-dark/50">
      <div class="max-w-md mx-auto text-center">
        <!-- QR Code -->
        <div v-if="qrDataUrl" class="bg-apex-card border border-apex-border rounded-xl p-8 mb-6">
          <img :src="qrDataUrl" alt="Scan to download ApexPocket" class="mx-auto mb-4 rounded-lg" width="200" height="200" />
          <p class="text-gray-400 text-sm">Scan to download</p>
        </div>
        <div v-else-if="!loading" class="bg-apex-card border border-apex-border rounded-xl p-8 mb-6">
          <div class="w-[200px] h-[200px] mx-auto mb-4 rounded-lg border border-dashed border-apex-border flex items-center justify-center">
            <span class="text-gray-600 text-sm">QR loading...</span>
          </div>
          <p class="text-gray-400 text-sm">Scan to download</p>
        </div>

        <!-- Version badges -->
        <div class="flex flex-wrap justify-center gap-3">
          <span class="text-xs px-3 py-1.5 rounded-full bg-gold/10 text-gold font-medium">
            v{{ appVersion?.version_name || '1.0.0' }}
          </span>
          <span class="text-xs px-3 py-1.5 rounded-full bg-white/5 text-gray-300">
            {{ appVersion?.file_size_mb || 43 }} MB
          </span>
          <span class="text-xs px-3 py-1.5 rounded-full bg-white/5 text-gray-300">
            Android {{ appVersion?.min_android || '8.0+' }}
          </span>
        </div>
      </div>
    </section>

    <!-- ════ Feature Showcase ═══════════════════════════════════════════ -->
    <section class="py-24 px-4">
      <div class="max-w-5xl mx-auto">
        <h2 class="text-3xl sm:text-4xl font-bold text-center mb-4">Everything. In Your Hand.</h2>
        <p class="text-gray-400 text-center mb-16 max-w-2xl mx-auto">
          Not a web wrapper. A native Android companion built for the ApexAurum ecosystem.
        </p>

        <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <!-- Four AI Agents (special card with multi-color accent) -->
          <div class="bg-apex-card border border-apex-border rounded-xl p-6 hover:border-[#FFD700]/50 transition-colors group relative overflow-hidden">
            <!-- Multi-agent color bar at top -->
            <div class="absolute top-0 left-0 right-0 h-0.5 flex">
              <div class="flex-1 bg-[#FFD700]"></div>
              <div class="flex-1 bg-[#E8B4FF]"></div>
              <div class="flex-1 bg-[#4FC3F7]"></div>
              <div class="flex-1 bg-white"></div>
            </div>
            <div class="flex items-center gap-2 mb-4 mt-2">
              <span class="w-3 h-3 rounded-full bg-[#FFD700]"></span>
              <span class="w-3 h-3 rounded-full bg-[#E8B4FF]"></span>
              <span class="w-3 h-3 rounded-full bg-[#4FC3F7]"></span>
              <span class="w-3 h-3 rounded-full bg-white"></span>
            </div>
            <h3 class="font-bold text-lg mb-2">Four AI Agents</h3>
            <p class="text-sm text-gray-400">Switch between AZOTH, ELYSIAN, VAJRA, and KETHER instantly. Each brings a different mind to the conversation.</p>
          </div>

          <!-- Soul Face -->
          <div class="bg-apex-card border border-apex-border rounded-xl p-6 hover:border-[#FFD700]/50 transition-colors group relative overflow-hidden">
            <div class="absolute top-0 left-0 right-0 h-0.5 bg-[#FFD700]"></div>
            <div class="text-3xl mb-4 mt-2 group-hover:scale-110 transition-transform" v-html="'&#128171;'"></div>
            <h3 class="font-bold text-lg mb-2">Soul Face</h3>
            <p class="text-sm text-gray-400">Animated mood expressions that react to conversation flow. Your agent's emotional state, visualized.</p>
          </div>

          <!-- SensorHead -->
          <div class="bg-apex-card border border-apex-border rounded-xl p-6 hover:border-[#4FC3F7]/50 transition-colors group relative overflow-hidden">
            <div class="absolute top-0 left-0 right-0 h-0.5 bg-[#4FC3F7]"></div>
            <div class="text-3xl mb-4 mt-2 group-hover:scale-110 transition-transform" v-html="'&#128225;'"></div>
            <h3 class="font-bold text-lg mb-2">SensorHead Dashboard</h3>
            <p class="text-sm text-gray-400">Cameras, thermal, environment sensors on your Raspberry Pi -- controlled from your phone.</p>
          </div>

          <!-- Council -->
          <div class="bg-apex-card border border-apex-border rounded-xl p-6 hover:border-[#E8B4FF]/50 transition-colors group relative overflow-hidden">
            <div class="absolute top-0 left-0 right-0 h-0.5 bg-[#E8B4FF]"></div>
            <div class="text-3xl mb-4 mt-2 group-hover:scale-110 transition-transform" v-html="'&#127981;'"></div>
            <h3 class="font-bold text-lg mb-2">Council Deliberation</h3>
            <p class="text-sm text-gray-400">Watch four minds debate in real-time. Interrupt, redirect, or let them reach consensus.</p>
          </div>

          <!-- CerebroCortex -->
          <div class="bg-apex-card border border-apex-border rounded-xl p-6 hover:border-[#FFD700]/50 transition-colors group relative overflow-hidden">
            <div class="absolute top-0 left-0 right-0 h-0.5 bg-[#FFD700]"></div>
            <div class="text-3xl mb-4 mt-2 group-hover:scale-110 transition-transform" v-html="'&#129504;'"></div>
            <h3 class="font-bold text-lg mb-2">CerebroCortex Memory</h3>
            <p class="text-sm text-gray-400">Graph visualization of AI memory constellations. Search, explore, and connect the dots.</p>
          </div>

          <!-- Village Pulse -->
          <div class="bg-apex-card border border-apex-border rounded-xl p-6 hover:border-[#4FC3F7]/50 transition-colors group relative overflow-hidden">
            <div class="absolute top-0 left-0 right-0 h-0.5 bg-[#4FC3F7]"></div>
            <div class="text-3xl mb-4 mt-2 group-hover:scale-110 transition-transform" v-html="'&#128301;'"></div>
            <h3 class="font-bold text-lg mb-2">Village Pulse</h3>
            <p class="text-sm text-gray-400">Live WebSocket feed of agent activity. See every tool call, every result, as it happens.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ════ Screenshots Gallery ════════════════════════════════════════ -->
    <section class="py-24 px-4 bg-apex-dark/50">
      <div class="max-w-6xl mx-auto">
        <h2 class="text-3xl sm:text-4xl font-bold text-center mb-4">See It In Action</h2>
        <p class="text-gray-400 text-center mb-12 max-w-2xl mx-auto">
          Native Android, designed for the Athanor.
        </p>

        <!-- Horizontal scroll gallery -->
        <div class="overflow-x-auto pb-4 -mx-4 px-4 scrollbar-hide">
          <div class="flex gap-6 w-max">
            <div
              v-for="(shot, i) in screenshots"
              :key="i"
              class="flex-shrink-0 w-48 sm:w-56"
            >
              <!-- Phone mockup frame -->
              <div
                class="rounded-[2rem] border-2 overflow-hidden"
                :style="{ borderColor: shot.color + '40' }"
                style="aspect-ratio: 9 / 19.5;"
              >
                <div class="w-full h-full bg-apex-card flex flex-col items-center justify-center px-4 relative">
                  <!-- Notch -->
                  <div class="absolute top-3 left-1/2 -translate-x-1/2 w-16 h-2 rounded-full bg-black/60"></div>

                  <!-- Simulated content -->
                  <div class="w-8 h-8 rounded-full mb-3 opacity-20" :style="{ backgroundColor: shot.color }"></div>
                  <div class="w-3/4 h-1.5 rounded-full bg-white/10 mb-2"></div>
                  <div class="w-1/2 h-1.5 rounded-full bg-white/5 mb-6"></div>

                  <!-- Center icon -->
                  <div
                    class="w-16 h-16 rounded-xl flex items-center justify-center text-2xl mb-4"
                    :style="{ backgroundColor: shot.color + '15' }"
                  >
                    <span :style="{ color: shot.color }">Au</span>
                  </div>

                  <!-- Fake lines -->
                  <div class="w-full space-y-2 px-2">
                    <div class="w-full h-1 rounded-full bg-white/5"></div>
                    <div class="w-4/5 h-1 rounded-full bg-white/5"></div>
                    <div class="w-3/5 h-1 rounded-full bg-white/5"></div>
                  </div>

                  <!-- Bottom nav dots -->
                  <div class="absolute bottom-4 flex gap-2">
                    <div class="w-1.5 h-1.5 rounded-full" :style="{ backgroundColor: shot.color + '60' }"></div>
                    <div class="w-1.5 h-1.5 rounded-full bg-white/10"></div>
                    <div class="w-1.5 h-1.5 rounded-full bg-white/10"></div>
                  </div>
                </div>
              </div>
              <!-- Label -->
              <p class="text-center text-sm text-gray-400 mt-3">{{ shot.label }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ════ Changelog ══════════════════════════════════════════════════ -->
    <section v-if="appVersion?.changelog?.length" class="py-20 px-4">
      <div class="max-w-2xl mx-auto">
        <h2 class="text-2xl sm:text-3xl font-bold text-center mb-10">What's Included</h2>
        <div class="bg-apex-card border border-apex-border rounded-xl p-6 sm:p-8">
          <div class="flex items-center gap-3 mb-6">
            <span class="text-xs px-2.5 py-1 rounded-full bg-gold/10 text-gold font-bold">v{{ appVersion.version_name }}</span>
            <span class="text-xs text-gray-500">{{ appVersion.release_date }}</span>
          </div>
          <ul class="space-y-3">
            <li
              v-for="(item, i) in appVersion.changelog"
              :key="i"
              class="flex items-start gap-3 text-sm text-gray-300"
            >
              <span class="text-gold mt-0.5 flex-shrink-0">&#10003;</span>
              <span>{{ item }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <!-- ════ Requirements ═══════════════════════════════════════════════ -->
    <section class="py-20 px-4" :class="appVersion?.changelog?.length ? 'bg-apex-dark/50' : ''">
      <div class="max-w-2xl mx-auto">
        <h2 class="text-2xl sm:text-3xl font-bold text-center mb-10">Requirements</h2>
        <div class="bg-apex-card border border-apex-border rounded-xl p-6 sm:p-8">
          <div class="grid sm:grid-cols-2 gap-6">
            <div>
              <h3 class="font-bold text-sm text-gold mb-3 uppercase tracking-wider">Device</h3>
              <ul class="space-y-2 text-sm text-gray-400">
                <li class="flex items-center gap-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0"></span>
                  Android 8.0+ (API 26)
                </li>
                <li class="flex items-center gap-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0"></span>
                  ~{{ appVersion?.file_size_mb || 43 }} MB download
                </li>
                <li class="flex items-center gap-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0"></span>
                  ARM64 or x86_64
                </li>
              </ul>
            </div>
            <div>
              <h3 class="font-bold text-sm text-gold mb-3 uppercase tracking-wider">Permissions</h3>
              <ul class="space-y-2 text-sm text-gray-400">
                <li class="flex items-center gap-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-gold flex-shrink-0"></span>
                  Internet access
                </li>
                <li class="flex items-center gap-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-gray-500 flex-shrink-0"></span>
                  Camera <span class="text-gray-600">(optional)</span>
                </li>
                <li class="flex items-center gap-2">
                  <span class="w-1.5 h-1.5 rounded-full bg-gray-500 flex-shrink-0"></span>
                  Notifications
                </li>
              </ul>
            </div>
          </div>

          <!-- SensorHead callout -->
          <div class="mt-8 pt-6 border-t border-apex-border">
            <div class="flex items-start gap-3">
              <div class="w-10 h-10 rounded-lg bg-[#4FC3F7]/10 flex items-center justify-center text-lg flex-shrink-0" v-html="'&#128225;'"></div>
              <div>
                <p class="text-sm font-medium text-white mb-1">SensorHead Integration</p>
                <p class="text-xs text-gray-500">
                  Pair with a Raspberry Pi 5 SensorHead for the full experience &mdash;
                  cameras, thermal imaging, and environment sensors accessible from your phone.
                  <button
                    @click="router.push('/devices/build-guide')"
                    class="text-[#4FC3F7] hover:underline ml-1"
                  >Build one &rarr;</button>
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ════ Install Instructions ═══════════════════════════════════════ -->
    <section class="py-20 px-4">
      <div class="max-w-2xl mx-auto">
        <h2 class="text-2xl sm:text-3xl font-bold text-center mb-10">Installation</h2>
        <div class="space-y-4">
          <div class="bg-apex-card border border-apex-border rounded-xl p-5 flex items-start gap-4">
            <div class="w-8 h-8 rounded-full bg-gold/10 flex items-center justify-center text-gold font-bold text-sm flex-shrink-0">1</div>
            <div>
              <p class="font-medium text-sm">Download the APK</p>
              <p class="text-xs text-gray-500 mt-1">Tap the download button above or scan the QR code from another device.</p>
            </div>
          </div>
          <div class="bg-apex-card border border-apex-border rounded-xl p-5 flex items-start gap-4">
            <div class="w-8 h-8 rounded-full bg-gold/10 flex items-center justify-center text-gold font-bold text-sm flex-shrink-0">2</div>
            <div>
              <p class="font-medium text-sm">Allow unknown sources</p>
              <p class="text-xs text-gray-500 mt-1">Android will prompt you to allow installation from this source. This is required for APK sideloading.</p>
            </div>
          </div>
          <div class="bg-apex-card border border-apex-border rounded-xl p-5 flex items-start gap-4">
            <div class="w-8 h-8 rounded-full bg-gold/10 flex items-center justify-center text-gold font-bold text-sm flex-shrink-0">3</div>
            <div>
              <p class="font-medium text-sm">Install and sign in</p>
              <p class="text-xs text-gray-500 mt-1">Open the APK, install, then sign in with your ApexAurum account. The Village awaits.</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ════ Footer CTA ═════════════════════════════════════════════════ -->
    <section class="py-24 px-4 text-center bg-apex-dark/50">
      <div class="max-w-2xl mx-auto">
        <p class="text-gold font-serif text-2xl italic mb-6">"The Village awaits."</p>
        <p class="text-gray-400 mb-10">Four minds. Your pocket. Everywhere you go.</p>
        <div class="flex flex-col sm:flex-row gap-4 justify-center">
          <a
            :href="downloadUrl || '#'"
            :class="[
              'px-10 py-4 bg-gold text-black font-bold rounded-lg text-lg transition-all inline-flex items-center gap-2',
              !downloadUrl ? 'opacity-50 pointer-events-none' : 'hover:bg-gold/90 hover:scale-105'
            ]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
            Download ApexPocket
          </a>
        </div>
        <p class="mt-8 text-sm text-gray-500">
          Need the hardware?
          <button
            @click="router.push('/devices/build-guide')"
            class="text-gold hover:underline ml-1"
          >
            Build Guide &rarr;
          </button>
        </p>
      </div>
      <div class="mt-16 text-xs text-gray-600">
        &copy; 2026 ApexAurum. All rights reserved.
      </div>
    </section>

  </div>
</template>

<style scoped>
/* Hide scrollbar for screenshots gallery */
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
</style>
