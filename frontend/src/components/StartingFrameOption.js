import React from "react";
import { isBuiltinVideoProvider, supportsVisualReference } from "../utils/visualProviders";

export function StartingFrameOption({ mode, provider, checked, onChange, disabled, required = false }) {
  if (!isBuiltinVideoProvider(provider) || !supportsVisualReference(provider, mode)) return null;
  return <label className="flex items-start gap-3 rounded-xl border border-gray-200 p-4 text-sm dark:border-gray-700">
    <input type="checkbox" checked={required || checked} disabled={disabled || required} onChange={event => onChange(event.target.checked)} className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600" />
    <span><span className="block font-semibold">Review starting frames before generating</span><span className="mt-1 block text-xs leading-relaxed text-gray-500 dark:text-gray-400">{required ? "Required for this video's character references." : "Generate an image for each shot, then approve it before animation. Adds image generation costs; no character reference needed."}</span></span>
  </label>;
}
