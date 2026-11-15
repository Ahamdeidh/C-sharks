import '@testing-library/jest-dom';

// Polyfill ResizeObserver & non-zero container geometry for Recharts ResponsiveContainer in jsdom
global.ResizeObserver = class ResizeObserver {
  constructor(callback) {
    this.callback = callback;
  }
  observe(target) {
    if (typeof this.callback === 'function') {
      this.callback(
        [
          {
            target,
            contentRect: { width: 800, height: 320, top: 0, left: 0, bottom: 320, right: 800 },
          },
        ],
        this
      );
    }
  }
  unobserve() {}
  disconnect() {}
};

if (typeof HTMLElement !== 'undefined') {
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', { configurable: true, get: () => 800 });
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, get: () => 320 });
  Object.defineProperty(HTMLElement.prototype, 'clientWidth', { configurable: true, get: () => 800 });
  Object.defineProperty(HTMLElement.prototype, 'clientHeight', { configurable: true, get: () => 320 });
  HTMLElement.prototype.getBoundingClientRect = function getBoundingClientRect() {
    return {
      width: 800,
      height: 320,
      top: 0,
      left: 0,
      right: 800,
      bottom: 320,
      x: 0,
      y: 0,
      toJSON: () => {},
    };
  };
}
