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
});

test('under target: suggests positive moves, none with zero delta', () => {
  const sections = {
    topics: [
      { title: 'T1', priority: 3, core: [{ priority: 3 }], probe: [] },
      { title: 'T2', priority: 3, core: [{ priority: 3 }], probe: [] },
      { title: 'T3', priority: 3, core: [{ priority: 3 }], probe: [] },
      { title: 'T4', priority: 3, core: [{ priority: 3 }], probe: [] },
      { title: 'T5', priority: 3, core: [{ priority: 3 }], probe: [] },
    ],
    expansion: ['E1', 'E2'], focus: 'x',
  };
  // est at depth 25 = 4 min; target 20 -> well under.
  const s = D.generateSuggestions(sections, 20, 25);
  assert.ok(s.length > 0);
  assert.ok(s.every((c) => c.deltaMin > 0));
  assert.strictEqual(s[0].type, 'raise_depth');
  assert.strictEqual(s[0].toValue, 50);
  assert.strictEqual(s[0].deltaMin, 1);
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
