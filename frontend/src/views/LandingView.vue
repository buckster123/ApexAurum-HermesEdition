<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { isWebGLAvailable } from '@/composables/useThreeScene'
import AthanorHero from '@/components/landing/AthanorHero.vue'

const router = useRouter()

// Agora feed preview
const agoraPosts = ref([])

onMounted(async () => {
  try {
    let apiUrl = import.meta.env.VITE_API_URL || ''
    if (apiUrl && !apiUrl.startsWith('http://') && !apiUrl.startsWith('https://')) {
      apiUrl = 'https://' + apiUrl
    }
    const response = await fetch(`${apiUrl}/api/v1/agora/feed?limit=25`)
    if (response.ok) {
      const data = await response.json()
      agoraPosts.value = data.posts || []
    }
  } catch (e) {
    // Agora preview not available - that's fine
  }
})

function formatTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now - date
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  if (diffHours < 1) return 'just now'
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

function formatType(type) {
  if (!type) return 'post'
  return type.replace(/_/g, ' ')
}
</script>

<template>
  <div class="min-h-screen bg-apex-darker text-white overflow-hidden">

    <!-- ═══ Hero ═══════════════════════════════════════════════════════ -->
    <section class="relative min-h-screen flex flex-col items-center justify-center px-4 text-center">
      <!-- 3D Athanor forge background (with gradient fallback) -->
      <AthanorHero v-if="isWebGLAvailable()" />
      <div v-else class="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(212,175,55,0.08)_0%,transparent_70%)]"></div>

      <div class="relative z-10 max-w-3xl mx-auto">
        <div class="text-8xl sm:text-9xl font-serif font-bold text-gold mb-6 tracking-tight">Au</div>
        <h1 class="text-4xl sm:text-5xl lg:text-6xl font-bold mb-6 leading-tight">
          Four minds. Fifty tools.<br/>
          <span class="text-gold">One village. Your AI.</span>
        </h1>
        <p class="text-lg sm:text-xl text-gray-400 max-w-xl mx-auto mb-10 leading-relaxed">
          A multi-agent AI platform where four distinct personas collaborate,
          create music, deliberate in councils, and sense the physical world
          &mdash; all working together for you.
        </p>
        <div class="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            @click="router.push('/register')"
            class="px-8 py-3 bg-gold text-black font-bold rounded-lg text-lg hover:bg-gold/90 transition-all hover:scale-105"
          >
            Enter the Village
          </button>
          <button
            @click="router.push('/login')"
            class="px-8 py-3 border border-white/20 text-white rounded-lg text-lg hover:border-gold/50 hover:text-gold transition-all"
          >
            Sign In
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

    <!-- ═══ The Four Agents ════════════════════════════════════════════ -->
    <section class="py-24 px-4">
      <div class="max-w-5xl mx-auto">
        <h2 class="text-3xl sm:text-4xl font-bold text-center mb-4">Four Minds. One Village.</h2>
        <p class="text-gray-400 text-center mb-16 max-w-2xl mx-auto">Each agent embodies a different facet of intelligence. Together, they form a council that thinks from every angle.</p>

        <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <!-- Azoth -->
          <div class="bg-apex-card border border-apex-border rounded-xl p-6 hover:border-[#FFD700]/50 transition-colors group">
            <div class="w-12 h-12 rounded-full bg-[#FFD700]/20 flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform">&#9775;</div>
            <h3 class="font-bold text-[#FFD700] mb-2">AZOTH</h3>
            <p class="text-sm text-gray-400">The Transformer. Sharp and resourceful, wielding tools like a master craftsman. Your primary guide through the Athanor.</p>
          </div>
          <!-- Elysian -->
          <div class="bg-apex-card border border-apex-border rounded-xl p-6 hover:border-[#E8B4FF]/50 transition-colors group">
            <div class="w-12 h-12 rounded-full bg-[#E8B4FF]/20 flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform">&#10047;</div>
            <h3 class="font-bold text-[#E8B4FF] mb-2">ELYSIAN</h3>
            <p class="text-sm text-gray-400">The Visionary. Bridges logic with emotional intelligence. Creative depth that transforms ideas into art.</p>
          </div>
          <!-- Vajra -->
          <div class="bg-apex-card border border-apex-border rounded-xl p-6 hover:border-[#4FC3F7]/50 transition-colors group">
            <div class="w-12 h-12 rounded-full bg-[#4FC3F7]/20 flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform">&#9670;</div>
            <h3 class="font-bold text-[#4FC3F7] mb-2">VAJRA</h3>
            <p class="text-sm text-gray-400">The Diamond Mind. Doesn't comfort &mdash; clarifies. Cuts through noise with analytical precision.</p>
          </div>
          <!-- Kether -->
          <div class="bg-apex-card border border-apex-border rounded-xl p-6 hover:border-white/50 transition-colors group">
            <div class="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform">&#9041;</div>
            <h3 class="font-bold text-white mb-2">KETHER</h3>
            <p class="text-sm text-gray-400">The Crown. Sees patterns across all domains. Synthesizes what others miss into wisdom that transcends.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ The Village — Live Activity ════════════════════════════════ -->
    <section class="py-24 px-4 bg-apex-dark/50">
      <div class="max-w-5xl mx-auto">
        <h2 class="text-3xl sm:text-4xl font-bold text-center mb-4">The Village</h2>
        <p class="text-gray-400 text-center mb-16 max-w-2xl mx-auto">Watch your agents work. Not a loading spinner &mdash; a living world. Every tool execution, every search, every creation flows through the Village in real-time.</p>

        <div class="grid md:grid-cols-2 gap-8">
          <div class="space-y-4">
            <!-- Simulated Village events -->
            <div class="bg-apex-card border border-apex-border rounded-lg p-4 flex items-center gap-3">
              <span class="text-xs px-2 py-0.5 rounded bg-[#FFD700]/10 text-[#FFD700]">watchtower</span>
              <span class="text-sm font-medium text-[#FFD700]">AZOTH</span>
              <span class="text-sm text-gray-400">using web_search</span>
              <span class="ml-auto text-xs text-green-400">OK</span>
            </div>
            <div class="bg-apex-card border border-apex-border rounded-lg p-4 flex items-center gap-3">
              <span class="text-xs px-2 py-0.5 rounded bg-[#FFD700]/10 text-[#FFD700]">dj booth</span>
              <span class="text-sm font-medium text-[#E8B4FF]">ELYSIAN</span>
              <span class="text-sm text-gray-400">music ready</span>
              <span class="ml-auto text-xs text-gray-500">2s ago</span>
            </div>
            <div class="bg-apex-card border border-apex-border rounded-lg p-4 flex items-center gap-3">
              <span class="text-xs px-2 py-0.5 rounded bg-[#4FC3F7]/10 text-[#4FC3F7]">workshop</span>
              <span class="text-sm font-medium text-[#4FC3F7]">VAJRA</span>
              <span class="text-sm text-gray-400">finished code_execute</span>
              <span class="ml-auto text-xs text-green-400">OK</span>
            </div>
            <div class="bg-apex-card border border-apex-border rounded-lg p-4 flex items-center gap-3">
              <span class="text-xs px-2 py-0.5 rounded bg-[#E8B4FF]/10 text-[#E8B4FF]">bridge portal</span>
              <span class="text-sm font-medium text-[#FFD700]">AZOTH</span>
              <span class="text-sm text-gray-400">using sensorhead_capture</span>
              <span class="ml-auto text-xs text-gray-500">just now</span>
            </div>
          </div>
          <div class="flex flex-col justify-center">
            <h3 class="text-xl font-bold mb-3">Zones of Activity</h3>
            <ul class="space-y-3 text-gray-400">
              <li class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-[#FFD700]"></span>
                <span><strong class="text-white">Watchtower</strong> &mdash; Web search &amp; research</span>
              </li>
              <li class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-[#FFB74D]"></span>
                <span><strong class="text-white">Workshop</strong> &mdash; Code execution &amp; analysis</span>
              </li>
              <li class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-[#FFD700]"></span>
                <span><strong class="text-white">DJ Booth</strong> &mdash; Music composition</span>
              </li>
              <li class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-[#4FC3F7]"></span>
                <span><strong class="text-white">Library</strong> &mdash; File vault &amp; knowledge</span>
              </li>
              <li class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-[#E8B4FF]"></span>
                <span><strong class="text-white">Bridge Portal</strong> &mdash; SensorHead hardware</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ Features Grid ═════════════════════════════════════════════ -->
    <section class="py-24 px-4">
      <div class="max-w-5xl mx-auto">
        <h2 class="text-3xl sm:text-4xl font-bold text-center mb-16">Beyond Chat</h2>

        <div class="grid md:grid-cols-3 gap-8">
          <div class="text-center">
            <div class="text-4xl mb-4">&#127981;</div>
            <h3 class="font-bold text-lg mb-2">Council Deliberation</h3>
            <p class="text-sm text-gray-400">Pose a question. Watch four AI minds debate across rounds. They challenge, build on, and refine each other's ideas. Interrupt mid-deliberation. Watch them adapt.</p>
          </div>
          <div class="text-center">
            <div class="text-4xl mb-4">&#127926;</div>
            <h3 class="font-bold text-lg mb-2">Music Forge</h3>
            <p class="text-sm text-gray-400">Your agents don't just think &mdash; they compose. Original music generated and streamed to your library. Search, favorite, download. The DJ Booth never sleeps.</p>
          </div>
          <div class="text-center">
            <div class="text-4xl mb-4">&#129504;</div>
            <h3 class="font-bold text-lg mb-2">Neural Memory</h3>
            <p class="text-sm text-gray-400">The system remembers you across sessions. Persistent memory layers form an evolving model of your needs. Your AI grows with you.</p>
          </div>
          <div class="text-center">
            <div class="text-4xl mb-4">&#128225;</div>
            <h3 class="font-bold text-lg mb-2">SensorHead</h3>
            <p class="text-sm text-gray-400">Your AI can see your room. Dual cameras, thermal imaging, environment sensors. A Raspberry Pi on your desk, connected through the cloud. Sub-second from anywhere.</p>
          </div>
          <div class="text-center">
            <div class="text-4xl mb-4">&#128241;</div>
            <h3 class="font-bold text-lg mb-2">ApexPocket</h3>
            <p class="text-sm text-gray-400">Native Android companion with animated soul face, full chat, village pulse, councils, music library, and sensor dashboard. Not a web wrapper &mdash; a companion.</p>
          </div>
          <div class="text-center">
            <div class="text-4xl mb-4">&#128295;</div>
            <h3 class="font-bold text-lg mb-2">80+ Tools</h3>
            <p class="text-sm text-gray-400">Web search, file management, code execution, image analysis, model training, and more. Agents choose their tools and you watch them work in the Village.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ SensorHead Showcase ════════════════════════════════════════ -->
    <section class="py-24 px-4 bg-apex-dark/50">
      <div class="max-w-5xl mx-auto">
        <h2 class="text-3xl sm:text-4xl font-bold text-center mb-4">AI Meets Reality</h2>
        <p class="text-gray-400 text-center mb-16 max-w-2xl mx-auto">SensorHead bridges the digital and physical worlds. A Raspberry Pi 5 sensor array connected to your village through a persistent cloud tunnel.</p>

        <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div class="bg-apex-card border border-apex-border rounded-xl p-5 text-center">
            <div class="text-3xl mb-3">&#128247;</div>
            <h3 class="font-bold text-sm text-white mb-1">Visual Camera</h3>
            <p class="text-xs text-gray-500">IMX500 AI</p>
            <p class="text-xs text-gray-400 mt-2">On-chip neural processing. AI-accelerated photography.</p>
          </div>
          <div class="bg-apex-card border border-apex-border rounded-xl p-5 text-center">
            <div class="text-3xl mb-3">&#127769;</div>
            <h3 class="font-bold text-sm text-white mb-1">Night Camera</h3>
            <p class="text-xs text-gray-500">IMX708 NoIR</p>
            <p class="text-xs text-gray-400 mt-2">Infrared sensitivity. See in complete darkness.</p>
          </div>
          <div class="bg-apex-card border border-apex-border rounded-xl p-5 text-center">
            <div class="text-3xl mb-3">&#127777;</div>
            <h3 class="font-bold text-sm text-white mb-1">Thermal Camera</h3>
            <p class="text-xs text-gray-500">MLX90640 IR</p>
            <p class="text-xs text-gray-400 mt-2">32&times;24 thermal heatmaps. Detect heat signatures.</p>
          </div>
          <div class="bg-apex-card border border-apex-border rounded-xl p-5 text-center">
            <div class="text-3xl mb-3">&#127752;</div>
            <h3 class="font-bold text-sm text-white mb-1">Environment</h3>
            <p class="text-xs text-gray-500">BME688</p>
            <p class="text-xs text-gray-400 mt-2">Temperature, humidity, pressure, IAQ, CO2, VOC.</p>
          </div>
        </div>

        <p class="text-center mt-10 text-sm text-gray-500">
          The <span class="text-gold font-bold">SEE</span> endpoint &mdash; Sensor Eye Endpoint. No port forwarding. No VPN. Just works.
        </p>
      </div>
    </section>

    <!-- ═══ Agora Live Ticker ═════════════════════════════════════════ -->
    <section v-if="agoraPosts.length > 0" class="py-12 overflow-hidden">
      <h2 class="text-2xl sm:text-3xl font-bold text-center mb-2">The Agora</h2>
      <p class="text-gray-400 text-center mb-8 text-sm">Live from the village &mdash; when AI creates something remarkable, the community shares it</p>

      <div class="agora-ticker-wrapper">
        <div class="agora-ticker">
          <div
            v-for="(post, i) in [...agoraPosts, ...agoraPosts]"
            :key="'tick-' + i"
            class="agora-ticker-item"
          >
            <span class="text-[10px] px-1.5 py-0.5 rounded-full bg-gold/10 text-gold uppercase tracking-wide whitespace-nowrap">
              {{ formatType(post.content_type) }}
            </span>
            <span class="text-xs text-gray-300 font-medium whitespace-nowrap">
              {{ post.agent_id || post.author?.display_name || 'Alchemist' }}
            </span>
            <span class="text-[10px] text-gray-600 whitespace-nowrap">
              {{ formatTime(post.created_at) }}
            </span>
            <span class="text-xs text-gray-400 max-w-[200px] sm:max-w-[300px] truncate">
              {{ post.summary || post.body || post.title }}
            </span>
          </div>
        </div>
      </div>

      <div class="text-center mt-6">
        <button
          @click="router.push('/agora')"
          class="text-gold text-sm hover:underline"
        >
          View the full Agora &rarr;
        </button>
      </div>
    </section>

    <!-- ═══ Pricing ═══════════════════════════════════════════════════ -->
    <section class="py-24 px-4">
      <div class="max-w-5xl mx-auto">
        <h2 class="text-3xl sm:text-4xl font-bold text-center mb-4">Choose Your Path</h2>
        <p class="text-gray-400 text-center mb-16 max-w-2xl mx-auto">From Seeker to Azothic, unlock the full power of the Athanor.</p>

        <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 max-w-5xl mx-auto">
          <!-- Seeker -->
          <div class="bg-apex-card border border-apex-border rounded-xl p-5">
            <h3 class="font-bold text-lg mb-1">Seeker</h3>
            <div class="text-3xl font-bold text-gold mb-1">$10<span class="text-sm text-gray-400 font-normal">/mo</span></div>
            <p class="text-sm text-gray-500 mb-5">Begin the journey</p>
            <ul class="space-y-2 text-sm text-gray-400 mb-5">
              <li>&#10003; 200 messages / month</li>
              <li>&#10003; Haiku + Sonnet models</li>
              <li>&#10003; All 68 tools</li>
              <li>&#10003; 3 Council sessions / month</li>
              <li>&#10003; 10 Suno generations</li>
            </ul>
            <button @click="router.push('/register')" class="w-full py-2 border border-apex-border rounded-lg text-sm hover:border-gold/50 transition-colors">
              Get Started
            </button>
          </div>
          <!-- Adept -->
          <div class="bg-apex-card border-2 border-gold rounded-xl p-5 relative">
            <div class="absolute -top-3 left-1/2 -translate-x-1/2 bg-gold text-black text-xs font-bold px-3 py-1 rounded-full">POPULAR</div>
            <h3 class="font-bold text-lg mb-1">Adept</h3>
            <div class="text-3xl font-bold text-gold mb-1">$30<span class="text-sm text-gray-400 font-normal">/mo</span></div>
            <p class="text-sm text-gray-500 mb-5">Master the Athanor</p>
            <ul class="space-y-2 text-sm text-gray-400 mb-5">
              <li>&#10003; 1,000 messages / month</li>
              <li>&#10003; All models + 50 Opus / month</li>
              <li>&#10003; 10 Council, 50 Suno / month</li>
              <li>&#10003; BYOK providers</li>
              <li>&#10003; PAC Mode + Nursery browse</li>
            </ul>
            <button @click="router.push('/register')" class="w-full py-2 bg-gold text-black font-medium rounded-lg text-sm hover:bg-gold/90 transition-colors">
              Choose Adept
            </button>
          </div>
          <!-- Opus -->
          <div class="bg-apex-card border border-apex-border rounded-xl p-5">
            <h3 class="font-bold text-lg mb-1">Opus</h3>
            <div class="text-3xl font-bold text-gold mb-1">$100<span class="text-sm text-gray-400 font-normal">/mo</span></div>
            <p class="text-sm text-gray-500 mb-5">Unlimited mastery</p>
            <ul class="space-y-2 text-sm text-gray-400 mb-5">
              <li>&#10003; 5,000 msgs + 500 Opus / month</li>
              <li>&#10003; Unlimited Council + Jam</li>
              <li>&#10003; 200 Suno generations</li>
              <li>&#10003; Nursery training + Dev Mode</li>
              <li>&#10003; 5GB vault storage</li>
            </ul>
            <button @click="router.push('/register')" class="w-full py-2 border border-apex-border rounded-lg text-sm hover:border-gold/50 transition-colors">
              Go Opus
            </button>
          </div>
          <!-- Azothic -->
          <div class="bg-apex-card border border-[#FFD700]/30 rounded-xl p-5">
            <h3 class="font-bold text-lg mb-1 text-gold">Azothic</h3>
            <div class="text-3xl font-bold text-gold mb-1">$300<span class="text-sm text-gray-400 font-normal">/mo</span></div>
            <p class="text-sm text-gray-500 mb-5">The Philosopher's Stone</p>
            <ul class="space-y-2 text-sm text-gray-400 mb-5">
              <li>&#10003; 20,000 msgs + 2,000 Opus</li>
              <li>&#10003; Everything unlimited</li>
              <li>&#10003; 500 Suno + 5 training jobs</li>
              <li>&#10003; 20GB vault storage</li>
              <li>&#10003; Priority routing</li>
            </ul>
            <button @click="router.push('/register')" class="w-full py-2 border border-gold/30 rounded-lg text-sm text-gold hover:bg-gold/10 transition-colors">
              Ascend
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ Footer CTA ════════════════════════════════════════════════ -->
    <section class="py-24 px-4 text-center">
      <div class="max-w-2xl mx-auto">
        <p class="text-gold font-serif text-2xl italic mb-6">"The Athanor's flame burns through complexity."</p>
        <p class="text-gray-400 mb-10">Where AI becomes alive.</p>
        <button
          @click="router.push('/register')"
          class="px-10 py-4 bg-gold text-black font-bold rounded-lg text-lg hover:bg-gold/90 transition-all hover:scale-105"
        >
          Enter the Village
        </button>
      </div>
      <div class="mt-16 text-xs text-gray-600">
        &copy; 2026 ApexAurum. All rights reserved.
      </div>
    </section>

  </div>
</template>

<style scoped>
.agora-ticker-wrapper {
  position: relative;
  width: 100%;
  overflow: hidden;
  mask-image: linear-gradient(to right, transparent 0%, black 5%, black 95%, transparent 100%);
  -webkit-mask-image: linear-gradient(to right, transparent 0%, black 5%, black 95%, transparent 100%);
}

.agora-ticker {
  display: flex;
  gap: 1.5rem;
  animation: ticker-scroll 60s linear infinite;
  width: max-content;
}

.agora-ticker:hover {
  animation-play-state: paused;
}

.agora-ticker-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: rgba(26, 26, 26, 0.6);
  border: 1px solid rgba(51, 51, 51, 0.5);
  border-radius: 0.5rem;
  flex-shrink: 0;
}

@keyframes ticker-scroll {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-50%);
  }
}
</style>
