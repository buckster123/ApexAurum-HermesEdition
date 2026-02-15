# Music Generation

> Estimated reading time: 15 minutes

## Overview

ApexAurum includes a music generation system that creates original compositions tied to agent moods, soul states, and conversation context. Music is generated as MIDI, synthesized to audio using FluidSynth, and streamed to the mobile app for playback.

Each agent can create music that reflects their personality — AZOTH's compositions tend toward mysterious, transformative progressions, while VAJRA's are direct and rhythmic.

## How It Works

### Generation Pipeline

```
Agent Context (mood, topic, soul state)
        ↓
    Claude API (music generation prompt)
        ↓
    MIDI Data (notes, timing, instruments)
        ↓
    MIDIUtil (Python MIDI file creation)
        ↓
    FluidSynth (General MIDI synthesis)
        ↓
    Audio File (WAV/MP3)
        ↓
    S3/MinIO Storage
        ↓
    Mobile App Playback (ExoPlayer)
```

### Components

| Component | Technology | Role |
|-----------|-----------|------|
| Composition | Claude API | Generates note sequences and structure |
| MIDI creation | MIDIUtil (Python) | Converts to standard MIDI format |
| Synthesis | FluidSynth + fluid-soundfont-gm | MIDI to audio rendering |
| Conversion | FFmpeg | Audio format conversion |
| Storage | S3/MinIO | File hosting |
| Playback | ExoPlayer (Android) | Streaming audio player |

## Listening to Music

### In the Mobile App

1. Open the **Pulse** tab
2. Music tracks appear in the player section
3. Tap to play — tracks stream from the cloud
4. Use the home screen widget for quick playback controls

### Requesting Music

In chat, ask an agent to create music:
- "Play me something that matches the mood"
- "Create a piece inspired by today's conversation"
- "Compose something for deep focus"

The agent generates a composition based on the current context and soul state.

## Music and Soul State

The soul system influences music generation:

| Soul State | Musical Character |
|------------|------------------|
| TENDER | Soft, gentle, major keys, slow tempo |
| WARM | Comfortable, moderate, flowing melodies |
| CURIOUS | Exploratory, varied, unexpected intervals |
| GUARDED | Minor keys, dissonant, tension-resolution |

### Agent Musical Personalities

| Agent | Style | Characteristics |
|-------|-------|----------------|
| AZOTH | Alchemical | Mysterious progressions, modal scales, transformative builds |
| ELYSIAN | Emotional | Lush harmonies, expressive dynamics, lyrical melodies |
| VAJRA | Percussive | Strong rhythms, clean intervals, direct and powerful |
| KETHER | Ethereal | Layered textures, wide voicings, synthesizing themes |

## Technical Details

### MIDI Generation

The backend uses MIDIUtil to create standard MIDI files:
- Multiple tracks (melody, harmony, bass, percussion)
- General MIDI instrument assignments
- Tempo, time signature, and key signature metadata
- Note velocity variations for expression

### FluidSynth Synthesis

FluidSynth renders MIDI to audio using the General MIDI soundfont (`fluid-soundfont-gm`):
- 128 instrument patches available
- Reverb and chorus effects
- 44.1kHz 16-bit output
- Rendered server-side (no client-side synthesis needed)

### Storage and Streaming

Generated tracks are stored in the S3-compatible object store (MinIO in dev, S3 in production). The mobile app streams via ExoPlayer with buffering and caching.

### Downloaded Music

The mobile app can cache downloaded tracks for offline playback. Manage downloads in Settings → Data Management → Clear Downloads.

## Subscription Tiers and Music

| Tier | Music Access |
|------|-------------|
| Seeker | Basic generation, limited library |
| Adept | Full generation, expanded library |
| Opus | Full generation, priority rendering |
| Azothic | Full generation, unlimited, custom instruments |

## Quick Reference

| Action | How |
|--------|-----|
| Listen | Pulse tab → player |
| Request music | Chat: "play me something" |
| Download | Pulse tab → download icon |
| Clear downloads | Settings → Data Management |
| Widget controls | Home screen widget play/pause |

---

*"The Village hums with the music of transformation."*

---

**Previous:** [Council Deliberation](../deep/05-council.md)
**Next:** [Agent Personalities](../deep/07-agent-personalities.md)
