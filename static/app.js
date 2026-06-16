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

function getDepthPreset(value) {
  const key = { 0: "breadth", 25: "slightly_broad", 50: "balanced", 75: "slightly_deep", 100: "deep" }[value];
  return PACING_DEPTH_PRESETS[key] || PACING_DEPTH_PRESETS.balanced;
}

function applyDepthPreset(value) {
  const valid = [0, 25, 50, 75, 100];
  value = valid.reduce((prev, curr) => Math.abs(curr - value) < Math.abs(prev - value) ? curr : prev);
  state.depthSliderValue = value;
  state.sections.pacing = { ...getDepthPreset(value) };
  renderTemplate();
}

function priorityFactor(p) {
  return 0.5 + ((p ?? 3) - 1) * 0.25;
}

function estimateDuration() {
  const topics = state.sections.topics;
  if (topics.length === 0) return 2;

  let raw = 0.8 * topics.length;
  for (const t of topics) {
    raw += Math.max(0, t.core.length - 1) * 0.2;
    raw += t.probe.length * 0.1;
  }

  raw += 0.5; // finish line buffer
  raw += state.sections.expansion.length * 0.2;
  if (state.sections.focus) raw += 0.5;

  // depth factor: asymmetric — 0.65 at Breadth, 1.0 at Balanced, 1.8 at Deep
  const v = state.depthSliderValue;
  const depthFactor = v < 50
    ? 1.0 - ((50 - v) / 50) * 0.35
    : 1.0 + ((v - 50) / 50) * 0.8;
  raw *= depthFactor;

  return Math.round(Math.min(90, Math.max(2, raw)));
}

function durationViewModel() {
  const estimate = estimateDuration();
  const targetPct = state.durationTarget > 0 ? (state.durationTarget / 90) * 100 : 0;
  const estimatePct = (estimate / 90) * 100;
  const targetLabelText = state.durationTarget > 0
    ? `● Target: ${state.durationTarget} min`
    : "● No target set";
  return { estimate, targetPct, estimatePct, targetLabelText };
}

function setDurationTarget(value) {
  state.durationTarget = Math.min(90, Math.max(0, value || 0));
  const slider = document.querySelector(".duration-slider");
  const number = document.querySelector(".duration-number");
  if (slider) slider.value = state.durationTarget;
  if (number) number.value = state.durationTarget || "";
  updateDurationDisplay();
}

function updateDurationDisplay() {
  const { estimate, targetPct, estimatePct, targetLabelText } = durationViewModel();

  const targetFill = document.querySelector(".target-fill");
  const estimateFill = document.querySelector(".estimate-fill");
  const targetLabelEl = document.querySelector(".duration-label-target");
  const estimateLabelEl = document.querySelector(".duration-label-estimate");

  if (targetFill) targetFill.style.width = targetPct.toFixed(1) + "%";
  if (estimateFill) estimateFill.style.width = estimatePct.toFixed(1) + "%";
  if (targetLabelEl) targetLabelEl.textContent = targetLabelText;
  if (estimateLabelEl) estimateLabelEl.textContent = `● Est: ${estimate} min`;
}

// ─── STATE ────────────────────────────────────────────────────────────────────

const state = {
  streaming: false,
  exportFilename: "",
  depthSliderValue: 50,
  durationTarget: 0,
  collapsedSections: new Set(["metadata", "pacing"]),
  sections: {
    metadata: { title: "", version: "1.0", date: new Date().toISOString().split("T")[0] },
    pacing: { ...PACING_DEFAULTS },
    focus: "",
    topics: [],
    expansion: []
  }
};

// ─── INIT ─────────────────────────────────────────────────────────────────────

