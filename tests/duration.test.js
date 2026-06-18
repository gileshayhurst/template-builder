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
