import React, { useState } from "react";
import { reviewStartingImage } from "../api/apiService";

const verdictLabels = { ready: "Looks ready", needs_changes: "Changes suggested", uncertain: "Needs a closer look" };
const categoryLabels = { character: "Character appearance", shot: "Shot details", composition: "Composition", quality: "Image quality" };

export const SceneImageReview = ({ scene, disabled, edited, onUseDescription, onSaved }) => {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const review = edited ? null : result || scene.starting_image_review;
  const run = async () => {
    if (busy || disabled || edited) return;
    setBusy(true);
    setError("");
    try {
      const response = await reviewStartingImage(scene.id, scene.starting_asset);
      if (!response?.ok) {
        setError(response?.message || "Could not review this image. Please try again.");
      } else if (response.data?.source_key === scene.starting_image_review_key) {
        setResult(response.data);
        onSaved(true);
      } else {
        setError("The image or shot changed. Refresh and review the current image.");
        onSaved(true);
      }
    } catch {
      setError("Could not review this image. Please try again.");
    } finally {
      setBusy(false);
    }
  };
  return <section aria-label="AI starting image review" className="mt-4 border-t border-gray-200 pt-3 dark:border-gray-700">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h3 className="text-sm font-medium">{review ? verdictLabels[review.verdict] : "Optional AI check"}</h3>
      <button type="button" disabled={disabled || edited || busy} onClick={run} className="rounded-lg px-2 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-50 disabled:opacity-50 dark:text-blue-300 dark:hover:bg-blue-950">{busy ? "Reviewing image…" : review ? "Review again with AI" : "Review image with AI"}</button>
    </div>
    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{edited ? "Generate your updated image before reviewing it." : "One paid AI request per check. AI can miss details."}</p>
    {busy && <p role="status" className="mt-2 text-xs text-gray-500">Checking character appearance, shot details, composition and image quality…</p>}
    {error && <p role="alert" className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>}
    {review && <div className="mt-3 space-y-2" aria-live="polite">
      <p className="text-xs leading-relaxed text-gray-600 dark:text-gray-300">{review.summary}</p>
      {(review.findings?.length > 0 || review.suggested_description) && <details>
        <summary className="cursor-pointer text-xs text-gray-500 dark:text-gray-400">Review details</summary>
        {review.findings?.length > 0 && <ul className="mt-3 space-y-3 text-xs">{review.findings.map((finding, index) => <li key={index}><p className="font-medium">{categoryLabels[finding.category]}</p><p className="mt-1">{finding.issue}</p><p className="mt-1 text-gray-500 dark:text-gray-400">Suggested fix: {finding.fix}</p></li>)}</ul>}
        {review.suggested_description && <div className="mt-3 text-xs"><p className="font-medium">Suggested shot description</p><p className="mt-1 whitespace-pre-wrap text-gray-600 dark:text-gray-300">{review.suggested_description}</p></div>}
      </details>}
      {review.suggested_description && <button type="button" disabled={disabled || busy} onClick={() => onUseDescription(review.suggested_description)} className="rounded-lg bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700 disabled:opacity-50 dark:bg-blue-900/30 dark:text-blue-300">Use suggested description</button>}
    </div>}
  </section>;
};
