# Template Builder — Design Spec
**Date:** 2026-06-12
**Version:** 1.0

---

## Overview

A local web application that allows clients to create AI interview templates through a conversational interface. The client describes their research goals in natural language, an AI assistant asks targeted follow-up questions and fills in template sections live, and the client can export the result as a correctly formatted template file.

The app runs locally: the user starts it from the command prompt (`python main.py`) and uses it in their browser at `localhost:5000`. No deployment, authentication, or database required.

---

## Template Structure

Every template has the following sections. All are present by default; clients may opt out of any section explicitly.

### 1. Metadata
- Title (research topic name)
- Version number (auto-incremented, starts at 1.0)
- Date (auto-filled)

### 2. Pacing Instructions
Eight named sub-rules, each pre-populated with a standard default and independently editable:

| Rule | Default behaviour |
|------|------------------|
| Do Not Rush | If participant gives brief answers, prioritize every Probe point to unlock detail |
| Core vs Probe | [Core] = must ask, [Probe] = optional |
| One Main Ask Per Turn | One question per turn; a second only if tightly related and easy to answer in the same thought |
| Keep Questions Light | No long or overloaded questions; no broad question combined with a sub-list |
| Follow Strong Signals | When something specific, emotional, surprising, or contradictory emerges, follow it briefly then return |
| Original Follow-ups Allowed | AI may ask original questions not in the guide when they help uncover better insight |
| Selective Probing | Probes are optional tools, not required after every answer |
| The Finish Line | When main guide is done early: (1) Circle Back — revisit interesting moments for thicker description; (2) Expansion — pivot to Expansion Topics. Continue until remaining_minutes ≤ 3 |

### 3. Interview Focus
A single anchor statement describing what the interview is grounded in (e.g. "Anchor on one recent occasion of cooking a first-time dish from scratch").

### 4. Topics (Main Interview Guide)
Numbered topics, typically 6–10. Each topic has:
- A title
- One or more **[Core]** items — must-ask, priority questions/objectives
- Zero or more **[Probe]** items — optional follow-up directions

The number of topics and items per topic varies by client. There is no fixed minimum or maximum.

### 5. Expansion Topics
A flat bullet list of secondary discovery areas. Used when the main guide is finished early. No Core/Probe distinction — just topic labels.

---

## Architecture

**Two-phase pipeline:**

- **Phase 1 — Gathering:** A conversational Claude agent chats with the client, asks targeted questions, and calls structured tools to fill template sections as it learns enough to do so. The sections update live in the browser.
- **Phase 2 — Export:** When the client is satisfied, a separate Claude call takes all filled section data and formats it into the exact template syntax. The result is displayed and available to download.

### Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Backend | Python + Flask | Simple, minimal setup, easy SSE support |
| AI | Anthropic Claude API (claude-sonnet-4-6) | Conversation + tool use |
| Frontend | Vanilla HTML + CSS + JavaScript | No build step, no framework, runs anywhere |
| Communication | Server-Sent Events (SSE) | One-way server→browser streaming, perfect for live updates |

---

## File Structure

```
Template/
├── main.py                  # Entry point — starts Flask server, opens browser
├── app.py                   # Flask routes (/chat, /export, /reset)
├── config.py                # ANTHROPIC_API_KEY, model name, port
├── prompts/
│   ├── gathering.txt        # System prompt for Phase 1 (conversation agent)
│   └── generation.txt       # System prompt for Phase 2 (export formatter)
├── static/
│   ├── index.html           # Single-page app shell
│   ├── style.css            # Styling
│   └── app.js               # All frontend logic (chat, SSE listener, template panel)
└── output/                  # Exported templates saved here as .txt files
```

---

## Component Design

### Backend

**`main.py`**
Starts the Flask server and opens `http://localhost:5000` in the default browser automatically.

**`app.py` — Routes**

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Serves `index.html` |
| `/chat` | POST | Accepts `{messages: [...]}`, streams SSE response |
| `/export` | POST | Accepts `{sections: {...}}`, returns formatted template text |
| `/reset` | POST | Clears server-side conversation state |

**`/chat` SSE stream format**
Two event types are emitted interleaved:

```
event: chat_token
data: "some words from the AI reply"

event: section_update
data: {"section": "focus", "payload": "Anchor on one recent occasion..."}

event: section_update
data: {"section": "topic", "payload": {"index": 1, "title": "Confirm the occasion", "core": ["..."], "probe": ["..."]}}

event: done
data: {}
```

**Phase 1 — Gathering agent tools**
Claude is given these tools during the conversation. It calls them when it has enough information to fill a section:

