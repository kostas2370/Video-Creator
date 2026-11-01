import { useState } from "react";
import { readWorkspace, saveWorkspace } from "../../utils/editorWorkspace";

export function RememberedDetails({ videoId, panel, defaultOpen = false, children, ...props }) {
  const key = `${videoId}:${panel}`;
  const savedOpen = readWorkspace(videoId)[panel];
  const initialOpen = typeof savedOpen === "boolean" ? savedOpen : defaultOpen;
  const [state, setState] = useState(() => ({ key, open: initialOpen }));
  const open = state.key === key ? state.open : initialOpen;
  return <details {...props} open={open} onToggle={event => {
    const next = event.currentTarget.open;
    if (next === open) return;
    setState({ key, open: next });
    saveWorkspace(videoId, { [panel]: next });
  }}>{children}</details>;
}
