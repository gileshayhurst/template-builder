# Interactive Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add collapsible template sections, a settings strip with Depth/Breadth and Duration controls, and quick-action chat buttons to the Template Builder frontend.

**Architecture:** All changes are purely frontend — no new routes or API calls. `state.collapsedSections` (a `Set`) tracks collapsed state; `renderTemplate()` delegates to `renderSettingsStrip()` for the new settings strip div. The duration estimate runs as a JS formula on every `applyUpdate()` call.

**Tech Stack:** Vanilla JS, CSS, Jinja HTML — no build step. Backend: Flask/Python (unchanged). Tests: pytest for existing backend routes (must still pass).

---

## File Map

| File | What changes |
|------|-------------|
| `static/app.js` | Add `PACING_DEPTH_PRESETS`; extend `state`; add `toggleSection`, `applyDepthPreset`, `getDepthPreset`, `estimateDuration`, `setDurationTarget`, `updateDurationDisplay`, `renderSettingsStrip`, `sendQuickAction`; update `sectionBlock`, `renderPacing`, `renderTopicBlock`, `renderTopics`, `renderTemplate`, `resetPacing`, `applyUpdate`, `streamFromServer` |
| `static/style.css` | Add chevron/collapse styles, settings strip layout, duration track styles, quick-action pill styles |
| `templates/index.html` | Add `<div id="settings-strip">` between panel-header and template-sections; add quick-action button row above textarea |

---

## Task 1: Add PACING_DEPTH_PRESETS constant and extend state

**Files:**
- Modify: `static/app.js` (constants block, lines 1–37)

- [ ] **Step 1: Add PACING_DEPTH_PRESETS after PACING_LABELS and extend state**

Replace the CONSTANTS and STATE sections (lines 1–37) with the following. The `balanced` preset spreads `PACING_DEFAULTS` so they stay in sync automatically.

