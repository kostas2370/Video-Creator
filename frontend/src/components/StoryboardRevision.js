import React, { useState } from "react";
import { reviseStoryboard } from "../api/apiService";
import { editorInput } from "./ui/EditorDialog";

export function StoryboardRevision({ videoId, storyboard, disabled, onApply }) {
  const [instructions, setInstructions] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [proposal, setProposal] = useState(null);
  const stale = proposal && proposal.source !== JSON.stringify(storyboard);

  const revise = async () => {
    if (disabled || busy || !instructions.trim()) return;
    const source = JSON.stringify(storyboard);
    setBusy(true);
    setError("");
    try {
      const response = await reviseStoryboard(videoId, { storyboard, instructions: instructions.trim() });
      if (!response?.ok) {
        setError(response?.message || "Could not revise the storyboard. Please try again.");
      } else {
        setProposal({ source, storyboard: response.data });
      }
    } catch {
      setError("Could not revise the storyboard. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-label="Revise storyboard with AI" className="mb-5 rounded-xl border border-indigo-200 bg-indigo-50/50 p-4 dark:border-indigo-800 dark:bg-indigo-950/20">
      <h3 className="text-sm font-semibold">Revise storyboard with AI</h3>
      <p className="mt-1 text-xs text-gray-500">Describe your changes. Preview the proposal before applying it. One paid AI request; media is generated only after Proceed.</p>
      <label className="mt-3 block text-sm">
        What would you like to change?
        <textarea
          rows={2}
          maxLength={2000}
          value={instructions}
          disabled={disabled || busy}
          onChange={event => setInstructions(event.target.value)}
          placeholder="Make it more suspenseful, shorten it to six scenes, and keep the same characters."
          className={`${editorInput} mt-2`}
        />
      </label>
      <button type="button" disabled={disabled || busy || !instructions.trim()} onClick={revise} className="mt-3 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">
        {busy ? "Revising storyboard…" : "Suggest revision"}
      </button>
      {busy && <p role="status" className="mt-2 text-xs">Preparing a revised storyboard. Your current edits are preserved.</p>}
      {error && <p role="alert" className="mt-2 text-sm text-red-600">{error}</p>}
      {proposal && (
        <div className="mt-4 rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900">
          <h4 className="text-sm font-semibold">Proposed storyboard · {proposal.storyboard.scenes.length} scenes</h4>
          <p className="mt-1 text-xs text-gray-500">Compare with your current storyboard below. Applying replaces its text and shot settings.</p>
          <div className="mt-3 max-h-80 space-y-3 overflow-y-auto text-sm">
            <p className="font-semibold">{proposal.storyboard.title}</p>
            {proposal.storyboard.visual_continuity && <p><strong>Character &amp; setting continuity:</strong> {proposal.storyboard.visual_continuity}</p>}
            {proposal.storyboard.scenes.map((scene, index) => (
              <div key={index} className="border-t border-gray-100 pt-2 dark:border-gray-700">
                <p className="font-semibold">Scene {index + 1}: {scene.scene}</p>
                {scene.sentences.map((shot, shotIndex) => (
                  <div key={shotIndex} className="mt-2 space-y-1">
                    {shot.sentence && <p><strong>Narration:</strong> {shot.sentence}</p>}
                    <p><strong>Visual:</strong> {shot.image_description}</p>
                    {shot.shot_plan && <p className="text-xs text-gray-500">{shot.shot_plan.shot_size} · {shot.shot_plan.camera_movement} · {shot.shot_plan.subject_action} · {shot.shot_plan.target_duration}s</p>}
                  </div>
                ))}
              </div>
            ))}
          </div>
          {stale && <p role="status" className="mt-3 text-xs text-amber-700">Your storyboard changed. Request a new revision before applying.</p>}
          <div className="mt-3 flex gap-4">
            <button type="button" disabled={disabled || busy || stale} onClick={() => {
              onApply(proposal.storyboard);
              setProposal(null);
              setInstructions("");
            }} className="text-sm font-semibold text-indigo-600 disabled:opacity-50">Apply revision</button>
            <button type="button" disabled={disabled || busy} onClick={() => setProposal(null)} className="text-sm text-gray-500">Discard revision</button>
          </div>
        </div>
      )}
    </section>
  );
}
