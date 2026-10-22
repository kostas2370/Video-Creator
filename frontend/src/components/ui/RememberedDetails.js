import { useState } from "react";
import { readWorkspace, saveWorkspace } from "../../utils/editorWorkspace";

export function RememberedDetails({ videoId, panel, children, ...props }) {
  const key = `${videoId}:${panel}`;
  const [state, setState] = useState(() => ({ key, open: readWorkspace(videoId)[panel] === true }));
  const open = state.key === key ? state.open : readWorkspace(videoId)[panel] === true;
  return <details {...props} open={open} onToggle={event => {
    const next = event.currentTarget.open;
    if (next === open) return;
    setState({ key, open: next });
    saveWorkspace(videoId, { [panel]: next });
  }}>{children}</details>;
}