```js
// ─── CONSTANTS ────────────────────────────────────────────────────────────────

const PACING_DEFAULTS = {
  do_not_rush: "If the participant provides brief answers, prioritize every [Probe] point in the Main Interview Guide to unlock more detail.",
  core_vs_probe: "Treat [Core] points as priorities and [Probe] points as optional. Some [Probe] points may go unasked.",
  one_ask_per_turn: "Each turn should usually contain one main question. You may combine a second ask only when it is tightly related, easy to answer in the same thought, and not from a different part of the story.",
  keep_light: "Avoid long or overloaded questions. Do not combine a broad main question with a list of sub-questions in the same turn.",
  follow_signals: "When something specific, emotional, surprising, or contradictory emerges, follow it briefly, then return to the interview guide.",
  original_followups: "You may ask original follow-up questions not explicitly listed in the interview guide when they help uncover better insight.",
  selective_probing: "Use follow-up probes selectively; they are optional tools, not required after every answer.",
  finish_line: "Reaching the end of the Main Interview Guide does not signal the end of the interview. If you finish those topics early, you must utilize the following two options to fill the time until remaining_minutes is 3 or less:\n  1. Circle Back: Revisit an earlier interesting moment to ask for \"thicker\" description (sensory details, specific emotions, or a deeper \"why\").\n  2. Expansion: Pivot to the Expansion Topics at the bottom of this plan."
};

const PACING_LABELS = {
  do_not_rush: "Do Not Rush",
  core_vs_probe: "Core vs. Probe",
  one_ask_per_turn: "One Main Ask Per Turn",
  keep_light: "Keep Questions Light",
  follow_signals: "Follow Strong Signals",
  original_followups: "Original Follow-ups Allowed",
  selective_probing: "Selective Probing",
  finish_line: "The Finish Line"
};

const PACING_DEPTH_PRESETS = {
  breadth: {
    do_not_rush: "Keep the conversation moving. If a participant gives a brief answer and the response is clear, accept it and move on. Use probes only when an answer is unclear or incomplete.",
    core_vs_probe: "Treat [Core] points as must-ask items. Skip most [Probe] points unless they arise naturally. Prioritise covering all topics over depth in any one area.",
    one_ask_per_turn: "Each turn should contain exactly one question. Do not combine follow-up questions or add sub-questions.",
    keep_light: "Keep questions short and easy to answer. Avoid anything that requires extended reflection.",
    follow_signals: "When something interesting emerges, note it briefly and return immediately to the guide. Do not follow tangents.",
    original_followups: "Stick closely to the interview guide. Only ask questions not in the guide when explicitly necessary to clarify something.",
    selective_probing: "Use probes sparingly. Prefer moving to the next topic over dwelling on the current one.",
    finish_line: "Reaching the end of the Main Interview Guide signals the end of the interview. If a few minutes remain, close warmly. Do not pivot to Expansion Topics."
  },
  slightly_broad: {
    do_not_rush: "Keep the conversation flowing. Use probes when an answer seems incomplete, but do not linger. Accept brief answers for straightforward questions.",
    core_vs_probe: "Treat [Core] points as priorities. Use [Probe] points selectively — when an answer is thin or a topic clearly needs more colour.",
    one_ask_per_turn: "Each turn should usually contain one main question. You may add a second only when it flows naturally from the first answer.",
    keep_light: "Avoid long or overloaded questions. Do not combine a broad main question with a list of sub-questions in the same turn.",
    follow_signals: "When something specific or emotional emerges, follow it with one brief follow-up, then return to the guide.",
    original_followups: "You may ask original follow-up questions when they would clearly deepen understanding. Keep them brief.",
    selective_probing: "Use follow-up probes selectively. Prefer coverage over depth when time is limited.",
    finish_line: "Reaching the end of the Main Interview Guide does not necessarily signal the end of the interview. If time remains, revisit one interesting moment briefly before closing."
  },
  balanced: { ...PACING_DEFAULTS },
  slightly_deep: {
    do_not_rush: "If a participant gives brief answers, use [Probe] points to unlock more detail. Take time on answers that hint at something richer.",
    core_vs_probe: "Treat [Core] points as priorities and [Probe] points as important tools. Use most probes unless time pressure is significant.",
    one_ask_per_turn: "Each turn should usually contain one main question. You may combine a second when it is tightly related, easy to answer in the same thought, and not from a different part of the story.",
    keep_light: "Avoid long or overloaded questions. Do not combine a broad main question with a list of sub-questions in the same turn.",
    follow_signals: "When something specific, emotional, surprising, or contradictory emerges, follow it — ask a clarifying or deepening question — then return to the guide.",
    original_followups: "Ask original follow-up questions when they would help uncover better insight. Good intuition is an asset here.",
    selective_probing: "Use probes thoughtfully. When an answer feels thin or opens a door, follow it. Do not skip probes by default.",
    finish_line: "Reaching the end of the Main Interview Guide does not signal the end of the interview. Use Circle Back and Expansion Topics to fill remaining time until remaining_minutes is 3 or less."
  },
  deep: {
    do_not_rush: "Prioritize depth over coverage. If the participant gives brief answers, use every available [Probe] point to unlock detail. Never accept a thin answer when a richer one is possible.",
    core_vs_probe: "Treat both [Core] and [Probe] points as essential. Use all probes unless the participant has already addressed them or time is critically short.",
    one_ask_per_turn: "Each turn should contain one focused question. You may add a tightly related follow-up when it deepens the current answer rather than changing the subject.",
    keep_light: "Keep individual questions focused and clear, but do not shy away from questions that require genuine reflection or pause.",
    follow_signals: "When something specific, emotional, surprising, or contradictory emerges, follow it fully. Ask multiple deepening questions before returning to the guide. These moments often yield the richest insight.",
    original_followups: "Actively ask original follow-up questions not in the guide whenever they would surface deeper understanding. Treat the guide as a floor, not a ceiling.",
    selective_probing: "Use every relevant probe. Probes are not optional tools — they are the primary mechanism for achieving depth. Only skip a probe if the participant has already fully addressed it.",
    finish_line: "Reaching the end of the Main Interview Guide does not signal the end of the interview. You must use Circle Back and Expansion Topics to fill the time until remaining_minutes is 3 or less. Circle Back is particularly important at this depth — revisit every moment that had depth potential and push for sensory detail, specific emotions, and deeper explanation."
  }
};

// ─── STATE ────────────────────────────────────────────────────────────────────

const state = {
  streaming: false,
  exportFilename: "",
  depthSliderValue: 50,
  durationTarget: 0,
  collapsedSections: new Set(["settings"]),
  sections: {
    metadata: { title: "", version: "1.0", date: new Date().toISOString().split("T")[0] },
    pacing: { ...PACING_DEFAULTS },
    focus: "",
    topics: [],
    expansion: []
  }
};
```

- [ ] **Step 2: Verify no console errors**

Run `python main.py`. Open browser at `http://localhost:5000`. Open DevTools console — no errors should appear. The page should look identical to before.

- [ ] **Step 3: Commit**

```bash
git add static/app.js
git commit -m "feat: add PACING_DEPTH_PRESETS constant and extend state for interactive controls"
```

---

## Task 2: Collapsible sections — toggleSection() + sectionBlock() + CSS

**Files:**
- Modify: `static/app.js` (add `toggleSection`, update `sectionBlock` and all its call sites)
- Modify: `static/style.css` (chevron + collapse styles)

- [ ] **Step 1: Replace `sectionBlock()` and add `toggleSection()` in app.js**

Find `sectionBlock` (currently around line 202). Replace it and add `toggleSection` just above it:

