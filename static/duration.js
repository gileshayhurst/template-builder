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

  function clone(sections) {
    return typeof structuredClone === 'function'
      ? structuredClone(sections)
      : JSON.parse(JSON.stringify(sections));
  }

  function maxIndex(topics) {
    return topics.reduce((m, t) => Math.max(m, t.index || 0), 0);
  }

  // Apply a sections-mutating suggestion, returning a fresh clone.
  // Depth moves (lower_depth/raise_depth) are handled by the caller; for delta
  // computation they are simulated via estimateRawFor(sections, toValue).
  function applySuggestion(sections, depthValue, s) {
    const next = clone(sections);
    const topics = next.topics || (next.topics = []);
    if (s.type === 'remove_topic') {
      topics.splice(s.topicPos, 1);
    } else if (s.type === 'remove_item') {
      topics[s.topicPos][s.itemType].splice(s.itemIndex, 1);
    } else if (s.type === 'add_probes') {
      const t = topics[s.topicPos];
      t.probe = t.probe || [];
      for (let i = 0; i < s.count; i++) t.probe.push({ text: '', priority: 3 });
    } else if (s.type === 'promote_expansion') {
      const title = (next.expansion || [])[s.expansionIndex];
      next.expansion.splice(s.expansionIndex, 1);
      topics.push({ index: maxIndex(topics) + 1, title, priority: 3, core: [{ text: '', priority: 3 }], probe: [] });
    } else if (s.type === 'add_topic') {
      topics.push({ index: maxIndex(topics) + 1, title: '', priority: 3, core: [{ text: '', priority: 3 }], probe: [] });
    }
    return { sections: next, depthValue };
  }

  function candidateDelta(sections, depthValue, baseRaw, c) {
    if (c.type === 'lower_depth' || c.type === 'raise_depth') {
      return Math.round(estimateRawFor(sections, c.toValue) - baseRaw);
    }
    const r = applySuggestion(sections, depthValue, c);
    return Math.round(estimateRawFor(r.sections, depthValue) - baseRaw);
  }

  function generateSuggestions(sections, target, depthValue) {
    if (!target || target <= 0) return [];
    const est = estimateDurationFor(sections, depthValue);
    const gap = est - target;
    if (Math.abs(gap) <= TOLERANCE) return [];

    const baseRaw = estimateRawFor(sections, depthValue);
    const topics = sections.topics || [];
    let cands = [];

    if (gap > 0) {
      // OVER target — trim, least valuable first.
      topics.forEach((t, ti) => {
        (t.probe || []).forEach((p, ii) => cands.push({
          type: 'remove_item', topicPos: ti, itemType: 'probe', itemIndex: ii,
          _cls: 0, _cut: p.priority ?? 3,
          label: 'Drop a probe in “' + (t.title || 'Untitled') + '”',
        }));
        for (let ii = 1; ii < (t.core || []).length; ii++) cands.push({
          type: 'remove_item', topicPos: ti, itemType: 'core', itemIndex: ii,
          _cls: 2, _cut: t.core[ii].priority ?? 3,
          label: 'Drop a core point in “' + (t.title || 'Untitled') + '”',
        });
      });
      if (topics.length > 1) {
        topics.forEach((t, ti) => cands.push({
          type: 'remove_topic', topicPos: ti,
          _cls: 3, _cut: t.priority ?? 3,
          label: 'Remove “' + (t.title || 'Untitled') + '”',
        }));
      }
      if (depthValue > 0) cands.push({
        type: 'lower_depth', toValue: depthValue - 25, _cls: 4, _cut: 3,
        label: 'Reduce depth one notch',
      });
    } else {
      // UNDER target — fill, quality-improving first.
      topics.forEach((t, ti) => {
        if ((t.probe || []).length === 0) cands.push({
          type: 'add_probes', topicPos: ti, count: 2, _cls: 0, _cut: 0,
          label: 'Add 2 probe slots to “' + (t.title || 'Untitled') + '”',
        });
      });
      (sections.expansion || []).forEach((x, xi) => cands.push({
        type: 'promote_expansion', expansionIndex: xi, _cls: 1, _cut: 0,
        label: 'Promote expansion topic “' + x + '”',
      }));
      if (depthValue < 100) cands.push({
        type: 'raise_depth', toValue: depthValue + 25, _cls: 2, _cut: 0,
        label: 'Increase depth one notch',
      });
      cands.push({ type: 'add_topic', _cls: 3, _cut: 0, label: 'Add a new topic' });
    }

    for (const c of cands) c.deltaMin = candidateDelta(sections, depthValue, baseRaw, c);
    cands = cands.filter((c) => c.deltaMin !== 0);
    cands = cands.filter((c) => Math.abs(gap + c.deltaMin) < Math.abs(gap));
    cands.sort((a, b) =>
      (a._cls - b._cls) ||
      (a._cut - b._cut) ||
      (Math.abs(gap + a.deltaMin) - Math.abs(gap + b.deltaMin)));

    for (const c of cands) {
      const dir = c.deltaMin < 0 ? 'saves ~' + (-c.deltaMin) + ' min' : 'adds ~' + c.deltaMin + ' min';
      const note = (c.type === 'lower_depth' || c.type === 'raise_depth') ? ' · also rewrites pacing text' : '';
      c.detail = dir + note;
    }
    return cands.slice(0, 3);
  }

  const api = { TOLERANCE, priorityFactor, depthFactorFor, estimateRawFor, estimateDurationFor, generateSuggestions, applySuggestion };
  if (typeof window !== 'undefined') window.DurationEngine = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
