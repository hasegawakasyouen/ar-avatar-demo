import assert from 'node:assert/strict';
import test from 'node:test';

import { MascotState, MascotStateMachine } from '../src/state-machine.js';

test('starts in loading and advances its generation on transition', () => {
  const machine = new MascotStateMachine();
  assert.equal(machine.state, MascotState.LOADING);
  assert.equal(machine.transition(MascotState.IDLE), 1);
  assert.equal(machine.state, MascotState.IDLE);
});

test('invalidates callbacks from an older generation', () => {
  const machine = new MascotStateMachine();
  const idleGeneration = machine.transition(MascotState.IDLE);
  machine.transition(MascotState.SUSPENDED);
  assert.equal(machine.isCurrent(idleGeneration), false);
});
