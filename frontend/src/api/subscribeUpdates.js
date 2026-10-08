import { API_BASE_URL } from "../endpoints";
import { refreshToken } from "./apiService";

// Share a stream and refresh requests between the editor and operation dialogs.
const subscriptions = new Map();
const RECONNECT_MS = 30000;

export function subscribeUpdates(path, { load, onUpdate, onError }) {
  let entry = subscriptions.get(path);
  if (!entry) {
    entry = {
      listeners: new Set(), source: null, disposed: false,
      retry: null, debounce: null, pending: null, dirty: false,
    };
    subscriptions.set(path, entry);

    const fetchUpdate = async () => {
      if (entry.disposed) return;
      try {
        const response = await load();
        if (entry.disposed) return;
        if (response.ok && response.data) {
          entry.listeners.forEach(listener => {
            if (listener.active) listener.onUpdate?.(response.data);
          });
        } else {
          entry.listeners.forEach(listener => { if (listener.active) listener.onError?.(response); });
        }
      } catch (error) {
        if (!entry.disposed) entry.listeners.forEach(listener => { if (listener.active) listener.onError?.(error); });
      } finally {
        entry.pending = null;
        if (entry.dirty && !entry.disposed) {
          entry.dirty = false;
          refresh();
        }
      }
    };
    const refresh = () => {
      if (entry.disposed) return;
      if (entry.pending) { entry.dirty = true; return; }
      entry.pending = Promise.resolve().then(fetchUpdate);
    };
    const connect = () => {
      if (entry.disposed || typeof EventSource === "undefined") return;
      try {
        const source = new EventSource(`${API_BASE_URL}${path}`, { withCredentials: true });
        entry.source = source;
        source.addEventListener("stream-open", () => {
          if (entry.disposed) return;
          refresh(); // Reconcile missed events on every connection, including reconnects.
        });
        source.addEventListener("update", () => {
          if (entry.disposed) return;
          clearTimeout(entry.debounce);
          entry.debounce = setTimeout(refresh, 250);
        });
        source.addEventListener("stream-reset", refresh);
        source.onerror = () => {
          source.close();
          entry.source = null;
          clearTimeout(entry.retry);
          if (!entry.disposed) entry.retry = setTimeout(async () => {
            await refreshToken(); // Renew access cookies without polling resource data.
            connect();
          }, RECONNECT_MS);
        };
        source.addEventListener("stream-error", source.onerror);
      } catch {
        if (!entry.disposed) entry.retry = setTimeout(connect, RECONNECT_MS);
      }
    };
    entry.refresh = refresh;
    entry.connect = connect;
  }
  // Ignore a request that started before this subscriber (e.g. before rendering).
  const listener = { onUpdate, onError, active: !entry.pending };
  entry.listeners.add(listener);
  const activate = () => {
    if (!entry.listeners.has(listener)) return;
    listener.active = true;
    entry.refresh();
  };
  if (entry.pending) entry.pending.then(activate);
  else activate();
  if (!entry.source && !entry.retry) entry.connect();

  let cancelled = false;
  return () => {
    if (cancelled) return;
    cancelled = true;
    entry.listeners.delete(listener);
    if (entry.listeners.size) return;
    entry.disposed = true;
    entry.source?.close();
    clearTimeout(entry.retry);
    clearTimeout(entry.debounce);
    subscriptions.delete(path);
  };
}