```js
function toggleSection(key) {
  if (state.collapsedSections.has(key)) {
    state.collapsedSections.delete(key);
  } else {
    state.collapsedSections.add(key);
  }
  renderTemplate();
}

function sectionBlock(id, title, bodyEl, collapseKey) {
  const block = document.createElement("div");
  block.className = "section-block";
  block.id = id;

  const header = document.createElement("div");
  header.className = "section-title";

  if (collapseKey) {
    const collapsed = state.collapsedSections.has(collapseKey);
    header.innerHTML = `<span class="section-chevron">${collapsed ? "▸" : "▾"}</span><span>${escHtml(title)}</span>`;
    header.style.cursor = "pointer";
    header.onclick = () => toggleSection(collapseKey);
  } else {
    header.textContent = title;
  }

  block.appendChild(header);

  if (!collapseKey || !state.collapsedSections.has(collapseKey)) {
    const body = document.createElement("div");
    body.className = "section-body";
    body.appendChild(bodyEl);
    block.appendChild(body);
  }

  return block;
}
```

- [ ] **Step 2: Update all sectionBlock call sites to pass collapseKey**

Find these four lines and update them:

```js
// in renderMetadata():
return sectionBlock("section-metadata", "Metadata", body, "metadata");

// in renderPacing():
return sectionBlock("section-pacing", "Pacing Instructions", body, "pacing");

// in renderFocus():
return sectionBlock("section-focus", "Interview Focus", body, "focus");

// in renderTopics():
return sectionBlock("section-topics", `Topics (${state.sections.topics.length})`, body, "topics");

// in renderExpansion():
return sectionBlock("section-expansion", "Expansion Topics", body, "expansion");
```

- [ ] **Step 3: Add chevron and collapse CSS to style.css**

Add after the `.section-body` rule (around line 79):

```css
.section-title { cursor: default; user-select: none; }
.section-title[style*="cursor: pointer"] { }
.section-chevron { margin-right: 6px; font-size: 10px; color: #999; display: inline-block; width: 10px; }
```

- [ ] **Step 4: Run app and verify**

Run `python main.py`. Open browser. Each section header should show a ▾ chevron. Click any header — it should collapse (body disappears, chevron becomes ▸). Click again — it expands.

- [ ] **Step 5: Commit**

```bash
git add static/app.js static/style.css
git commit -m "feat: collapsible template sections with chevron toggles"
```

---

## Task 3: Per-rule pacing collapse and per-topic collapse

**Files:**
- Modify: `static/app.js` (`renderPacing` and `renderTopicBlock`)

- [ ] **Step 1: Update renderPacing() to wrap each rule in a collapsible block**

Replace the entire `renderPacing()` function:

```js
function renderPacing() {
  const outer = document.createElement("div");
  for (const [key, label] of Object.entries(PACING_LABELS)) {
    const ruleKey = `pacing-${key}`;
    const collapsed = state.collapsedSections.has(ruleKey);

    const ruleBlock = document.createElement("div");
    ruleBlock.className = "pacing-rule";

    const ruleHeader = document.createElement("div");
    ruleHeader.className = "pacing-rule-header";
    ruleHeader.innerHTML = `<span class="section-chevron">${collapsed ? "▸" : "▾"}</span><span>${escHtml(label)}</span>`;
    ruleHeader.onclick = () => toggleSection(ruleKey);
    ruleBlock.appendChild(ruleHeader);

    if (!collapsed) {
      const ruleBody = document.createElement("div");
      ruleBody.innerHTML = `
        <textarea oninput="state.sections.pacing['${key}'] = this.value">${escHtml(state.sections.pacing[key])}</textarea>
        <button class="reset-link" onclick="resetPacing('${key}')">Reset to preset</button>`;
      ruleBlock.appendChild(ruleBody);
    }

    outer.appendChild(ruleBlock);
  }
  return sectionBlock("section-pacing", "Pacing Instructions", outer, "pacing");
}
```

- [ ] **Step 2: Update renderTopicBlock() to add per-topic collapse**

Replace the entire `renderTopicBlock()` function:

