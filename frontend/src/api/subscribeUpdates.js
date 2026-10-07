import { API_BASE_URL } from "../endpoints";

// Share a stream and refresh requests between the editor and operation dialogs.
const subscriptions = new Map();
const RECONNECT_MS = 30000;
const RECONCILE_MS = 60000;

export function subscribeUpdates(path, { load, onUpdate, onError, intervalMs = 4000, replay = true }) {
  let entry = subscriptions.get(path);
  if (!entry) {
    entry = {
      listeners: new Set(), source: null, connected: false, disposed: false,
      timer: null, retry: null, debounce: null, busy: false, dirty: false,
      latest: null, requestId: 0,
    };
    subscriptions.set(path, entry);

    const schedule = () => {
      clearTimeout(entry.timer);
      if (!entry.disposed) entry.timer = setTimeout(refresh, entry.connected ? RECONCILE_MS : intervalMs);
    };
    const refresh = async () => {
      if (entry.disposed) return;
      if (entry.busy) { entry.dirty = true; return; }
      entry.busy = true;
      const requestId = ++entry.requestId;
      try {
        const response = await load();
        if (entry.disposed) return;
        if (response.ok && response.data) {
          entry.latest = response.data;
          entry.listeners.forEach(listener => {
            if (requestId >= listener.minimumRequestId) listener.onUpdate?.(response.data);
          });
        } else {
          entry.listeners.forEach(listener => listener.onError?.(response));
        }
      } catch (error) {
        if (!entry.disposed) entry.listeners.forEach(listener => listener.onError?.(error));
      } finally {
        entry.busy = false;
        if (entry.dirty && !entry.disposed) {
          entry.dirty = false;
          refresh();
        } else schedule();
      }
    };
    const connect = () => {
      if (entry.disposed || typeof EventSource === "undefined") return;
      try {
        const source = new EventSource(`${API_BASE_URL}${path}`, { withCredentials: true });
        entry.source = source;
        source.addEventListener("ready", () => {
          if (entry.disposed) return;
          entry.connected = true;
          refresh(); // Reconcile missed events on every connection, including reconnects.
        });
        source.addEventListener("update", () => {
          if (entry.disposed) return;
          clearTimeout(entry.debounce);
          entry.debounce = setTimeout(refresh, 250);
        });
        source.onerror = () => {
          source.close();
          entry.source = null;
          entry.connected = false;
          refresh(); // Axios can refresh an expired access cookie before the next stream.
          clearTimeout(entry.retry);
          if (!entry.disposed) entry.retry = setTimeout(connect, RECONNECT_MS);
        };
      } catch {
        if (!entry.disposed) entry.retry = setTimeout(connect, RECONNECT_MS);
      }
    };
    entry.refresh = refresh;
    entry.connect = connect;
  }
  const listener = { onUpdate, onError, minimumRequestId: replay ? 0 : entry.requestId + 1 };
  entry.listeners.add(listener);
  if (replay && entry.latest) Promise.resolve().then(() => {
    if (entry.listeners.has(listener)) onUpdate?.(entry.latest);
  });
  if (!entry.source && !entry.retry) entry.connect();
  entry.refresh();

  let cancelled = false;
  return () => {
    if (cancelled) return;
    cancelled = true;
    entry.listeners.delete(listener);
    if (entry.listeners.size) return;
    entry.disposed = true;
    entry.source?.close();
    clearTimeout(entry.timer);
    clearTimeout(entry.retry);
    clearTimeout(entry.debounce);
    subscriptions.delete(path);
  };
}
