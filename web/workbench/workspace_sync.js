(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.WorkspaceSync = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function createDebouncedAction(action, delayMs) {
    const delay = Number.isFinite(Number(delayMs)) ? Math.max(0, Number(delayMs)) : 700;
    let timer = null;
    let lastArgs = null;

    return {
      schedule: function () {
        lastArgs = Array.prototype.slice.call(arguments);
        if (timer) {
          clearTimeout(timer);
        }
        timer = setTimeout(function () {
          timer = null;
          const args = lastArgs || [];
          lastArgs = null;
          action.apply(null, args);
        }, delay);
      },
      cancel: function () {
        if (timer) {
          clearTimeout(timer);
          timer = null;
        }
      },
      flush: function () {
        if (!timer) {
          return;
        }
        clearTimeout(timer);
        timer = null;
        const args = lastArgs || [];
        lastArgs = null;
        action.apply(null, args);
      },
    };
  }

  return {
    createDebouncedAction: createDebouncedAction,
  };
});
