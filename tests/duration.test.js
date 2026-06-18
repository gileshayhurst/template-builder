const { test } = require('node:test');
const assert = require('node:assert');
const D = require('../static/duration.js');

test('priorityFactor scales 0.5 .. 1.5', () => {
  assert.strictEqual(D.priorityFactor(1), 0.5);
  assert.strictEqual(D.priorityFactor(3), 1.0);
  assert.strictEqual(D.priorityFactor(5), 1.5);
  assert.strictEqual(D.priorityFactor(undefined), 1.0); // defaults to 3
});

test('estimateDurationFor matches known values across depths', () => {
  const sections = {
    topics: [
      { priority: 4, core: [{ priority: 4 }, { priority: 3 }], probe: [{ priority: 2 }] },
      { priority: 5, core: [{ priority: 5 }], probe: [] },
    ],
    expansion: ['a', 'b'],
    focus: 'x',
  };
  assert.strictEqual(D.estimateDurationFor(sections, 50), 4);  // factor 1.0
  assert.strictEqual(D.estimateDurationFor(sections, 100), 7); // factor 1.8
  assert.strictEqual(D.estimateDurationFor(sections, 0), 3);   // factor 0.65
});

test('estimateDurationFor returns floor of 2 for empty topics', () => {
  assert.strictEqual(D.estimateDurationFor({ topics: [], expansion: [], focus: '' }, 50), 2);
});

test('over target: removes the lowest-priority topic first', () => {
  const sections = {
    topics: [
      { title: 'Keep1', priority: 5, core: [{ priority: 5 }], probe: [] },
      { title: 'Keep2', priority: 5, core: [{ priority: 5 }], probe: [] },
      { title: 'Drop',  priority: 2, core: [{ priority: 2 }], probe: [] },
    ],
    expansion: [], focus: '',
  };
  // est at depth 100 = 6 min; target 2 -> 4 min over.
  const s = D.generateSuggestions(sections, 2, 100);
  assert.ok(s.length > 0);
  assert.strictEqual(s[0].type, 'remove_topic');
  assert.strictEqual(s[0].topicPos, 2);          // the P2 "Drop" topic
  assert.strictEqual(s[0].deltaMin, -1);
  assert.match(s[0].label, /Drop/);
  assert.match(s[0].detail, /saves/);
  const before = D.estimateDurationFor(sections, 100);
  for (const c of s) {
    const after = (c.type === 'raise_depth' || c.type === 'lower_depth')
      ? D.estimateDurationFor(sections, c.toValue)
      : D.estimateDurationFor(D.applySuggestion(sections, 100, c).sections, 100);
    assert.strictEqual(after - before, c.deltaMin, 'deltaMin must equal the bar change for ' + c.type);
  }
});

test('under target: every suggestion deltaMin equals the actual bar change', () => {
  const sections = {
    topics: [
      { title: 'T1', priority: 3, core: [{ priority: 3 }], probe: [] },
      { title: 'T2', priority: 3, core: [{ priority: 3 }], probe: [] },
      { title: 'T3', priority: 3, core: [{ priority: 3 }], probe: [] },
      { title: 'T4', priority: 3, core: [{ priority: 3 }], probe: [] },
      { title: 'T5', priority: 3, core: [{ priority: 3 }], probe: [] },
    ],
    expansion: [], focus: '',
  };
  // depth 0 puts the estimate (3 min) near a rounding boundary, where
  // add_topic's raw delta (~0.52) rounds up but the displayed bar does not move —
  // exactly the case where deltaMin must track the bar, not the raw difference.
  const depth = 0;
  const before = D.estimateDurationFor(sections, depth); // 3
  const s = D.generateSuggestions(sections, 20, depth);
  assert.ok(s.length > 0);
  for (const c of s) {
    assert.ok(c.deltaMin > 0, 'under-target moves must add time');
    const after = (c.type === 'raise_depth' || c.type === 'lower_depth')
      ? D.estimateDurationFor(sections, c.toValue)
      : D.estimateDurationFor(D.applySuggestion(sections, depth, c).sections, depth);
    assert.strictEqual(after - before, c.deltaMin, 'deltaMin must equal the bar change for ' + c.type);
  }
});

test('on target returns no suggestions', () => {
  const sections = { topics: [{ priority: 3, core: [{ priority: 3 }], probe: [] }], expansion: [], focus: '' };
  const est = D.estimateDurationFor(sections, 50);
  assert.deepStrictEqual(D.generateSuggestions(sections, est, 50), []);
});

test('no target returns no suggestions', () => {
  const sections = { topics: [{ priority: 3, core: [{ priority: 3 }], probe: [] }], expansion: [], focus: '' };
  assert.deepStrictEqual(D.generateSuggestions(sections, 0, 50), []);
});

test('never removes the last remaining topic', () => {
  const sections = { topics: [{ title: 'Solo', priority: 5, core: [{ priority: 5 }], probe: [] }], expansion: [], focus: '' };
  const s = D.generateSuggestions(sections, 2, 100);
  assert.ok(s.every((c) => c.type !== 'remove_topic'));
});

test('applySuggestion is pure (does not mutate input)', () => {
  const sections = { topics: [{ title: 'A', priority: 3, core: [{ priority: 3 }], probe: [] }, { title: 'B', priority: 3, core: [{ priority: 3 }], probe: [] }], expansion: [], focus: '' };
  const before = JSON.stringify(sections);
  D.applySuggestion(sections, 50, { type: 'remove_topic', topicPos: 0 });
  assert.strictEqual(JSON.stringify(sections), before);
});