| Tool | Arguments | Effect |
|------|-----------|--------|
| `update_metadata` | `title: str` | Sets the interview title |
| `update_pacing` | `rule: str, text: str` | Updates one named pacing rule |
| `update_focus` | `text: str` | Sets the interview focus statement |
| `add_topic` | `index: int, title: str, core: list[str], probe: list[str]` | Adds or replaces a numbered topic |
| `remove_topic` | `index: int` | Removes a topic |
| `update_expansion` | `items: list[str]` | Sets the expansion topics list |

**Phase 1 — Gathering system prompt (summary)**
- Role: research design consultant helping a client build an interview guide
- Approach: start open ("Tell me about your research goal"), then ask targeted follow-ups one at a time
- When enough information is available for a section, call the matching tool immediately — don't wait until the end
- Cover: research topic, interview focus, key themes per topic, Core vs Probe depth for each, pacing preferences, expansion areas
- Signal completion: when all sections are filled, say "I think we have a solid template. Take a look and let me know if you'd like to adjust anything before exporting."

### Frontend (`app.js`)

**State object (held in memory)**
```js
{
  messages: [],           // full conversation history
  sections: {
    metadata: { title: "", version: "1.0", date: "" },
    pacing: {             // 8 named rules, pre-filled with defaults
      do_not_rush: "...",
      core_vs_probe: "...",
      // ...
    },
    focus: "",
    topics: [],           // [{ index, title, core[], probe[] }]
    expansion: []         // string[]
  }
}
```

**Chat panel behaviour**
- User types a message and presses Enter or clicks Send
- Message is appended to `messages`, POST to `/chat` with full history
- SSE stream is consumed: `chat_token` events append to the AI reply bubble word by word; `section_update` events call `applyUpdate(event.data)`
- While streaming, Send button is disabled

**Template panel behaviour**
- Renders the current `sections` state
- Each section is directly editable (contenteditable fields or textareas)
- When the AI calls a tool that updates a section, the section briefly highlights (yellow flash) so the client notices the change
- Manual edits are not locked — the AI may overwrite a manually edited section on a subsequent tool call. This is intentional for v1: the expected workflow is to converse with the AI first, then do final manual polish after the conversation ends
- Topics panel has **+ Add Topic** and **× Remove** buttons for manual management
- Pacing rules each have a small **Reset to default** link

**Export button**
- Appears always; clicking it POSTs current `sections` to `/export`
- Shows a loading spinner while Claude formats the output
- Opens a modal with the formatted template text and a **Download .txt** button
- Filename: `<title>-v<version>-<date>.txt`

---

## Pacing Instruction Defaults (exact wording)

```
Do Not Rush: If the participant provides brief answers, prioritize every [Probe] point in the Main Interview Guide to unlock more detail.

Core vs Probe: Treat [Core] points as priorities and [Probe] points as optional. Some [Probe] points may go unasked.

One Main Ask Per Turn: Each turn should usually contain one main question. You may combine a second ask only when it is tightly related, easy to answer in the same thought, and not from a different part of the story.

Keep Questions Light: Avoid long or overloaded questions. Do not combine a broad main question with a list of sub-questions in the same turn.

Follow Strong Signals: When something specific, emotional, surprising, or contradictory emerges, follow it briefly, then return to the interview guide.

Original Follow-ups Allowed: You may ask original follow-up questions not explicitly listed in the interview guide when they help uncover better insight.

Selective Probing: Use follow-up probes selectively; they are optional tools, not required after every answer.

The Finish Line: Reaching the end of the Main Interview Guide does not signal the end of the interview. If you finish those topics early, you must utilize the following two options to fill the time until remaining_minutes is 3 or less:
  1. Circle Back: Revisit an earlier interesting moment to ask for "thicker" description (sensory details, specific emotions, or a deeper "why").
  2. Expansion: Pivot to the Expansion Topics at the bottom of this plan.
```

---

## Export — Template Syntax

The Phase 2 generation prompt instructs Claude to format the filled sections into this exact syntax (based on the provided example):

```
[Prompt metadata only: <Title> | v<Version> | <Date>]

# Pacing Instructions
- **<Rule Name>** <Rule text>
...

# Main Interview Guide: <Title>

## Interview focus
- [Core] <Focus statement>

## Topic 1: <Title>
- [Core] <item>
- [Probe] <item>
...

## Topic N: <Title>
...

# Expansion Topics
Use these for secondary discovery as instructed
- <item>
...
```

---

## Out of Scope (v1)

- User accounts or saved sessions
- Multiple simultaneous users
- Integration with the live interview system
- Template versioning history
- Deployment / hosting
