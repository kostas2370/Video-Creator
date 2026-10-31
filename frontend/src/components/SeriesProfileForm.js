import { useState } from "react";
import { CreationDraftContext, useCreationDraft } from "../hooks/useCreationDraft";
import { useDraftFile } from "../hooks/useDraftFile";
import { restoreWizardDraft } from "../utils/creationDrafts";
import { CreationDraftNotice } from "./ui/CreationDraftNotice";
import { getVoices, getIntro, getOutro } from "../api/apiService";
import { useAssetOptions } from "../hooks/useAssetOptions";
import { useObjectUrl } from "../hooks/useObjectUrl";
import { defaultSeries, seriesPayload, storyFormats, characterIsApproved } from "../utils/series";
import { SeriesCastEditor } from "./SeriesCastEditor";
import { SeriesCastDesigner } from "./SeriesCastDesigner";
import { CreationSteps } from "./ui/CreationSteps";
import { visualProviderNames, supportsVisualReference, isBuiltinVideoProvider } from "../utils/visualProviders";
import { videoFormats } from "../utils/videoFormats";
import { API_HOST } from "../endpoints";
import { MoreAssetOptions } from "./ui/MoreAssetOptions";
import { editorInput, editorButton } from "./ui/EditorDialog";

const styles = [
  { label: "3D animation", value: "Stylized 3D animation, expressive characters, rich colors, soft cinematic lighting." },
  { label: "Cinematic", value: "Cinematic realism, natural faces and textures, dramatic lighting, film-like color grading." },
  { label: "Storybook", value: "Soft storybook illustrations, warm colors, painted textures and gentle lighting." },
];
const choiceClass = active => `rounded-2xl border p-4 text-left text-sm transition ${active ? "border-indigo-400 bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200 dark:border-indigo-500 dark:bg-indigo-900/40 dark:text-indigo-200 dark:ring-indigo-900" : "border-gray-200 hover:border-indigo-300 dark:border-gray-700"}`;

function AssetSelect({ label, value, onChange, options, none }) {
  return <label className="block text-sm font-semibold">{label}
    <select value={value || ""} onChange={event => onChange(event.target.value)} className={`${editorInput} mt-2`}>
      <option value="">{none}</option>
      {value && !options.items.some(item => item.id === value) && <option value={value}>Saved selection</option>}
      {options.items.map(item => <option key={item.id} value={item.id}>{item.name || item.title || "Untitled"}{item.provider ? ` · ${item.provider}` : ""}</option>)}
    </select><MoreAssetOptions options={options} label={label.toLowerCase()} />
  </label>;
}