```js
function renderTopicBlock(topic) {
  const topicKey = `topic-${topic.index}`;
  const collapsed = state.collapsedSections.has(topicKey);

  const block = document.createElement("div");
  block.className = "topic-block";

  const topicHeader = document.createElement("div");
  topicHeader.className = "topic-block-header";
  topicHeader.innerHTML = `
    <span class="section-chevron">${collapsed ? "▸" : "▾"}</span>
    <input value="${escHtml(topic.title)}" placeholder="Topic title…"
      oninput="updateTopicField(${topic.index}, 'title', this.value)"
      onclick="event.stopPropagation()">
    <button class="remove-topic-btn" onclick="event.stopPropagation(); removeTopicManually(${topic.index})">×</button>`;
  topicHeader.onclick = () => toggleSection(topicKey);
  block.appendChild(topicHeader);

  if (!collapsed) {
    const body = document.createElement("div");
    body.className = "topic-block-body";

    const list = document.createElement("div");
    list.className = "items-list";
    topic.core.forEach((text, i) => list.appendChild(renderItemRow("core", topic.index, i, text)));
    topic.probe.forEach((text, i) => list.appendChild(renderItemRow("probe", topic.index, i, text)));
    body.appendChild(list);

    const btnRow = document.createElement("div");
    btnRow.style.cssText = "display:flex;gap:6px;margin-top:4px;";
    const ac = document.createElement("button");
    ac.className = "add-item-btn"; ac.textContent = "+ Core item";
    ac.onclick = () => addItem(topic.index, "core");
    const ap = document.createElement("button");
    ap.className = "add-item-btn"; ap.textContent = "+ Probe item";
    ap.onclick = () => addItem(topic.index, "probe");
    btnRow.appendChild(ac); btnRow.appendChild(ap);
    body.appendChild(btnRow);

    block.appendChild(body);
  }

  return block;
}
```

- [ ] **Step 3: Add CSS for new pacing-rule and topic-block-header elements**

Add to `style.css`:

```css
.pacing-rule-header {
  display: flex; align-items: center; cursor: pointer;
  font-size: 11px; font-weight: 600; color: #555;
  padding: 4px 0; user-select: none;
}
.pacing-rule-header:hover { color: #4f46e5; }
.pacing-rule-header .section-chevron { color: #aaa; }
.pacing-rule textarea {
  width: 100%; border: 1px solid #ddd; border-radius: 4px;
  padding: 6px 8px; font-size: 12px; font-family: inherit; resize: vertical; min-height: 48px; outline: none;
  margin-top: 4px;
}
.pacing-rule textarea:focus { border-color: #4f46e5; }

.topic-block-header {
  display: flex; align-items: center; gap: 6px;
  cursor: pointer; padding-bottom: 4px; user-select: none;
}
.topic-block-header input {
  flex: 1; border: none; border-bottom: 1px solid #ddd;
  padding: 3px 0; font-weight: 600; font-size: 13px; outline: none;
  font-family: inherit; cursor: text; background: transparent;
}
.topic-block-header input:focus { border-bottom-color: #4f46e5; }
.topic-block-body { padding-top: 8px; }
```

Also remove the old `.topic-title input` and `.pacing-rule label` rules that are now superseded (search for them and delete):

```css
/* DELETE this block: */
.topic-title input {
  width: 100%; border: none; border-bottom: 1px solid #ddd;
  padding: 3px 0; font-weight: 600; font-size: 13px; outline: none; margin-bottom: 8px; font-family: inherit;
}
/* DELETE this block: */
.pacing-rule label { font-size: 11px; font-weight: 600; color: #555; display: block; margin-bottom: 3px; }
```

- [ ] **Step 4: Run app and verify**

Run `python main.py`. Expand the Pacing Instructions section. Each individual pacing rule should have its own ▾ chevron. Clicking a rule label collapses that rule's textarea. Expand Topics and verify each topic can be independently collapsed.

- [ ] **Step 5: Commit**

```bash
git add static/app.js static/style.css
git commit -m "feat: per-rule pacing collapse and per-topic collapse"
```

---

## Task 4: Settings strip — HTML div + renderSettingsStrip() shell + CSS layout

**Files:**
- Modify: `templates/index.html`
- Modify: `static/app.js` (add `renderSettingsStrip`, call from `renderTemplate`)
- Modify: `static/style.css`

- [ ] **Step 1: Add settings-strip div to index.html**

In `templates/index.html`, add `<div id="settings-strip"></div>` between `.panel-header` and `#template-sections`:

```html
    <div class="panel template-panel">
      <div class="panel-header">
        <span>Live Template</span>
        <button class="export-btn" onclick="exportTemplate()">Export Template</button>
      </div>
      <div id="settings-strip"></div>
      <div id="template-sections"></div>
    </div>
```

- [ ] **Step 2: Add renderSettingsStrip() to app.js**

Add this function just before `renderTemplate()`:

```js
function renderSettingsStrip() {
  const strip = document.getElementById("settings-strip");
  if (!strip) return;
  const collapsed = state.collapsedSections.has("settings");
  strip.innerHTML = `
    <div class="settings-strip-header" onclick="toggleSection('settings')">
      <span class="section-chevron">${collapsed ? "▸" : "▾"}</span>
      <span>Settings</span>
    </div>
    ${collapsed ? "" : `<div class="settings-strip-body"></div>`}
  `;
}
```

- [ ] **Step 3: Call renderSettingsStrip() from renderTemplate()**

