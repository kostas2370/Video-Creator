import React from "react";

const shotSizes = [["WIDE", "Wide"], ["MEDIUM", "Medium"], ["CLOSE_UP", "Close-up"], ["DETAIL", "Detail"]];
const movements = [["STATIC", "Static"], ["PAN_LEFT", "Pan left"], ["PAN_RIGHT", "Pan right"], ["TILT_UP", "Tilt up"], ["TILT_DOWN", "Tilt down"], ["PUSH_IN", "Push in"], ["PULL_OUT", "Pull out"]];
const controlClass = "mt-2 w-full rounded-xl border border-gray-300 bg-white p-3 text-sm text-gray-900 focus:border-blue-500 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-900 dark:text-white";

export function ShotPlanFields({ plan = {}, onChange, disabled = false, narration = true }) {
  const change = (field, value) => onChange({ ...plan, [field]: value });
  return <fieldset disabled={disabled} className="rounded-xl bg-gray-50 p-3 dark:bg-gray-900/50">
    <legend className="px-1 text-sm font-semibold">Shot plan</legend>
    <div className="grid gap-3 sm:grid-cols-2">
      <label className="block text-sm font-medium">Shot size
        <select value={plan.shot_size || ""} onChange={event => change("shot_size", event.target.value)} className={controlClass}>
          <option value="">Use visual prompt</option>
          {shotSizes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
      <label className="block text-sm font-medium">Camera / image motion
        <select value={plan.camera_movement || ""} onChange={event => change("camera_movement", event.target.value)} className={controlClass}>
          <option value="">Use existing direction</option>
          {movements.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
    </div>
    <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Camera direction guides generated clips. For still images it becomes a pan or zoom in the editor. Shot choices take priority over conflicting visual prompt directions.</p>
    <label className="mt-3 block text-sm font-medium">Subject action
      <textarea value={plan.subject_action || ""} maxLength={500} rows={2} onChange={event => change("subject_action", event.target.value)} placeholder="What does the subject do in this shot?" className={controlClass} />
    </label>
    <label className="mt-3 block text-sm font-medium">Target duration (seconds)
      <input type="number" min={0.5} max={30} step={0.1} value={plan.target_duration ?? ""} onChange={event => change("target_duration", event.target.value === "" ? null : Number(event.target.value))} className={controlClass} />
      <span className="mt-2 block text-xs font-normal text-gray-500 dark:text-gray-400">{narration ? "A planning estimate. Recorded narration sets the scene length; this does not shorten speech." : "Sets the scene length without narration. Available generated clip lengths depend on your provider."}</span>
    </label>
  </fieldset>;
}
