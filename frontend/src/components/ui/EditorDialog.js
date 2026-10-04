import { Dialog, DialogPanel, DialogTitle, Description } from "@headlessui/react";

export const editorInput = "block w-full rounded-xl border border-gray-200 bg-gray-50 p-3 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white";
export const editorButton = "rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40";

export function EditorDialog({ open, onClose, title, description, busy, children }) {
  return <Dialog open={open} onClose={() => !busy && onClose()} className="relative z-50">
    <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-sm" aria-hidden="true" />
    <div className="fixed inset-0 overflow-y-auto"><div className="flex min-h-full items-center justify-center p-4">
      <DialogPanel className="w-full max-w-3xl rounded-2xl bg-white shadow-xl dark:bg-gray-800">
        <header className="flex items-start justify-between gap-4 border-b border-gray-100 p-6 dark:border-gray-700">
          <div><DialogTitle className="text-xl font-semibold text-gray-900 dark:text-white">{title}</DialogTitle><Description className="mt-1 text-sm text-gray-500 dark:text-gray-400">{description}</Description></div>
          <button type="button" disabled={busy} aria-label="Close editor" onClick={onClose} className="rounded-lg px-3 py-1 text-xl text-gray-400 hover:bg-gray-100 disabled:opacity-40 dark:hover:bg-gray-700">×</button>
        </header>
        <div className="p-6">{children}</div>
      </DialogPanel>
    </div></div>
  </Dialog>;
}
