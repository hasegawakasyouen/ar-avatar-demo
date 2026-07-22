export const MascotState = Object.freeze({
  LOADING: 'loading',
  IDLE: 'idle',
  SUSPENDED: 'suspended',
  ERROR: 'error',
});

export class MascotStateMachine {
  constructor() {
    this.state = MascotState.LOADING;
    this.generation = 0;
  }

  transition(next) {
    this.generation += 1;
    this.state = next;
    return this.generation;
  }

  isCurrent(generation) {
    return generation === this.generation;
  }
}
