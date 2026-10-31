import { createContext, useContext, useRef, useState } from "react";
import useAuth from "./useAuth";
import { creationDraftKey, creationDraftOwner, readCreationDraft } from "../utils/creationDrafts";

export const CreationDraftContext = createContext(null);

export function useDraftOwner() {
  const { user, access_token } = useAuth();
  return creationDraftOwner(user, access_token);
}

export function useCreationDraft(kind, defaults, restore = value => value) {
  const owner = useDraftOwner();
  const key = creationDraftKey(owner, kind);
  const initialize = () => {
    const saved = readCreationDraft(key);
    let value = defaults;
    try { if (saved) value = restore(saved.value, defaults); } catch { return { key, value: defaults, restored: false, error: "", epoch: 0, closed: false }; }
    return { key, value, restored: !!saved, error: "", epoch: 0, closed: false };
  };
  let [frame, setFrame] = useState(initialize);
  if (frame.key !== key) { frame = initialize(); setFrame(frame); }
  const current = useRef(frame);
  current.current = frame;
  const epoch = frame.epoch;
  const update = action => {
    const previous = current.current;
    if (previous.key !== key || previous.epoch !== epoch || previous.closed) return;
    const value = typeof action === "function" ? action(previous.value) : action;
    let error = "";
    if (key) {
      try { localStorage.setItem(key, JSON.stringify({ version: 1, savedAt: Date.now(), value })); }
      catch { error = "Your browser could not save this draft. Keep this page open or save the project before leaving."; }
    }
    const next = { ...previous, value, error };
    current.current = next; setFrame(next);
  };
  const clear = () => {
    if (key) try { localStorage.removeItem(key); } catch { return; }
    if (current.current.key === key && current.current.epoch === epoch) {
      const next = { ...current.current, epoch: epoch + 1, closed: true };
      current.current = next; setFrame(next);
    }
  };
  const reset = () => {
    clear();
    const next = { key, value: defaults, restored: false, error: "", epoch: current.current.epoch + 1, closed: false };
    current.current = next; setFrame(next);
  };
  return { ...frame, update, clear, reset };
}

export function useDraftSection(key, defaults) {
  const context = useContext(CreationDraftContext);
  const [fallback, setFallback] = useState(defaults);
  if (!context) return [fallback, setFallback];
  const value = context.value.ui?.[key] || defaults;
  const update = action => context.update(previous => {
    const before = previous.ui?.[key] || defaults;
    return { ...previous, ui: { ...previous.ui, [key]: typeof action === "function" ? action(before) : action } };
  });
  return [value, update];
}
