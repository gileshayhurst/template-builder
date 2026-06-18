// Pure, DOM-free duration math + suggestion engine.
// Loaded in the browser as window.DurationEngine (classic script, before app.js),
// and required directly in Node tests.
(function () {
  const TOLERANCE = 2; // minutes; within this band the template is "on target"

  function priorityFactor(p) {
    return 0.5 + ((p ?? 3) - 1) * 0.25;
  }

  function depthFactorFor(v) {
    return v < 50 ? 1.0 - ((50 - v) / 50) * 0.35 : 1.0 + ((v - 50) / 50) * 0.8;
  }

  // Clamped but UN-rounded estimate. Suggestion deltas use this so sub-minute
  // moves are compared honestly before rounding.
  function estimateRawFor(sections, depthValue) {
    const topics = (sections && sections.topics) || [];
    if (topics.length === 0) return 2;
    let raw = 0;
    for (const t of topics) {
      raw += 0.8 * priorityFactor(t.priority ?? 3);
      const core = t.core || [];
      for (let i = 1; i < core.length; i++) raw += 0.2 * priorityFactor(core[i].priority ?? 3);
      for (const p of (t.probe || [])) raw += 0.1 * priorityFactor(p.priority ?? 3);
    }
    raw += 0.5;
    raw += ((sections.expansion || []).length) * 0.2;
    if (sections.focus) raw += 0.5;
    raw *= depthFactorFor(depthValue);
    return Math.min(90, Math.max(2, raw));
  }

  // Rounded estimate — what the bar displays.
  function estimateDurationFor(sections, depthValue) {
    return Math.round(estimateRawFor(sections, depthValue));
  }

  const api = { TOLERANCE, priorityFactor, depthFactorFor, estimateRawFor, estimateDurationFor };
  if (typeof window !== 'undefined') window.DurationEngine = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
