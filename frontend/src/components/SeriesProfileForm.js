import { useState } from "react";
import { getVoices, getIntro, getOutro } from "../api/apiService";
import { useAssetOptions } from "../hooks/useAssetOptions";
import { useObjectUrl } from "../hooks/useObjectUrl";
import { defaultSeries, seriesPayload } from "../utils/series";
import { visualProviderNames, supportsVisualReference } from "../utils/visualProviders";
import { videoFormats } from "../utils/videoFormats";
import { API_HOST } from "../endpoints";
import { MoreAssetOptions } from "./ui/MoreAssetOptions";
import { editorInput, editorButton } from "./ui/EditorDialog";

function AssetSelect({ label, value, onChange, options, none, required = false }) {
  return <label className="block text-sm font-semibold">{label}
    <select required={required} value={value || ""} onChange={event => onChange(event.target.value)} className={`${editorInput} mt-2`}>
      <option value="">{none}</option>
      {value && !options.items.some(item => item.id === value) && <option value={value}>Saved selection</option>}
      {options.items.map(item => <option key={item.id} value={item.id}>{item.name || item.title || "Untitled"}{item.provider ? ` · ${item.provider}` : ""}</option>)}
    </select>
    <MoreAssetOptions options={options} label={label.toLowerCase()} />
  </label>;
}

