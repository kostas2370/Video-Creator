import { API_BASE_URL } from "../endpoints";
import { refreshToken } from "./apiService";

// Share a stream and refresh requests between the editor and operation dialogs.
const subscriptions = new Map();
const RECONNECT_MS = 30000;
const pageVisible = () => typeof document === "undefined" || document.visibilityState !== "hidden";
let authRefresh = null;

function renewAuthentication() {
  if (!authRefresh) {
    authRefresh = Promise.resolve().then(refreshToken).finally(() => { authRefresh = null; });
  }
  return authRefresh;
}

export function subscribeUpdates(path, { load, onUpdate, onError }) {
  let entry = subscriptions.get(path);
  if (!entry) {
    entry = {
      listeners: new Set(), source: null, disposed: false,
      retry: null, debounce: null, pending: null, dirty: false, authFailed: false,
    };
    subscriptions.set(path, entry);

    const fetchUpdate = async () => {
      try {
        if (entry.disposed || !pageVisible()) return;
        const response = await load();
        if (entry.disposed || !pageVisible()) return;
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
      if (entry.disposed || !pageVisible()) return;
      if (entry.pending) { entry.dirty = true; return; }
      entry.pending = Promise.resolve().then(fetchUpdate);
    };
    // HTTP/1 connections are shared across tabs; hidden streams can block normal requests.
    const pause = () => {
      const source = entry.source;
      entry.source = null;
      source?.close();
      clearTimeout(entry.retry);
      clearTimeout(entry.debounce);
      entry.retry = null;
      entry.debounce = null;
      entry.dirty = false;
    };
    const scheduleReconnect = () => {
      if (entry.disposed || entry.authFailed || !pageVisible()) return;
      clearTimeout(entry.retry);
      entry.retry = setTimeout(async () => {
        entry.retry = null;
        if (entry.disposed || !pageVisible()) return;
        try {
          const response = await renewAuthentication();
          if (entry.disposed || !pageVisible()) return;
          if (!response.ok) {
            if ([400, 401, 403].includes(response.status)) {
              pause();
              entry.authFailed = true;
              entry.listeners.forEach(listener => { if (listener.active) listener.onError?.(response); });
            } else scheduleReconnect();
            return;
          }
          connect();
        } catch {
          scheduleReconnect();
        }
      }, RECONNECT_MS);
    };
    const connect = () => {
      if (entry.disposed || entry.authFailed || !pageVisible() || entry.source || typeof EventSource === "undefined") return;
      try {
        const source = new EventSource(`${API_BASE_URL}${path}`, { withCredentials: true });
        entry.source = source;
        const current = () => !entry.disposed && entry.source === source && pageVisible();
        source.addEventListener("stream-open", () => {
          if (current()) refresh(); // Reconcile updates missed while hidden or disconnected.
        });
        source.addEventListener("update", () => {
          if (!current()) return;
          clearTimeout(entry.debounce);
          entry.debounce = setTimeout(refresh, 250);
        });
        source.addEventListener("stream-reset", () => { if (current()) refresh(); });
        source.onerror = () => {
          source.close();
          if (entry.source !== source) return;
          entry.source = null;
          scheduleReconnect();
        };
        source.addEventListener("stream-error", source.onerror);
      } catch {
        scheduleReconnect();
      }
    };
    const visibilityChanged = () => {
      if (!pageVisible()) pause();
      else if (!entry.authFailed) {
        refresh();
        if (!entry.retry) connect();
      }
    };
    if (typeof document !== "undefined") document.addEventListener("visibilitychange", visibilityChanged);
    entry.cleanup = () => {
      pause();
      if (typeof document !== "undefined") document.removeEventListener("visibilitychange", visibilityChanged);
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
    entry.cleanup();
    subscriptions.delete(path);
  };
}