Update `renderTemplate()` to call it first:

```js
function renderTemplate() {
  renderSettingsStrip();
  const container = document.getElementById("template-sections");
  container.innerHTML = "";
  container.appendChild(renderMetadata());
  container.appendChild(renderPacing());
  container.appendChild(renderFocus());
  container.appendChild(renderTopics());
  container.appendChild(renderExpansion());
}
```

- [ ] **Step 4: Add settings strip CSS to style.css**

Add after the `.panel-header` rule block:

```css
#settings-strip {
  flex-shrink: 0;
  border-bottom: 1px solid #e0e0e0;
  background: #fafafa;
}
.settings-strip-header {
  display: flex; align-items: center; gap: 4px;
  padding: 6px 16px; cursor: pointer; user-select: none;
  font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.05em; color: #888;
}
.settings-strip-header:hover { color: #444; }
.settings-strip-body {
  display: flex; gap: 20px;
  padding: 10px 16px 14px;
  border-top: 1px solid #e0e0e0;
}
.settings-control { flex: 1; min-width: 0; }
.settings-control-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.06em; color: #888; margin-bottom: 6px;
}
```

- [ ] **Step 5: Run app and verify**

Run `python main.py`. A "▾ Settings" header should appear between the template panel header and the sections. Clicking it should collapse/expand an empty body. The strip starts collapsed (▸ Settings).

- [ ] **Step 6: Commit**

```bash
git add templates/index.html static/app.js static/style.css
git commit -m "feat: add settings strip shell with collapse toggle"
```

---

## Task 5: Depth slider — wire to PACING_DEPTH_PRESETS

**Files:**
- Modify: `static/app.js` (add `getDepthPreset`, `applyDepthPreset`; update `resetPacing`; flesh out `renderSettingsStrip`)

- [ ] **Step 1: Add getDepthPreset() and applyDepthPreset() to app.js**

Add these two functions just after the `PACING_DEPTH_PRESETS` constant:

```js
function getDepthPreset(value) {
  const key = { 0: "breadth", 25: "slightly_broad", 50: "balanced", 75: "slightly_deep", 100: "deep" }[value];
  return PACING_DEPTH_PRESETS[key] || PACING_DEPTH_PRESETS.balanced;
}

function applyDepthPreset(value) {
  state.depthSliderValue = value;
  state.sections.pacing = { ...getDepthPreset(value) };
  renderTemplate();
}
```

- [ ] **Step 2: Update resetPacing() to reset to current preset**

Replace the existing `resetPacing` function:

```js
function resetPacing(rule) {
  state.sections.pacing[rule] = getDepthPreset(state.depthSliderValue)[rule];
  renderTemplate();
}
```

- [ ] **Step 3: Add depth slider HTML to renderSettingsStrip()**

Replace the entire `renderSettingsStrip()` function:

```js
function renderSettingsStrip() {
  const strip = document.getElementById("settings-strip");
  if (!strip) return;
  const collapsed = state.collapsedSections.has("settings");

  const depthLabels = { 0: "Breadth", 25: "Slightly Broad", 50: "Balanced", 75: "Slightly Deep", 100: "Deep" };
  const depthLabel = depthLabels[state.depthSliderValue] || "Balanced";

  strip.innerHTML = `
    <div class="settings-strip-header" onclick="toggleSection('settings')">
      <span class="section-chevron">${collapsed ? "▸" : "▾"}</span>
      <span>Settings</span>
    </div>
    ${collapsed ? "" : `
    <div class="settings-strip-body">
      <div class="settings-control">
        <div class="settings-control-label">Depth vs. Breadth</div>
        <input type="range" class="depth-slider" min="0" max="100" step="25"
          value="${state.depthSliderValue}"
          oninput="applyDepthPreset(parseInt(this.value))">
        <div class="depth-slider-labels">
          <span>Breadth</span>
          <span class="depth-active-label">${escHtml(depthLabel)}</span>
          <span>Deep</span>
        </div>
      </div>
      <div class="settings-control" id="duration-control">
        <div class="settings-control-label">Interview Duration</div>
        <p style="font-size:11px;color:#aaa;margin-top:4px;">Coming in next step</p>
      </div>
    </div>
    `}
  `;
}
```

- [ ] **Step 4: Add depth slider CSS to style.css**

```css
.depth-slider {
  width: 100%; accent-color: #4f46e5; display: block; margin-bottom: 4px;
}
.depth-slider-labels {
  display: flex; justify-content: space-between; font-size: 10px; color: #aaa;
}
.depth-active-label { color: #4f46e5; font-weight: 700; }
```

- [ ] **Step 5: Run app and verify**

