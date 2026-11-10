import React from "react";
import { ShotPlanFields } from "./ShotPlanFields";
import { VisualEditingFields } from "./VisualEditingFields";
import { isBuiltinVideoProvider } from "../utils/visualProviders";

const inputClass = "mt-2 w-full rounded-xl border border-gray-300 bg-white p-3 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white";

export function StoryboardScene({ scene, index, video, narration, disabled, onChange }) {
  const diagram = scene.sentences.some(shot => shot.editing?.diagram);
  const moving = scene.sentences.some(shot =>
    (shot.shot_plan?.camera_movement && shot.shot_plan.camera_movement !== "STATIC") ||
    (shot.editing?.motion_style && shot.editing.motion_style !== "NONE") ||
    (shot.editing?.animation_preset && shot.editing.animation_preset !== "NONE")
  );
  return (
    <details key={index} className="group rounded-2xl border border-gray-200 bg-white transition open:shadow-sm dark:border-gray-700 dark:bg-gray-800/50">
      <summary className="flex cursor-pointer list-none items-start gap-3 p-4">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gray-100 text-xs font-bold text-gray-500 dark:bg-gray-700 dark:text-gray-300">{String(index + 1).padStart(2, "0")}</span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold">Scene {index + 1}: {scene.scene}</h3>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${diagram ? "bg-violet-50 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300" : "bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-300"}`}>
              {diagram ? "Animated diagram" : moving ? "Motion" : "Still"}
            </span>
          </div>
          <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
            {scene.sentences.map(shot => narration ? shot.sentence : shot.image_description).filter(Boolean).join(" ")}
          </p>
        </div>
        <span aria-hidden="true" className="mt-1 text-gray-400 transition group-open:rotate-180">⌄</span>
      </summary>
      <div className="space-y-5 border-t border-gray-100 p-4 dark:border-gray-700">
        {scene.sentences.map((shot, shotIndex) => (
          <div key={shotIndex} className="space-y-3">
            {scene.sentences.length > 1 && <p className="text-xs font-semibold text-gray-500">Shot {shotIndex + 1}</p>}
            {narration && <label className="block text-sm font-medium">Narration
              <textarea required maxLength={2000} rows={2} disabled={disabled} value={shot.sentence || ""} onChange={event => onChange(shotIndex, "sentence", event.target.value)} className={inputClass} />
            </label>}
            <label className="block text-sm font-medium">Visual prompt
              <textarea required maxLength={2000} rows={3} disabled={disabled} value={shot.image_description || ""} onChange={event => onChange(shotIndex, "image_description", event.target.value)} className={inputClass} />
            </label>
            {(video.mode === "AI" || video.settings?.ai_scene_editing) && (
              <details className="rounded-xl bg-gray-50 p-3 dark:bg-gray-900/50">
                <summary className="cursor-pointer text-xs font-medium text-gray-500">Motion, diagrams &amp; shot settings</summary>
                <div className="mt-3 space-y-4">
                  <ShotPlanFields plan={shot.shot_plan} disabled={disabled} narration={narration} onChange={plan => onChange(shotIndex, "shot_plan", plan)} />
                  {video.settings?.ai_scene_editing && shot.editing && <VisualEditingFields
                    editing={shot.editing} disabled={disabled}
                    photoAnimations={video.mode === "WEB" || (video.settings?.visual_type !== "VIDEO" && !isBuiltinVideoProvider(video.settings?.provider))}
                    onChange={value => onChange(shotIndex, "editing", value)}
                  />}
                </div>
              </details>
            )}
          </div>
        ))}
      </div>
    </details>
  );
}
