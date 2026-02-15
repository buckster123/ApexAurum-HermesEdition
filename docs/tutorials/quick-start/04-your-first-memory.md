# Your First Memory

**Estimated reading time: 7 minutes**

AI conversations normally vanish when you close the window. CerebroCortex changes that. It gives the agents a persistent memory that spans conversations, spans sessions, and can even be shared between agents. This guide walks you through storing your first memory and seeing how the system works.

---

## What is CerebroCortex?

CerebroCortex is ApexAurum's memory system. It is a graph database where each memory is a node, and memories can be linked to each other by meaning, time, cause, or emotion. When an agent stores a memory, it goes through a pipeline:

1. **Classification** -- the system determines what kind of memory it is.
2. **Deduplication** -- if a very similar memory already exists, it merges rather than duplicates.
3. **Embedding** -- the memory is converted to a vector for semantic search.
4. **Linking** -- the system connects it to related memories already in the graph.

The result is that agents do not just remember isolated facts. They build a web of interconnected knowledge about you and your world.

---

## Step 1: Store a Memory

Open a chat with any agent in the ApexPocket app (or the web dashboard). Tell the agent something worth remembering:

```
Remember that my favorite color is blue.
```

The agent will confirm that it stored this memory. Behind the scenes, it called the `cortex_remember` tool, which classified this as a **semantic** memory (a fact about you) and stored it in the graph.

Try a few more:

```
Remember that I have a meeting every Tuesday at 10am.
```

```
Remember that I prefer dark mode in all my apps.
```

```
Remember that my dog's name is Luna.
```

Each of these becomes a node in your personal memory graph.

> **Tip:** You do not always have to say "remember." The agents are also trained to notice important information during normal conversation and store it proactively. But explicit "remember this" requests guarantee storage.

---

## Step 2: Recall a Memory

Now test retrieval. Start a **new conversation** (this is important -- you want to prove the memory persists beyond a single chat session).

Ask the agent:

```
What's my favorite color?
```

The agent will use the `cortex_recall` tool to search its memory graph semantically. It should find the "favorite color is blue" memory and tell you.

Try some variations:

```
Do you know anything about my schedule?
```

```
What pets do I have?
```

The recall is semantic, not keyword-based. This means the agent can find relevant memories even if you phrase the question differently from how you originally stated the fact. Asking "What do I like to look at?" could surface the color preference. Asking "Any animals in my life?" could surface the dog memory.

---

## Step 3: Browse Your Memories

In the ApexPocket app, navigate to the **Memories** tab (the brain icon in the bottom navigation). Here you can see all stored memories in a scrollable list.

Each memory card shows:

- **Content** -- what was stored
- **Type badge** -- the classification (episodic, semantic, procedural, etc.)
- **Agent** -- which agent stored it
- **Timestamp** -- when it was created
- **Salience** -- how important the system considers it (0.0 to 1.0)

You can pull down to refresh the list and use the search bar at the top for semantic search.

---

## Step 4: Explore Memory Types

CerebroCortex classifies memories into several types. Understanding these helps you work more effectively with the system.

| Type | What It Stores | Example |
|------|---------------|---------|
| **Semantic** | Facts and knowledge | "User's favorite color is blue" |
| **Episodic** | Events and experiences | "User had a great day at the park on Saturday" |
| **Procedural** | How-to knowledge and workflows | "To deploy the app: git push, wait for CI, check Railway logs" |
| **Affective** | Emotional patterns and preferences | "User gets frustrated when apps load slowly" |
| **Prospective** | Future intentions and reminders | "User wants to start learning Rust next month" |
| **Schematic** | Patterns and principles derived from multiple memories | "User prefers concise explanations over lengthy ones" |

The system classifies automatically. You do not need to tag memories yourself, although you can add tags if you want to organize things further.

---

## Step 5: See the Graph

In the Memories tab, look for the **Graph** toggle or view option. This shows your memories as a visual network:

- Each **node** is a memory
- Each **line** between nodes is a link
- Links have types: temporal, causal, semantic, contextual, supports, contradicts

Tap a node to read the full memory. Long-press to see its connections.

The graph grows organically as you interact with the agents. Over time, clusters form around topics you discuss frequently. You might see a cluster of work-related memories connected to a cluster of personal preferences, with bridge nodes linking them.

---

## Agent Filtering

At the top of the Memories screen, you will see filter chips:

| Chip | Shows |
|------|-------|
| **All** | Every memory from every agent |
| **AZO** | Only AZOTH's memories |
| **ELY** | Only ELYSIAN's memories |
| **VAJ** | Only VAJRA's memories |
| **KET** | Only KETHER's memories |

This is useful because different agents notice and remember different things. ELYSIAN might store memories about your emotional patterns, while VAJRA might remember your technical preferences. Filtering lets you see what each agent has learned about you.

---

## How Agents Share Memories

By default, memories are **shared** across all agents. When AZOTH learns your favorite color, ELYSIAN can recall it too. This means you do not have to repeat yourself when switching agents.

There are three visibility levels:

| Level | Who Can See It |
|-------|---------------|
| **Shared** | All four agents (default) |
| **Private** | Only the agent that stored it |
| **Thread** | Only within the current conversation thread |

Most memories are shared, which gives every agent a consistent picture of who you are. Private memories are useful for agent-specific context that would not make sense for the others.

---

## Memory Persistence Across Sessions

Here is the key thing that makes CerebroCortex different from normal AI chat memory: it persists indefinitely. You can:

- Close the app completely and come back days later -- memories are still there.
- Switch between phone and web dashboard -- same memory graph.
- Talk to different agents in different conversations -- they all access the same memories.
- Even trigger a **Dream cycle** (an offline consolidation process) that strengthens connections between related memories and prunes low-value ones.

Memories live in the cloud on the ApexAurum backend, with a local cache on your phone for fast access and offline viewing.

---

## Things to Try

Now that you understand the basics, experiment:

1. **Tell an agent about your work.** A few sentences about what you do. Then in a new conversation, ask it to help you with a work problem and notice how it uses that context.

2. **Share something personal with ELYSIAN.** ELYSIAN stores affective memories -- things about how you feel, what matters to you. These subtly shape how all agents interact with you.

3. **Ask VAJRA for a technical recommendation.** Then later, ask the same question again and watch how it remembers its previous analysis.

4. **Create a deliberate contradiction.** Tell one agent your favorite food is pizza, then tell another it is sushi. See how the system handles conflicting memories.

---

## What's Next

You have a connected Pi, a paired phone, agents who know you, and a memory system that persists. Now let us put those SensorHead sensors to work.

--> [05 - SensorHead Basics](./05-sensorhead-basics.md)
