// SPDX-License-Identifier: MPL-2.0
// Optional, page-local workaround for YTM's bound volume updates during a drag.
// Run in the music.youtube.com page context. Reload or call the restore function
// to remove it. This is not injected by the receiver and makes no requests.
(() => {
  if (location.hostname !== "music.youtube.com") {
    throw new Error("This workaround is only for YouTube Music Web.");
  }
  window.audioLabRestoreVolumeDragGuard?.();
  const patched = new Map();

  function install() {
    for (const slider of document.querySelectorAll(
      'ytmusic-player-bar tp-yt-paper-slider[id*="volume"]'
    )) {
      if (patched.has(slider) || typeof slider._updateKnob !== "function") continue;
      const descriptor = Object.getOwnPropertyDescriptor(slider, "_updateKnob");
      const original = slider._updateKnob;
      const guarded = function (...args) {
        // Pointer tracking continues to update immediateValue and send volume.
        // Bound feedback must not reset the knob/drag anchor in the meantime.
        if (!this.dragging) return original.apply(this, args);
      };
      slider._updateKnob = guarded;
      patched.set(slider, {descriptor, guarded});
    }
  }

  const observer = new MutationObserver(install);
  observer.observe(document.documentElement, {childList: true, subtree: true});
  install();
  window.audioLabRestoreVolumeDragGuard = () => {
    observer.disconnect();
    for (const [slider, {descriptor, guarded}] of patched) {
      if (slider._updateKnob !== guarded) continue;
      if (descriptor) Object.defineProperty(slider, "_updateKnob", descriptor);
      else delete slider._updateKnob;
    }
    patched.clear();
    delete window.audioLabRestoreVolumeDragGuard;
  };
  return `Audio Lab volume drag guard: ${patched.size} slider(s). Reload to undo.`;
})();