export function SeriesProfileForm({ initial, busy, onSave, onCancel, error }) {
  const draft = useCreationDraft(initial?.id ? `series:${initial.id}` : "series-new", {
    form: { ...defaultSeries, narration: false, visual_style: styles[0].value, ...initial }, step: 0,
    customStyle: !!initial && !styles.some(style => style.value === initial.visual_style),
    hasReferenceFile: false, removeReference: false, ui: {},
  }, restoreWizardDraft);
  const { form, step, customStyle, removeReference } = draft.value;
  const setForm = action => draft.update(previous => ({ ...previous, form: typeof action === "function" ? action(previous.form) : action }));
  const setStep = value => draft.update(previous => ({ ...previous, step: value }));
  const setCustomStyle = value => draft.update(previous => ({ ...previous, customStyle: value }));
  const setRemoveReference = value => draft.update(previous => ({ ...previous, removeReference: value }));
  const [validation, setValidation] = useState("");
  const referenceFile = useDraftFile(draft.key && `${draft.key}:reference`, draft.value.hasReferenceFile, value => draft.update(previous => ({ ...previous, hasReferenceFile: value })));
  const reference = referenceFile.file;
  const setReference = referenceFile.change;
  const [fileError, setFileError] = useState("");
  const preview = useObjectUrl(reference);
  const voices = useAssetOptions(getVoices);
  const intros = useAssetOptions(getIntro);
  const outros = useAssetOptions(getOutro);
  const change = (key, value) => setForm(current => ({ ...current, [key]: value }));
  const referenceSupported = supportsVisualReference(form.provider, "AI");
  const currentReference = initial?.reference_image && (/^https?:\/\//i.test(initial.reference_image) ? initial.reference_image : `${API_HOST}${initial.reference_image}`);
  const image = preview || (!removeReference && currentReference);
  const approvedCount = form.cast.filter(character => characterIsApproved(character, form.visual_style)).length;
  const navigate = target => {
    setValidation("");
    if (target > 0 && (!form.title.trim() || !form.premise.trim() || !form.visual_style.trim())) { setStep(0); setValidation("Add a series name, an idea and a visual style to continue."); return; }
    if (target > 1 && form.cast.some(character => !character.name.trim() || !character.appearance.trim())) { setStep(1); setValidation("Give each character a name and appearance. AI can write these for you."); return; }
    setStep(target);
  };
  const submit = async event => {
    event.preventDefault();
    if (busy) return;
    if (step < 2) { navigate(step + 1); return; }
    if (referenceFile.loading || (referenceFile.error && !reference)) return;
    if (!form.title.trim() || !form.premise.trim() || !form.visual_style.trim()) { navigate(1); return; }
    if (form.cast.some(character => !character.name.trim() || !character.appearance.trim())) { navigate(2); return; }
    if (form.narration && !form.voice_model) { setValidation("Choose a voice for narration, or turn voice-over off."); return; }
    if (!Number.isInteger(Number(form.scene_count)) || Number(form.scene_count) < 1 || Number(form.scene_count) > 60) { setValidation("Choose between 1 and 60 shots per episode."); return; }
    if (!fileError) {
      const result = await onSave(seriesPayload(form, reference, removeReference));
      if (result?.ok) { setReference(null); draft.clear(); }
    }
  };
  return <CreationDraftContext.Provider key={`${draft.key}:${draft.epoch}`} value={draft}><form noValidate onSubmit={submit} className="mx-auto max-w-4xl overflow-hidden rounded-3xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
    <fieldset disabled={busy}>
      <div className="border-b border-gray-100 px-5 py-6 sm:px-8 dark:border-gray-700"><p className="text-xs font-semibold uppercase tracking-widest text-indigo-500 dark:text-indigo-200">Series studio</p><h2 className="mt-2 text-2xl font-bold tracking-tight">{initial ? "Shape your series" : "One world. Endless stories."}</h2><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Start with an idea. Build a cast. Make it yours.</p></div>
      <div className="p-5 sm:p-8">
        <CreationDraftNotice draft={draft} onReset={() => { setReference(null); draft.reset(); setValidation(""); setFileError(""); }} />
        {referenceFile.error && <p role="alert" className="mb-4 text-sm text-amber-700 dark:text-amber-200">{referenceFile.error} <button type="button" onClick={() => setReference(null)} className="underline">Remove this reference</button></p>}
        <CreationSteps steps={["Idea", "Cast", "Finish"]} current={step} onSelect={navigate} disabled={busy} />
        {validation && <p role="alert" className="mb-5 rounded-xl bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-900/30 dark:text-amber-200">{validation}</p>}
        <div hidden={step !== 0}>
          <section aria-label="Series idea" className="space-y-6">
            <div><h3 className="text-xl font-bold">What’s the story?</h3><p className="mt-1 text-sm text-gray-500">A few details are enough to get started.</p></div>
            <label className="block text-sm font-semibold">Series name<input required maxLength={100} value={form.title} onChange={event => change("title", event.target.value)} className={`${editorInput} mt-2`} placeholder="Give your world a name" /></label>
            <label className="block text-sm font-semibold">What is this series about?<textarea required maxLength={2000} rows={4} value={form.premise} onChange={event => change("premise", event.target.value)} className={`${editorInput} mt-2 font-normal`} placeholder="Two unlikely friends get caught in a new mystery every episode…" /></label>
            <div><p className="mb-3 text-sm font-semibold">Story format</p><div className="grid gap-3 sm:grid-cols-3">{storyFormats.map(format => <button key={format.value} type="button" aria-pressed={form.story_format === format.value} onClick={() => change("story_format", format.value)} className={choiceClass(form.story_format === format.value)}><span className="font-semibold">{format.label}</span><span className="mt-2 block text-xs leading-relaxed opacity-70">{format.description}</span></button>)}</div></div>
            <div><p className="mb-3 text-sm font-semibold">Signature visual style</p><div className="grid grid-cols-2 gap-3 sm:grid-cols-4">{styles.map(style => <button type="button" key={style.label} aria-pressed={!customStyle && form.visual_style === style.value} onClick={() => { setCustomStyle(false); change("visual_style", style.value); }} className={choiceClass(!customStyle && form.visual_style === style.value)}>{style.label}</button>)}<button type="button" aria-pressed={customStyle} onClick={() => setCustomStyle(true)} className={choiceClass(customStyle)}>Custom style</button></div>{customStyle && <label className="mt-4 block text-sm font-semibold">Describe your style<textarea required maxLength={800} rows={3} value={form.visual_style} onChange={event => change("visual_style", event.target.value)} className={`${editorInput} mt-2 font-normal`} /></label>}</div>
          </section>
        </div>
        <div hidden={step !== 1}>
          <section aria-label="Series cast" className="space-y-6">
            <div><h3 className="text-xl font-bold">Meet your characters</h3><p className="mt-1 text-sm text-gray-500">Let AI write their descriptions, then choose how they look.</p></div>
            <details open={form.cast.length === 0 || !!draft.value.ui["cast-proposal"]?.draft} className="rounded-2xl border border-gray-200 p-4 dark:border-gray-700"><summary className="cursor-pointer text-sm font-semibold">{form.cast.length ? "Design a different cast with AI" : "Start with an AI-generated cast"}</summary><div className="mt-4"><SeriesCastDesigner premise={form.premise} visualStyle={form.visual_style} storyFormat={form.story_format} hasCast={form.cast.length > 0} onUse={value => change("cast", value)} /></div></details>
            <SeriesCastEditor cast={form.cast} visualStyle={form.visual_style} premise={form.premise} storyFormat={form.story_format} onChange={value => change("cast", value)} />
            {form.story_format === "GENERAL" && form.cast.length === 0 && <p className="text-xs text-gray-500">Characters are optional for a general series. Continue if your series doesn’t need a recurring cast.</p>}
          </section>
        </div>
        <div hidden={step !== 2}>
          <section aria-label="Series production" className="space-y-6">
            <div><h3 className="text-xl font-bold">Ready for your first episode?</h3><p className="mt-1 text-sm text-gray-500">Save your setup once. Reuse it for every new story.</p></div>
            <div className="rounded-2xl bg-gray-50 p-5 dark:bg-gray-900/40"><p className="font-semibold">{form.title || "Your series"}</p><p className="mt-1 text-sm text-gray-500">{storyFormats.find(format => format.value === form.story_format)?.label} · {form.scene_count} shots · {videoFormats.find(frame => frame.value === form.video_format)?.label}</p><p className="mt-3 text-xs text-gray-500">{form.cast.length ? `${approvedCount} of ${form.cast.length} character looks approved` : form.story_format === "GENERAL" ? "No recurring cast" : "Add a cast before drafting episode one"}. You can save now and finish character looks later.</p></div>
            <div className="grid gap-5 sm:grid-cols-2"><label className="block text-sm font-semibold">Frame<select value={form.video_format} onChange={event => change("video_format", event.target.value)} className={`${editorInput} mt-2`}>{videoFormats.map(item => <option key={item.value} value={item.value}>{item.label} · {item.ratio}</option>)}</select></label><label className="block text-sm font-semibold">Shots per episode<input type="number" min={1} max={60} value={form.scene_count} onChange={event => change("scene_count", event.target.value)} className={`${editorInput} mt-2`} /></label></div>
            <div className="flex flex-wrap gap-6"><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.narration} onChange={event => change("narration", event.target.checked)} />Voice-over</label><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.subtitles} onChange={event => change("subtitles", event.target.checked)} />Captions</label></div>
            {form.narration && <AssetSelect label="Narrator" none="Choose a voice" value={form.voice_model} onChange={value => change("voice_model", value)} options={voices} />}
            <details className="rounded-2xl border border-gray-200 p-4 dark:border-gray-700"><summary className="cursor-pointer text-sm font-semibold">Advanced settings <span className="ml-2 font-normal text-gray-400">{visualProviderNames[form.provider] || form.provider}</span></summary><div className="mt-5 space-y-5">
              <label className="block text-sm font-semibold">Visual provider<select value={form.provider} onChange={event => change("provider", event.target.value)} className={`${editorInput} mt-2`}>{Object.entries(visualProviderNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
              {form.cast.length > 0 && isBuiltinVideoProvider(form.provider) && <p className="text-xs text-gray-500">Each shot uses image credits to create a starting frame, then video credits to animate it.</p>}
              <label className="block text-sm font-semibold">World & shared continuity<textarea maxLength={2000} rows={3} value={form.characters} onChange={event => change("characters", event.target.value)} className={`${editorInput} mt-2 font-normal`} placeholder="Recurring places, important props or world rules" /></label>
              <div><label className="block text-sm font-semibold">Shared style reference <span className="font-normal text-gray-400">· optional</span><input type="file" accept="image/png,image/jpeg,image/webp" disabled={!referenceSupported} className="mt-3 block w-full text-sm" onChange={event => { const file = event.target.files?.[0]; setFileError(""); setReference(null); if (file?.size > 10 * 1024 * 1024) { setFileError("Choose an image smaller than 10 MB."); event.target.value = ""; return; } setReference(file || null); if (file) setRemoveReference(false); }} /></label><p className="mt-2 text-xs text-gray-500">{referenceSupported ? "References improve consistency; generated appearances can still vary." : "This provider does not support reference images."}</p>{image && <img src={image} alt="Series cast and style reference" className="mt-3 max-h-40 rounded-xl object-contain" />}{currentReference && <label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" checked={removeReference} onChange={event => { setRemoveReference(event.target.checked); if (event.target.checked) setReference(null); }} />Remove saved reference</label>}</div>
              <div className="grid gap-5 sm:grid-cols-2"><AssetSelect label="Intro" none="No intro" value={form.intro} onChange={value => change("intro", value)} options={intros} /><AssetSelect label="Outro" none="No outro" value={form.outro} onChange={value => change("outro", value)} options={outros} /></div>
            </div></details>
          </section>
        </div>
        {(error || fileError) && <p role="alert" className="mt-5 rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/40 dark:text-red-300">{error || fileError}</p>}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 bg-gray-50/60 px-5 py-5 sm:px-8 dark:border-gray-700 dark:bg-gray-900/20"><div className="flex gap-4">{step > 0 && <button type="button" onClick={() => navigate(step - 1)} className="text-sm font-semibold text-gray-600 dark:text-gray-300">Back</button>}{onCancel && <button type="button" onClick={onCancel} className="text-sm text-gray-500">Cancel</button>}</div><button type="submit" disabled={busy || !!fileError || (step === 2 && (referenceFile.loading || (!!referenceFile.error && !reference)))} className={editorButton}>{busy ? "Saving series…" : referenceFile.loading && step === 2 ? "Saving reference…" : step < 2 ? `Continue to ${step === 0 ? "cast" : "finish"}` : initial ? "Save changes" : "Create series"}</button></div>
    </fieldset>
  </form></CreationDraftContext.Provider>;
}
