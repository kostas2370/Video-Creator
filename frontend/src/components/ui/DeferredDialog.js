import React, { Suspense, useEffect, useState } from "react";
import { EditorDialog } from "./EditorDialog";

function LoadingDialog({ onClose, failed = false }) {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), 8000);
    return () => clearTimeout(timer);
  }, []);
  const stalled = failed || slow;
  return <EditorDialog open onClose={onClose} title={stalled ? "Editor could not finish loading" : "Loading editor…"} description={stalled ? "Reload the page to get the latest editor, or close this tool to continue working." : "Your tools will be ready in a moment."} maxWidth="max-w-lg">
    {stalled ? <div role="alert"><p className="text-sm text-gray-500 dark:text-gray-400">Reloading may discard unsaved changes in open editors.</p><div className="mt-4 flex gap-3"><button type="button" onClick={onClose} className="rounded-xl border border-gray-300 px-4 py-2 text-sm dark:border-gray-600">Close tool</button><button type="button" onClick={() => window.location.reload()} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white">Reload page</button></div></div> : <p role="status" className="text-sm text-gray-500 dark:text-gray-400">Loading…</p>}
  </EditorDialog>;
}

class ToolLoadBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return this.props.open ? <LoadingDialog failed onClose={this.props.onClose} /> : null;
    return this.props.children;
  }
}

// Load on first open, then retain drafts and background operation watchers on close.
export function DeferredDialog({ open, onClose, children }) {
  const [opened, setOpened] = useState(false);
  useEffect(() => { if (open) setOpened(true); }, [open]);
  if (!open && !opened) return null;
  return <ToolLoadBoundary open={open} onClose={onClose}><Suspense fallback={open ? <LoadingDialog onClose={onClose} /> : null}>{children}</Suspense></ToolLoadBoundary>;
}
