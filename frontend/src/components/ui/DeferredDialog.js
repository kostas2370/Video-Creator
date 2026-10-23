import { Suspense, useEffect, useState } from "react";
import { EditorDialog } from "./EditorDialog";

// Load on first open, then retain drafts and background operation watchers on close.
export function DeferredDialog({ open, onClose, children }) {
  const [opened, setOpened] = useState(false);
  useEffect(() => { if (open) setOpened(true); }, [open]);
  if (!open && !opened) return null;
  return <Suspense fallback={open ? <EditorDialog open onClose={onClose} title="Loading editor…" description="Your tools will be ready in a moment." maxWidth="max-w-lg"><p role="status" className="text-sm text-gray-500 dark:text-gray-400">Loading…</p></EditorDialog> : null}>
    {children}
  </Suspense>;
}