Run `python main.py`. Expand the Settings strip. Move the depth slider — the label (Breadth/Slightly Broad/Balanced/Slightly Deep/Deep) should update instantly. Expand Pacing Instructions — all 8 pacing rule texts should change to match the preset. The "Reset to preset" link on any rule should restore it to the current slider position's text.

- [ ] **Step 6: Commit**

```bash
git add static/app.js static/style.css
git commit -m "feat: depth slider applies pacing presets live"
```

---

## Task 6: Duration control — estimateDuration() + two-track display

**Files:**
- Modify: `static/app.js` (add `estimateDuration`, `setDurationTarget`, `updateDurationDisplay`; update `renderSettingsStrip`, `applyUpdate`)
- Modify: `static/style.css` (duration track and input styles)

- [ ] **Step 1: Add estimateDuration() function to app.js**

Add after `applyDepthPreset`:

```js
function estimateDuration() {
  const topics = state.sections.topics;
  if (topics.length === 0) return 2;

  let raw = 5 * topics.length;
  for (const t of topics) {
    raw += Math.max(0, t.core.length - 1) * 1.0;
    raw += t.probe.length * 0.5;
  }

  // finish line always adds buffer
  raw += 5;

  // expansion topics
  raw += state.sections.expansion.length * 0.75;

  // focus warmup
  if (state.sections.focus) raw += 2;

  // depth factor: 0.80 at Breadth (0), 1.20 at Deep (100), 1.0 at Balanced (50)
  const depthFactor = 0.80 + (state.depthSliderValue / 100) * 0.40;
  raw *= depthFactor;

  return Math.round(Math.min(90, Math.max(2, raw)));
}
```

- [ ] **Step 2: Add setDurationTarget() and updateDurationDisplay() to app.js**

Add after `estimateDuration`:

```js
function setDurationTarget(value) {
  state.durationTarget = Math.min(90, Math.max(0, value || 0));
  const slider = document.querySelector(".duration-slider");
  const number = document.querySelector(".duration-number");
  if (slider) slider.value = state.durationTarget;
  if (number) number.value = state.durationTarget || "";
  updateDurationDisplay();
}

function updateDurationDisplay() {
  const estimate = estimateDuration();
  const targetPct = state.durationTarget > 0 ? (state.durationTarget / 90) * 100 : 0;
  const estimatePct = (estimate / 90) * 100;

  const targetFill = document.querySelector(".target-fill");
  const estimateFill = document.querySelector(".estimate-fill");
  const targetLabelEl = document.querySelector(".duration-label-target");
  const estimateLabelEl = document.querySelector(".duration-label-estimate");

  if (targetFill) targetFill.style.width = targetPct.toFixed(1) + "%";
  if (estimateFill) estimateFill.style.width = estimatePct.toFixed(1) + "%";
  if (targetLabelEl) targetLabelEl.textContent = state.durationTarget > 0
    ? `● Target: ${state.durationTarget} min`
    : "● No target set";
  if (estimateLabelEl) estimateLabelEl.textContent = `● Est: ${estimate} min`;
}
```

- [ ] **Step 3: Add call to updateDurationDisplay() in applyUpdate()**

In `applyUpdate()`, add one line at the very end (after `renderTemplate()`):

```js
function applyUpdate(update) {
  // ... existing code unchanged ...
  renderTemplate();
  updateDurationDisplay();
}
```

- [ ] **Step 4: Replace the duration-control placeholder in renderSettingsStrip() with full HTML**

Replace the entire `renderSettingsStrip()` function:

```js
function renderSettingsStrip() {
  const strip = document.getElementById("settings-strip");
  if (!strip) return;
  const collapsed = state.collapsedSections.has("settings");

  const depthLabels = { 0: "Breadth", 25: "Slightly Broad", 50: "Balanced", 75: "Slightly Deep", 100: "Deep" };
  const depthLabel = depthLabels[state.depthSliderValue] || "Balanced";

  const estimate = estimateDuration();
  const targetPct = state.durationTarget > 0 ? (state.durationTarget / 90) * 100 : 0;
  const estimatePct = (estimate / 90) * 100;
  const targetLabelText = state.durationTarget > 0 ? `● Target: ${state.durationTarget} min` : "● No target set";

  strip.innerHTML = `
    <div class="settings-strip-header" onclick="toggleSection('settings')">
      <span class="section-chevron">${collapsed ? "▸" : "▾"}</span>
      <span>Settings</span>
    </div>
    ${collapsed ? "" : `
    <div class="settings-strip-body">
      <div class="settings-control">
        <div class="settings-control-label">Depth vs. Breadth</div>
        <input type="range" class="depth-slider" min="0" max="100" step="25"
          value="${state.depthSliderValue}"
          oninput="applyDepthPreset(parseInt(this.value))">
        <div class="depth-slider-labels">
          <span>Breadth</span>
          <span class="depth-active-label">${escHtml(depthLabel)}</span>
          <span>Deep</span>
        </div>
      </div>
      <div class="settings-control" id="duration-control">
        <div class="settings-control-label">Interview Duration</div>
        <div class="duration-labels">
          <span class="duration-label-target">${escHtml(targetLabelText)}</span>
          <span class="duration-label-estimate">● Est: ${estimate} min</span>
        </div>
        <div class="duration-tracks">
          <div class="duration-track">
            <div class="target-fill" style="width:${targetPct.toFixed(1)}%"></div>
          </div>
          <div class="duration-track">
            <div class="estimate-fill" style="width:${estimatePct.toFixed(1)}%"></div>
          </div>
        </div>
        <div class="duration-inputs">
          <input type="range" class="duration-slider" min="0" max="90" step="5"
            value="${state.durationTarget}"
            oninput="setDurationTarget(parseInt(this.value))">
          <input type="number" class="duration-number" min="0" max="90"
            value="${state.durationTarget || ""}"
            placeholder="—"
            oninput="setDurationTarget(parseInt(this.value) || 0)">
          <span class="duration-unit">min</span>
        </div>
      </div>
    </div>
    `}
  `;
}
```