export function SeriesProfileForm({ initial, busy, onSave, onCancel, error }) {
  const [form, setForm] = useState({ ...defaultSeries, ...initial });
  const [reference, setReference] = useState(null);
  const [removeReference, setRemoveReference] = useState(false);
  const [fileError, setFileError] = useState("");
  const preview = useObjectUrl(reference);
  const voices = useAssetOptions(getVoices);
  const intros = useAssetOptions(getIntro);
  const outros = useAssetOptions(getOutro);
  const change = (key, value) => setForm(current => ({ ...current, [key]: value }));
  const referenceSupported = supportsVisualReference(form.provider, "AI");
  const currentReference = initial?.reference_image && (/^https?:\/\//i.test(initial.reference_image) ? initial.reference_image : `${API_HOST}${initial.reference_image}`);
  const image = preview || (!removeReference && currentReference);
  return <form onSubmit={event => { event.preventDefault(); if (!fileError) onSave(seriesPayload(form, reference, removeReference)); }} className="rounded-2xl border border-gray-200 bg-white p-5 sm:p-7 dark:border-gray-700 dark:bg-gray-800">
    <fieldset disabled={busy} className="space-y-7">
      <div><h2 className="text-xl font-bold">{initial ? "Series setup" : "Create your series"}</h2><p className="mt-2 text-sm leading-relaxed text-gray-500 dark:text-gray-400">Save the world, cast and production choices once. Changes here apply to future episodes.</p></div>
      <section className="space-y-5" aria-labelledby="series-story-heading"><div className="border-b border-gray-100 pb-3 dark:border-gray-700"><h3 id="series-story-heading" className="font-bold"><span className="mr-2 text-indigo-500">01</span>The story &amp; world</h3><p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Give every episode a shared identity.</p></div>
      <label className="block text-sm font-semibold">Series name<input required maxLength={100} value={form.title} onChange={event => change("title", event.target.value)} className={`${editorInput} mt-2`} placeholder="Milo’s little discoveries" /></label>
      <label className="block text-sm font-semibold">What is this series about?<textarea required maxLength={2000} rows={3} value={form.premise} onChange={event => change("premise", event.target.value)} className={`${editorInput} mt-2`} placeholder="A curious fox explores everyday science in a woodland village. Each episode answers one question for young learners." /><span className="mt-2 block text-xs font-normal text-gray-500">Include your audience, tone and any rules every episode should follow.</span></label>
      <label className="block text-sm font-semibold">Recurring characters &amp; world<textarea maxLength={2000} rows={4} value={form.characters} onChange={event => change("characters", event.target.value)} className={`${editorInput} mt-2`} placeholder="Milo: a small orange fox with a cream muzzle, round glasses and a teal scarf. Curious, patient and a little clumsy. His workshop is inside an old oak tree." /><span className="mt-2 block text-xs font-normal text-gray-500">Describe names, identifying details, personalities and recurring locations. Leave blank for a series without recurring characters.</span></label>
      </section>
      <section className="space-y-5" aria-labelledby="series-look-heading"><div className="border-b border-gray-100 pb-3 dark:border-gray-700"><h3 id="series-look-heading" className="font-bold"><span className="mr-2 text-indigo-500">02</span>The look</h3><p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Set a recognizable style for the whole series.</p></div>
      <label className="block text-sm font-semibold">Signature visual style<textarea required maxLength={800} rows={3} value={form.visual_style} onChange={event => change("visual_style", event.target.value)} className={`${editorInput} mt-2`} placeholder="Soft storybook illustrations, warm woodland colors, gentle light and simple compositions." /></label>
      <div className="grid gap-5 sm:grid-cols-2">
        <label className="block text-sm font-semibold">Visual provider<select value={form.provider} onChange={event => change("provider", event.target.value)} className={`${editorInput} mt-2`}>{Object.entries(visualProviderNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label className="block text-sm font-semibold">Frame<select value={form.video_format} onChange={event => change("video_format", event.target.value)} className={`${editorInput} mt-2`}>{videoFormats.map(item => <option key={item.value} value={item.value}>{item.label} · {item.ratio}</option>)}</select></label>
      </div>
      <div className="rounded-xl border border-dashed border-gray-300 p-4 dark:border-gray-600">
        <label className="block text-sm font-semibold">Cast &amp; style reference <span className="font-normal text-gray-500">(optional)</span><input type="file" accept="image/png,image/jpeg,image/webp" disabled={!referenceSupported} className="mt-3 block w-full text-sm" onChange={event => {
          const file = event.target.files?.[0]; setFileError(""); setReference(null);
          if (file?.size > 10 * 1024 * 1024) { setFileError("Choose an image smaller than 10 MB."); event.target.value = ""; return; }
          setReference(file || null); if (file) setRemoveReference(false);
        }} /></label>
        <p className="mt-3 text-xs leading-relaxed text-gray-500 dark:text-gray-400">One reference image is reused across episodes. A cast sheet can show several recurring characters. PNG, JPEG or WebP, up to 10 MB. {referenceSupported ? "References improve consistency; generated appearances can still vary." : "This provider does not support reference images."}</p>
        {image && <img src={image} alt="Series cast and style reference" className="mt-4 max-h-44 rounded-lg object-contain" />}
        {currentReference && <label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" checked={removeReference} onChange={event => { setRemoveReference(event.target.checked); if (event.target.checked) setReference(null); }} />Remove saved reference</label>}
        {fileError && <p role="alert" className="mt-2 text-sm text-red-600">{fileError}</p>}
      </div>
      </section>
      <section className="space-y-5" aria-labelledby="series-production-heading"><div className="border-b border-gray-100 pb-3 dark:border-gray-700"><h3 id="series-production-heading" className="font-bold"><span className="mr-2 text-indigo-500">03</span>Episode defaults</h3><p className="mt-1 text-xs text-gray-500 dark:text-gray-400">Reuse these choices. Review each storyboard before making media.</p></div>
      <div className="grid gap-5 sm:grid-cols-2">
        <div><label className="mb-3 flex items-center gap-2 text-sm font-semibold"><input type="checkbox" checked={form.narration} onChange={event => change("narration", event.target.checked)} />Use the same narrator</label>{form.narration && <AssetSelect required label="Narrator" none="Choose a voice" value={form.voice_model} onChange={value => change("voice_model", value)} options={voices} />}</div>
        <label className="block text-sm font-semibold">Shots per episode<input required type="number" min={1} max={60} value={form.scene_count} onChange={event => change("scene_count", event.target.value)} className={`${editorInput} mt-2`} /><span className="mt-2 block text-xs font-normal text-gray-500">You can change the storyboard before generating media.</span></label>
      </div>
      <details className="rounded-xl border border-gray-200 p-4 dark:border-gray-700"><summary className="cursor-pointer text-sm font-semibold">Intro &amp; outro <span className="ml-1 font-normal text-gray-500">Optional branding</span></summary><div className="mt-4 grid gap-5 sm:grid-cols-2">
        <AssetSelect label="Intro" none="No intro" value={form.intro} onChange={value => change("intro", value)} options={intros} />
        <AssetSelect label="Outro" none="No outro" value={form.outro} onChange={value => change("outro", value)} options={outros} />
      </div>
      </details>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.subtitles} onChange={event => change("subtitles", event.target.checked)} />Add captions to every episode</label>
      </section>
      {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{error}</p>}
      <div className="flex flex-wrap items-center gap-3 border-t border-gray-100 pt-5 dark:border-gray-700"><button type="submit" disabled={busy || !!fileError} className={editorButton}>{busy ? "Saving series…" : initial ? "Save changes" : "Create series"}</button>{onCancel && <button type="button" onClick={onCancel} className="rounded-xl border border-gray-300 px-5 py-3 text-sm font-semibold dark:border-gray-600">Cancel</button>}</div>
    </fieldset>
  </form>;
}
