import { Dialog, DialogBackdrop, DialogPanel, DialogTitle, Description } from "@headlessui/react";
import { HiOutlineXMark } from "react-icons/hi2";

export const editorInput = "block w-full rounded-xl border border-gray-200 bg-gray-50 p-3 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-900 dark:text-white";
export const editorButton = "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-40 dark:focus-visible:ring-offset-gray-900";
export const editorSecondaryButton = "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-gray-200 px-4 py-3 text-sm font-semibold text-gray-600 transition-colors hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700";
export const editorDangerButton = "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-red-600 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 disabled:cursor-not-allowed disabled:opacity-40";

export function EditorDialog({ open, onClose, title, description, busy = false, children, footer, maxWidth = "max-w-3xl", panelClassName = "", icon: Icon, tone = "default", closeLabel = "Close editor" }) {
  const close = () => { if (!busy) onClose(); };
  return <Dialog open={open} onClose={close} className="relative z-50">
    <DialogBackdrop className="fixed inset-0 bg-gray-950/65 backdrop-blur-sm" />
    <div className="fixed inset-0 overflow-y-auto"><div className="flex min-h-full items-center justify-center p-3 sm:p-6">
      <DialogPanel aria-busy={busy} className={`app-dialog ${panelClassName} flex max-h-[calc(100dvh-1.5rem)] w-full ${maxWidth} flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white text-gray-900 shadow-2xl dark:border-gray-700 dark:bg-gray-800 dark:text-white sm:max-h-[calc(100dvh-3rem)]`}>
        <header className="editor-dialog-header flex shrink-0 items-start gap-3 border-b border-gray-100 p-4 sm:gap-4 sm:p-6 dark:border-gray-700">
          {Icon && <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${tone === "danger" ? "bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-300" : "bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-300"}`}><Icon aria-hidden="true" className="h-5 w-5" /></span>}
          <div className="min-w-0 flex-1"><DialogTitle className="break-words text-lg font-bold tracking-tight sm:text-xl">{title}</DialogTitle>{description && <Description className="mt-1.5 text-sm leading-relaxed text-gray-500 dark:text-gray-400">{description}</Description>}</div>
          <button type="button" disabled={busy} aria-label={closeLabel} onClick={close} className="-mr-1 -mt-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-40 dark:hover:bg-gray-700 dark:hover:text-white"><HiOutlineXMark aria-hidden="true" className="h-5 w-5" /></button>
        </header>
        {children != null && <div className="editor-dialog-body min-h-0 flex-1 overflow-y-auto overscroll-contain p-4 sm:p-6">{children}</div>}
        {footer && <div className="editor-dialog-footer shrink-0 border-t border-gray-100 bg-white px-4 py-3 sm:px-6 sm:py-4 dark:border-gray-700 dark:bg-gray-800">{footer}</div>}
      </DialogPanel>
    </div></div>
  </Dialog>;
}