window.addEventListener("DOMContentLoaded", () => {
  renderTemplate();

  document.getElementById("input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  startConversation();
});

async function startConversation() {
  await fetch("/reset", { method: "POST" });
  await streamFromServer("Hello, I am ready to create a template.");
}

// ─── CHAT ─────────────────────────────────────────────────────────────────────

function appendMessage(role, content) {
  const el = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = `message ${role}`;
  const roleLabel = role === "ai" ? "AI" : "You";
  div.innerHTML = `<div class="role">${roleLabel}</div><div class="body"></div>`;
  div.querySelector(".body").textContent = content;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
  return div.querySelector(".body");
}

function appendStatusMsg(text) {
  const el = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = "status-msg";
  div.textContent = text;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
  return div;
}

async function sendMessage() {
  if (state.streaming) return;
  const input = document.getElementById("input");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  appendMessage("user", text);
  await streamFromServer(text);
}

async function sendQuickAction(message) {
  if (state.streaming) return;
  appendMessage("user", message);
  await streamFromServer(message);
}

async function streamFromServer(message) {
  state.streaming = true;
  document.getElementById("send-btn").disabled = true;
  document.querySelectorAll(".quick-action-btn").forEach(b => b.disabled = true);

  let aiBodyEl = null;
  let aiText = "";
  let statusEl = null;

  try {
    const resp = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });

    if (!resp.ok) throw new Error(`Server error ${resp.status}`);
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();

      let currentEvent = null;
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          const raw = line.slice(6).trim();
          if (currentEvent === "chat_token") {
            const token = JSON.parse(raw);
            if (!aiBodyEl) aiBodyEl = appendMessage("ai", "");
            aiText += token;
            aiBodyEl.textContent = aiText;
            document.getElementById("messages").scrollTop = document.getElementById("messages").scrollHeight;
          } else if (currentEvent === "section_update") {
            if (!statusEl) statusEl = appendStatusMsg("✦ Updating template…");
            applyUpdate(JSON.parse(raw));
          } else if (currentEvent === "done") {
            if (statusEl) { statusEl.remove(); statusEl = null; }
          } else if (currentEvent === "error") {
            throw new Error(JSON.parse(raw));
          }
          currentEvent = null;
        }
      }
    }
  } catch (err) {
    appendMessage("ai", `⚠ Could not reach AI: ${err.message}`);
  } finally {
    state.streaming = false;
    document.getElementById("send-btn").disabled = false;
    document.querySelectorAll(".quick-action-btn").forEach(b => b.disabled = false);
  }
}

// ─── SECTION UPDATES ──────────────────────────────────────────────────────────

function normaliseItem(item) {
  if (typeof item === "string") return { text: item, priority: 3 };
  return { text: item.text, priority: item.priority ?? 3 };
}

function applyUpdate(update) {
  const { section, payload } = update;

  if (section === "metadata") {
    Object.assign(state.sections.metadata, payload);
    flashSection("section-metadata");
  } else if (section === "pacing") {
    state.sections.pacing[payload.rule] = payload.text;
    flashSection("section-pacing");
  } else if (section === "focus") {
    state.sections.focus = payload;
    flashSection("section-focus");
  } else if (section === "topic") {
    const topic = { ...payload, index: parseInt(payload.index, 10) };
    const idx = state.sections.topics.findIndex(t => t.index === topic.index);
    if (idx >= 0) state.sections.topics[idx] = topic;
    else {
      state.sections.topics.push(topic);
      state.sections.topics.sort((a, b) => a.index - b.index);
    }
    flashSection("section-topics");
  } else if (section === "remove_topic") {
    const removeIdx = parseInt(payload.index, 10);
    state.sections.topics = state.sections.topics.filter(t => t.index !== removeIdx);
    flashSection("section-topics");
  } else if (section === "expansion") {
    state.sections.expansion = payload;
    flashSection("section-expansion");
  }

  renderTemplate();
  updateDurationDisplay();
}

function flashSection(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.add("flash");
  setTimeout(() => el.classList.remove("flash"), 1200);
}

// ─── TEMPLATE RENDERING ───────────────────────────────────────────────────────

function renderSettingsStrip() {
  const strip = document.getElementById("settings-strip");
  if (!strip) return;
  const collapsed = state.collapsedSections.has("settings");

  const depthLabels = { 0: "Breadth", 25: "Slightly Broad", 50: "Balanced", 75: "Slightly Deep", 100: "Deep" };
  const depthLabel = depthLabels[state.depthSliderValue] || "Balanced";

  const { estimate, targetPct, estimatePct, targetLabelText } = durationViewModel();

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
          oninput="applyDepthPreset(parseInt(this.value, 10))">
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
            oninput="setDurationTarget(parseInt(this.value, 10))">
          <input type="number" class="duration-number" min="0" max="90" step="5"
            value="${state.durationTarget || ""}"
            placeholder="—"
            oninput="setDurationTarget(parseInt(this.value, 10) || 0)">
          <span class="duration-unit">min</span>
        </div>
      </div>
    </div>
    `}
  `;
}

function renderStarWidget(currentPriority, onClickFn) {
  const widget = document.createElement("div");
  widget.className = "star-widget";
  widget.onclick = e => e.stopPropagation();

  function paint(hoverVal) {
    const fill = hoverVal ?? currentPriority;
    Array.from(widget.children).forEach((s, i) => {
      s.className = "star" + (i < fill ? " filled" : "");
    });
  }

  for (let i = 1; i <= 5; i++) {
    const s = document.createElement("span");
    s.className = "star" + (i <= currentPriority ? " filled" : "");
    s.textContent = "★";
    s.onmouseenter = () => paint(i);
    s.onmouseleave = () => paint(null);
    s.onclick = () => { currentPriority = i; paint(null); onClickFn(i); };
    widget.appendChild(s);
  }

  widget.onmouseleave = () => paint(null);
  return widget;
}

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

function escHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function renderMetadata() {
  const s = state.sections.metadata;
  const body = document.createElement("div");
  body.className = "metadata-fields";
  body.innerHTML = `
    <label>Title
      <input value="${escHtml(s.title)}" placeholder="Research topic title"
        oninput="state.sections.metadata.title = this.value">
    </label>
    <label>Version
      <input value="${escHtml(s.version)}"
        oninput="state.sections.metadata.version = this.value">
    </label>
    <label>Date
      <input value="${escHtml(s.date)}"
        oninput="state.sections.metadata.date = this.value">
    </label>`;
  return sectionBlock("section-metadata", "Metadata", body, "metadata");
}

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

function renderFocus() {
  const body = document.createElement("div");
  body.innerHTML = `<textarea class="focus-textarea" placeholder="Interview focus anchor statement…"
    oninput="state.sections.focus = this.value">${escHtml(state.sections.focus)}</textarea>`;
  return sectionBlock("section-focus", "Interview Focus", body, "focus");
}

function renderTopics() {
  const body = document.createElement("div");
  for (const topic of state.sections.topics) body.appendChild(renderTopicBlock(topic));
  const addBtn = document.createElement("button");
  addBtn.className = "add-topic-btn";
  addBtn.textContent = "+ Add Topic";
  addBtn.onclick = addTopicManually;
  body.appendChild(addBtn);
  return sectionBlock("section-topics", `Topics (${state.sections.topics.length})`, body, "topics");
}

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

function renderItemRow(type, topicIndex, itemIndex, text) {
  const row = document.createElement("div");
  row.className = "item-row";
  row.innerHTML = `
    <span class="item-badge ${type}">${type === "core" ? "Core" : "Probe"}</span>
    <textarea oninput="updateItem(${topicIndex}, '${type}', ${itemIndex}, this.value)">${escHtml(text)}</textarea>`;
  return row;
}

function renderExpansion() {
  const joined = state.sections.expansion.join("\n");
  const body = document.createElement("div");
  body.innerHTML = `
    <div style="font-size:11px;color:#888;margin-bottom:6px;">One item per line</div>
    <textarea class="expansion-textarea" rows="5"
      placeholder="role of family and culture&#10;role of media or inspiration sources&#10;…"
      oninput="state.sections.expansion = this.value.split('\\n').map(s=>s.trim()).filter(Boolean)">${escHtml(joined)}</textarea>`;
  return sectionBlock("section-expansion", "Expansion Topics", body, "expansion");
}

// ─── EDITING HELPERS ──────────────────────────────────────────────────────────

function resetPacing(rule) {
  state.sections.pacing[rule] = getDepthPreset(state.depthSliderValue)[rule];
  renderTemplate();
}

function addTopicManually() {
  const nextIndex = state.sections.topics.length
    ? Math.max(...state.sections.topics.map(t => t.index)) + 1
    : 1;
  state.sections.topics.push({ index: nextIndex, title: "", core: [""], probe: [] });
  renderTemplate();
}

function removeTopicManually(index) {
  state.sections.topics = state.sections.topics.filter(t => t.index !== index);
  renderTemplate();
}

function updateTopicField(index, field, value) {
  const topic = state.sections.topics.find(t => t.index === index);
  if (topic) topic[field] = value;
}

function updateItem(topicIndex, type, itemIndex, value) {
  const topic = state.sections.topics.find(t => t.index === topicIndex);
  if (topic) topic[type][itemIndex] = value;
}

function updateItemText(topicIndex, type, itemIndex, value) {
  const topic = state.sections.topics.find(t => t.index === topicIndex);
  if (topic) topic[type][itemIndex].text = value;
}

function updateItemPriority(topicIndex, type, itemIndex, value) {
  const topic = state.sections.topics.find(t => t.index === topicIndex);
  if (topic) topic[type][itemIndex].priority = value;
}

function addItem(topicIndex, type) {
  const topic = state.sections.topics.find(t => t.index === topicIndex);
  if (topic) { topic[type].push(""); renderTemplate(); }
}

// ─── EXPORT ───────────────────────────────────────────────────────────────────

async function exportTemplate() {
  const outputEl = document.getElementById("template-output");
  const modal = document.getElementById("export-modal");
  const overlay = document.getElementById("modal-overlay");

  outputEl.textContent = "Generating template…";
  modal.classList.remove("hidden");
  overlay.classList.remove("hidden");

  try {
    const resp = await fetch("/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sections: state.sections })
    });
    const data = await resp.json();
    outputEl.textContent = data.template;
    state.exportFilename = data.filename;
  } catch (err) {
    outputEl.textContent = "Error generating template. Check the console.";
    console.error(err);
  }
}

function downloadTemplate() {
  const text = document.getElementById("template-output").textContent;
  if (!text || text === "Generating template…") return;
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = state.exportFilename || "template.txt";
  a.click();
  URL.revokeObjectURL(url);
}

function closeModal() {
  document.getElementById("export-modal").classList.add("hidden");
  document.getElementById("modal-overlay").classList.add("hidden");
}
