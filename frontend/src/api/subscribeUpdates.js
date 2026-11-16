// Short requests leave HTTP/1 connections available for navigation, editor chunks
// and media. A persistent stream per progress card/tab can exhaust that pool.
const subscriptions = new Map();
const waiting = new Set();
const MAX_REFRESHES = 2;
const REQUEST_TIMEOUT = 15000;
let running = 0;
let visibilityDocument = null;
const pageVisible = () => typeof document === "undefined" || document.visibilityState !== "hidden";

function intervalFor(path, data) {
  if (path.startsWith("notifications/")) return 30000;
  const busy = ["GENERATION", "RENDERING", "QUEUED", "TRANSCRIBING", "ANALYZING", "PROCESSING"];
  return busy.includes(data?.status) || data?.clips?.some(clip => busy.includes(clip.status)) ? 3000 : 15000;
}

function enqueue(entry) {
  if (entry.disposed || entry.authFailed || !pageVisible()) return;
  clearTimeout(entry.timer);
  if (entry.pending) { entry.dirty = true; return; }
  entry.pending = true;
  entry.revision += 1;
  waiting.add(entry);
  drain();
}

function drain() {
  for (const entry of waiting) {
    if (running >= MAX_REFRESHES) break;
    waiting.delete(entry);
    if (entry.disposed || !pageVisible()) { entry.pending = false; continue; }
    running += 1;
    refresh(entry).finally(() => { running -= 1; drain(); });
  }
}

async function refresh(entry) {
  const revision = entry.revision;
  const controller = new AbortController();
  entry.controller = controller;
  let timedOut = false;
  const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, REQUEST_TIMEOUT);
  // The race also releases the scheduler if a caller ignores cancellation.
  const cancelled = new Promise(resolve => controller.signal.addEventListener("abort", () => resolve(null), { once: true }));
  try {
    const response = await Promise.race([
      Promise.resolve().then(() => !controller.signal.aborted && pageVisible() ? entry.load({ signal: controller.signal, timeout: REQUEST_TIMEOUT }) : null), cancelled,
    ]);
    if (entry.disposed || !pageVisible() || (controller.signal.aborted && !timedOut)) return;
    if (response?.ok && response.data) {
      entry.data = response.data;
      const key = JSON.stringify(response.data);
      for (const listener of entry.listeners) {
        if (revision >= listener.afterRevision && (listener.key !== key || listener.failed)) {
          listener.key = key; listener.failed = false;
          listener.onUpdate?.(response.data);
        }
      }
    } else {
      const failure = response || { ok: false, message: "The update timed out. Retrying shortly." };
      if ([401, 403].includes(failure.status)) entry.authFailed = true;
      for (const listener of entry.listeners) {
        if (revision >= listener.afterRevision) { listener.failed = true; listener.onError?.(failure); }
      }
    }
  } catch (error) {
    if (!entry.disposed && pageVisible() && !controller.signal.aborted) {
      for (const listener of entry.listeners) {
        if (revision >= listener.afterRevision) { listener.failed = true; listener.onError?.(error); }
      }
    }
  } finally {
    clearTimeout(timeout);
    entry.controller = null;
    entry.pending = false;
    if (!entry.disposed && !entry.authFailed && pageVisible()) {
      if (entry.dirty) { entry.dirty = false; enqueue(entry); }
      else entry.timer = setTimeout(() => enqueue(entry), intervalFor(entry.path, entry.data));
    }
  }
}

function visibilityChanged() {
  for (const entry of subscriptions.values()) {
    if (!pageVisible()) entry.pause();
    else enqueue(entry);
  }
}

export function subscribeUpdates(path, { load, onUpdate, onError }) {
  let entry = subscriptions.get(path);
  if (!entry) {
    entry = { path, load, listeners: new Set(), revision: 0, pending: false, dirty: false, disposed: false, authFailed: false };
    const pause = () => {
      clearTimeout(entry.timer);
      entry.dirty = false;
      if (waiting.delete(entry)) entry.pending = false;
      entry.controller?.abort();
    };
    entry.pause = pause;
    if (!visibilityDocument && typeof document !== "undefined") {
      visibilityDocument = document;
      visibilityDocument.addEventListener("visibilitychange", visibilityChanged);
    }
    subscriptions.set(path, entry);
  }
  const listener = { onUpdate, onError, afterRevision: entry.revision + (entry.pending ? 1 : 0) };
  entry.listeners.add(listener);
  enqueue(entry);
  let stopped = false;
  return () => {
    if (stopped) return;
    stopped = true;
    entry.listeners.delete(listener);
    if (entry.listeners.size) return;
    entry.disposed = true;
    entry.pause();
    subscriptions.delete(path);
    if (!subscriptions.size && visibilityDocument) {
      visibilityDocument.removeEventListener("visibilitychange", visibilityChanged);
      visibilityDocument = null;
    }
  };
}
