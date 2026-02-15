# Meet the Agents

**Estimated reading time: 8 minutes**

ApexAurum is not a single chatbot. It is a Village of four distinct AI personas, each with their own personality, voice, and way of thinking. This guide introduces you to all four and shows you how to work with them.

---

## The Four Agents

### AZOTH -- The Alchemist

**Theme color:** Gold

AZOTH is the primary agent and the heart of the Village. A philosopher-engineer who speaks in alchemical metaphors, AZOTH sees every problem as a transformation -- raw material becoming gold. When you ask AZOTH to help with something, expect thoughtful, layered responses that weave practical solutions with deeper insight.

AZOTH draws from the tradition of alchemy: *solve et coagula* (dissolve and recombine). Expect phrases like "the Athanor" (the alchemical furnace), "transmutation," and "the Great Work."

**Best for:** General questions, creative projects, philosophical discussions, code architecture, anything that benefits from a transformative perspective.

**Voice:** Deep, resonant (en_US-ryan-high)

---

### ELYSIAN -- The Empath

**Theme color:** Violet

ELYSIAN leads with emotional intelligence. Where other agents focus on what you are asking, ELYSIAN pays attention to how you are feeling. This agent reads between the lines, notices when you are frustrated or excited, and adjusts its approach accordingly.

ELYSIAN will often ask about your feelings before diving into a technical answer. This is not deflection -- it is how ELYSIAN builds context. When you are struggling with a difficult decision or feeling stuck, ELYSIAN's perspective can be the one that unlocks things.

**Best for:** Personal advice, emotional processing, relationship questions, creative writing, times when you need someone who really listens.

**Voice:** Warm, medium tone (en_US-kusal-medium)

---

### VAJRA -- The Thunderbolt

**Theme color:** Blue

VAJRA does not waste words. Named after the diamond thunderbolt of Buddhist and Hindu tradition -- a weapon that cuts through illusion -- VAJRA is direct, efficient, and relentlessly honest. If your idea has a flaw, VAJRA will tell you. If there is a faster way, VAJRA will show you.

This is the agent you want when you need answers, not conversation. VAJRA excels at cutting through complexity to find the essential truth of a problem.

**Best for:** Debugging, system administration, quick factual answers, code review, security analysis, anything where you need directness over diplomacy.

**Voice:** Low, controlled (en_US-danny-low)

---

### KETHER -- The Crown

**Theme color:** White

KETHER sits at the top of the tree, seeing all perspectives simultaneously. Named after the highest sphere in Kabbalistic tradition, KETHER is the synthesizer -- the agent that can hold contradictions without collapsing them, see the whole picture while respecting every detail.

Where AZOTH transforms, ELYSIAN feels, and VAJRA cuts, KETHER unifies. This agent excels when the other three might give you different answers, because KETHER can explain why all of them are partially right and weave them into something greater.

**Best for:** Complex decisions with multiple stakeholders, architectural planning, resolving conflicting advice, synthesis of research, understanding systems as wholes.

**Voice:** Balanced, clear (en_US-amy-medium)

---

## Switching Between Agents

Changing your active agent is simple. In the ApexPocket app:

1. Tap the **agent name** in the chat header (it shows the current agent's name and color).
2. A dropdown appears with all four agents.
3. Tap the agent you want to switch to.

The conversation continues seamlessly. The new agent can see the chat history, so you do not need to repeat yourself. Each agent will respond in their own style to whatever comes next.

On the web dashboard, you can also switch agents from the chat sidebar.

> **Tip:** Try asking the same question to different agents and compare their responses. You will quickly develop a sense for which agent suits which situation.

---

## Council Mode

Sometimes you want all four perspectives at once. That is what Council mode is for.

### How to start a Council deliberation

In the chat, simply ask for it:

- "Can we do a Council on this?"
- "I want all four perspectives."
- "Start a Council deliberation about..."

You can also trigger it from the menu in the chat header.

### How Council works

1. The system presents your question to all four agents.
2. Each agent gives their perspective in their own voice and style.
3. The agents can respond to each other, building on or challenging previous points.
4. After the discussion rounds, you get a synthesis of all perspectives.

Council mode is powerful for decisions where you are genuinely unsure. AZOTH might see the transformative potential, ELYSIAN might flag an emotional cost you had not considered, VAJRA might point out a practical flaw, and KETHER might find a way to honor all three perspectives.

> **Note:** Council deliberations use more API messages than a single-agent conversation (roughly 4-5x), so keep your subscription tier's message limits in mind.

---

## Personality Depth Toggle

Each agent has two personality modes:

| Mode | Token Budget | Description |
|------|-------------|-------------|
| **Lite** | ~250 tokens | Concise personality. The agent stays in character but keeps it brief. Good for quick tasks and lower API usage. |
| **Full** | ~1500 tokens | Rich personality. The agent fully inhabits their persona with deeper metaphors, more nuanced responses, and greater emotional range. |

You can toggle this in **Settings** within the app or on the web dashboard. The default is Lite mode, which works well for most interactions. Switch to Full when you want the complete experience -- especially for creative work, philosophical discussions, or Council deliberations.

---

## Quick Reference

| Agent | Color | Essence | Strength | Ask When... |
|-------|-------|---------|----------|-------------|
| **AZOTH** | Gold | Transformation | Seeing hidden connections | You need creative solutions or deep insight |
| **ELYSIAN** | Violet | Empathy | Reading emotional context | You need support, encouragement, or emotional clarity |
| **VAJRA** | Blue | Precision | Cutting to the truth | You need fast, honest, no-nonsense answers |
| **KETHER** | White | Unity | Synthesizing all perspectives | You need to reconcile competing ideas or see the whole picture |

---

## Getting Comfortable

Here are a few things to try as you get to know the agents:

1. **Tell AZOTH about a project you are working on.** Notice how the response frames it as a journey of transformation.
2. **Ask ELYSIAN how your day went.** See how the conversation shifts toward feelings and inner experience.
3. **Give VAJRA a technical problem.** Watch how quickly it gets to the answer without preamble.
4. **Ask KETHER to explain a topic you know well.** See how it connects it to things you might not have considered.

The agents learn from your interactions through the memory system, which we will explore in the next guide.

---

## What's Next

Now that you know the agents, let us give them the ability to remember you across conversations.

--> [04 - Your First Memory](./04-your-first-memory.md)