- [ ] **Step 5: Add duration CSS to style.css**

```css
.duration-labels {
  display: flex; justify-content: space-between;
  font-size: 10px; font-weight: 600; margin-bottom: 5px;
}
.duration-label-target { color: #4f46e5; }
.duration-label-estimate { color: #f59e0b; }

.duration-tracks { display: flex; flex-direction: column; gap: 4px; margin-bottom: 7px; }
.duration-track {
  height: 7px; background: #e5e7eb; border-radius: 4px; position: relative; overflow: hidden;
}
.target-fill {
  position: absolute; left: 0; top: 0; height: 100%;
  background: #4f46e5; border-radius: 4px; transition: width 0.1s;
}
.estimate-fill {
  position: absolute; left: 0; top: 0; height: 100%;
  background: rgba(245, 158, 11, 0.2);
  border-right: 2px solid #f59e0b;
  border-radius: 4px; transition: width 0.2s;
}

.duration-inputs { display: flex; align-items: center; gap: 6px; }
.duration-slider { flex: 1; accent-color: #4f46e5; }
.duration-number {
  width: 48px; border: 1px solid #ddd; border-radius: 4px;
  padding: 3px 4px; font-size: 12px; font-family: inherit;
  text-align: center; outline: none;
}
.duration-number:focus { border-color: #4f46e5; }
.duration-unit { font-size: 11px; color: #888; white-space: nowrap; }
```

- [ ] **Step 6: Run app and verify**

Run `python main.py`. Expand Settings. The duration control should show two horizontal tracks — blue (target, initially flat at 0%) and orange dashed (estimate). Type "60" in the number field — blue track fills to 67%, slider moves to 60. Type a topic title in the template and add a Core item via the AI — the orange estimate track should update after the AI responds. Move the Depth slider to Deep — orange track should increase.

- [ ] **Step 7: Commit**

```bash
git add static/app.js static/style.css
git commit -m "feat: duration control with two-track display and live formula estimate"
```

---

## Task 7: Quick action buttons

**Files:**
- Modify: `templates/index.html` (add button row above textarea)
- Modify: `static/app.js` (add `sendQuickAction`; update `streamFromServer` to disable/enable buttons)
- Modify: `static/style.css` (pill button styles)

- [ ] **Step 1: Add quick-action row to index.html**

In `templates/index.html`, add the quick-actions div inside `.chat-input`, just before the `<textarea>`:

```html
    <div class="chat-input">
      <div class="quick-actions-row">
        <button class="quick-action-btn" onclick="sendQuickAction('Can you suggest another topic we haven\'t covered yet?')">+ Suggest a topic</button>
        <button class="quick-action-btn" onclick="sendQuickAction('Can you review the pacing instructions and tighten them up — make them more concise and actionable?')">⚡ Tighten pacing</button>
        <button class="quick-action-btn" onclick="sendQuickAction('Can you suggest some additional expansion topics based on what we\'ve built so far?')">↗ Add expansion ideas</button>
      </div>
      <div style="display:flex;gap:8px;">
        <textarea id="input" placeholder="Type your response…" rows="2"></textarea>
        <button id="send-btn" onclick="sendMessage()">Send</button>
      </div>
    </div>
```

- [ ] **Step 2: Add sendQuickAction() to app.js**

Add after `sendMessage()`:

```js
function sendQuickAction(message) {
  if (state.streaming) return;
  appendMessage("user", message);
  streamFromServer(message);
}
```

- [ ] **Step 3: Update streamFromServer() to disable/enable quick-action buttons**

In `streamFromServer`, add one line after `document.getElementById("send-btn").disabled = true;`:

```js
  state.streaming = true;
  document.getElementById("send-btn").disabled = true;
  document.querySelectorAll(".quick-action-btn").forEach(b => b.disabled = true);
```

And in the `finally` block, add after `document.getElementById("send-btn").disabled = false;`:

```js
  } finally {
    state.streaming = false;
    document.getElementById("send-btn").disabled = false;
    document.querySelectorAll(".quick-action-btn").forEach(b => b.disabled = false);
  }
```

- [ ] **Step 4: Add quick-action CSS to style.css**

First, update the existing `.chat-input` and `.chat-input button` rules. The current `.chat-input button` selector (specificity 0,1,1) would override `.quick-action-btn` (0,1,0) — so narrow `#send-btn` to avoid that:

Find this existing rule in style.css:
```css
.chat-input button, .export-btn {
  background: #4f46e5; color: #fff; border: none;
  border-radius: 6px; padding: 8px 16px; font-size: 13px;
  cursor: pointer; font-family: inherit;
}
```
Change `.chat-input button` to `#send-btn`:
```css
#send-btn, .export-btn {
  background: #4f46e5; color: #fff; border: none;
  border-radius: 6px; padding: 8px 16px; font-size: 13px;
  cursor: pointer; font-family: inherit;
}
```

Also find and update the hover, focus, and disabled rules that reference `.chat-input button`:
```css
/* change .chat-input button:hover to #send-btn:hover */
#send-btn:hover, .export-btn:hover { background: #3f35c5; }
#send-btn:focus, .export-btn:focus { outline: 2px solid #4f46e5; outline-offset: 2px; }
#send-btn:disabled { background: #aaa; cursor: not-allowed; }
```

Then update `.chat-input` layout and add the new classes:

```css
.chat-input {
  display: flex; flex-direction: column;
  border-top: 1px solid #e0e0e0; flex-shrink: 0; padding: 0;
}
.chat-input > div:last-child { display: flex; gap: 8px; padding: 8px 14px 12px; }

.quick-actions-row {
  display: flex; gap: 6px; flex-wrap: wrap;
  padding: 8px 14px 4px;
}
.quick-action-btn {
  font-size: 11px; font-family: inherit;
  background: white; color: #4f46e5;
  border: 1px solid #c7d2fe; border-radius: 12px;
  padding: 4px 10px; cursor: pointer;
}
.quick-action-btn:hover { background: #eef2ff; border-color: #4f46e5; }
.quick-action-btn:disabled { color: #aaa; border-color: #ddd; cursor: not-allowed; background: white; }
```

- [ ] **Step 5: Run app and verify**

Run `python main.py`. Three pill buttons ("+ Suggest a topic", "⚡ Tighten pacing", "↗ Add expansion ideas") should appear above the textarea. Click one — the message appears in the chat as a user bubble and the AI responds. All three buttons are greyed out while the AI is streaming, and re-enable when done.

- [ ] **Step 6: Commit**

```bash
git add templates/index.html static/app.js static/style.css
git commit -m "feat: quick action buttons for suggest topic, tighten pacing, add expansion"
```

---

## Task 8: Full verification and backend test check

**Files:** None — verification only.

- [ ] **Step 1: Run backend tests to confirm nothing broke**

```bash
pytest tests/ -v
```

Expected: all tests pass (routes and tools unaffected by frontend changes).

- [ ] **Step 2: Manual end-to-end walkthrough**

Run `python main.py`. Go through this checklist:

1. **Collapsible sections:** Click each section header (Metadata, Pacing Instructions, Interview Focus, Topics, Expansion Topics) — all collapse/expand. Click an individual pacing rule — collapses its textarea only. Add a topic via the AI and collapse that topic.

2. **Settings strip:** Click "▸ Settings" to expand. Depth slider at far left (Breadth) — expand Pacing and verify rule text changed. Move to Deep — rule text changes again. Move back to Balanced — text matches original defaults. Click "Reset to preset" on a pacing rule you manually edited — it restores preset text.

3. **Duration control:** Type "60" in the number field — blue bar fills to ~67%, slider moves to 60. Type "45" — blue bar shrinks, slider moves. Drag the slider to 30 — number field updates. Have the AI add topics and Core/Probe items — orange estimate bar updates after each AI response.

4. **Quick actions:** Click "⚡ Tighten pacing" — message appears in chat as user bubble, AI responds. During streaming, all three buttons are greyed out. After streaming, they re-enable.

5. **Export:** Click Export Template — modal opens with formatted output. Download works. Verify collapsed sections don't affect export (all pacing rules still exported regardless of UI collapse state).

- [ ] **Step 3: Fix any issues found, then commit**

```bash
git add -p
git commit -m "fix: <describe any issues found>"
```
