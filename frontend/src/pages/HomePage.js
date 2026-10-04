import React, { useState, useEffect, useRef } from "react";
import { getAvatars, getTemplates, getVoices, getCustomVisualProviders } from "../api/apiService";
import { toast } from "react-toastify";
import { deleteTemplate, generateVideo } from "../api/apiService";
import { pollVideo } from "../api/pollVideo";
import { Link } from "react-router-dom";
import { RiSparkling2Line, RiArrowRightLine, RiVolumeUpLine, RiImageLine, RiSettings3Line, RiArrowDownSLine } from "react-icons/ri";
import { ProceedModal } from "../components/ProceedModal";
import { SaveTemplateModal } from "../components/SaveTemplateModal";
import { DeleteModal } from "../components/DeleteModal";
import { useAxiosPrivate } from "../hooks/useAxiosPrivate";

const ttsProviderNames = {
  OPENAI: "OpenAI",
  ELEVENLABS: "ElevenLabs",
  SIXTYDB: "60dB",
};
const visualProviderNames = { "DALL-E": "OpenAI images", sora: "OpenAI Sora (video)", midjourney: "Midjourney", "stable-diffusion": "Stable Diffusion" };

const isBuiltinVisualProvider = name => Object.prototype.hasOwnProperty.call(visualProviderNames, name);

const inputClassName =
  "w-full p-3 mt-2 bg-gray-50 border border-gray-200 text-gray-900 text-sm rounded-xl focus:ring-blue-500 focus:border-blue-500 disabled:opacity-60 dark:bg-gray-900/50 dark:border-gray-600 dark:text-white dark:placeholder-gray-400";

const Home = () => {
  const isOpenFunction = (data) => {
    setOpen(data);
  };
  const [avatars, setAvatars] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [voices, setVoices] = useState([]);
  const [visualProviders, setVisualProviders] = useState([]);
  const [visualProvidersLoading, setVisualProvidersLoading] = useState(true);
  const [visualProvidersError, setVisualProvidersError] = useState("");
  const [providerReload, setProviderReload] = useState(0);
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [settings, setSettings] = useState(false);
  const [open, setOpen] = useState(false);
  const [video_id, setVideo_id] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [deletingTemplate, setDeletingTemplate] = useState(false);

  const [formData, setFormData] = useState({
    genre: "",
    template: "",
    avatar_selection: "",
    voice_id: "",
    message: "",
    target_audience: "",
    image_mode: "WEB",
    gpt_model: "gpt-5.4-mini",
    style: "natural",
    music: "",
    provider: "bing",
    subtitles: true,
    narration: true,
    avatar_position: "top,left",
  });

  useAxiosPrivate();
  const pollRef = useRef(null);

  useEffect(() => () => pollRef.current?.cancel(), []);

  useEffect(() => {
    let current = true;
    setVisualProvidersLoading(true);
    getCustomVisualProviders().then((result) => {
      if (!current) return;
      if (result.ok) {
        setVisualProviders(Array.isArray(result.data) ? result.data : result.data?.results ?? []);
        setVisualProvidersError("");
      } else {
        setVisualProvidersError(result.message);
      }
      setVisualProvidersLoading(false);
    });
    return () => { current = false; };
  }, [providerReload]);

  const handleInputChange = (event) => {
    const { name, value, type, checked } = event.target;

    if (type === "checkbox") {
      setFormData((prevData) => ({ ...prevData, [name]: checked }));
      return;
    }

    if (name === "template") {
      const selectedTemplate = templates.find(
        (t) => String(t.id) === String(value)
      );

      if (selectedTemplate) {
        setFormData((prevData) => ({
          ...prevData,
          template: selectedTemplate.id,
          message: selectedTemplate.message ?? prevData.message,
          genre: selectedTemplate.genre ?? "",
          target_audience: selectedTemplate.target_audience ?? "",
          avatar_selection: selectedTemplate.avatar_selection ?? "",
          voice_id: selectedTemplate.voice_id ?? "",
          gpt_model: selectedTemplate.gpt_model ?? prevData.gpt_model,
          image_mode: selectedTemplate.image_mode ?? prevData.image_mode,
          style: selectedTemplate.style ?? prevData.style,
          music: selectedTemplate.music ?? "",
          provider:
            selectedTemplate.provider ??
            (selectedTemplate.image_mode === "AI" ? "DALL-E" : "bing"),
          subtitles: selectedTemplate.subtitles ?? prevData.subtitles,
          narration: selectedTemplate.narration ?? prevData.narration,
          avatar_position:
            selectedTemplate.avatar_position ?? prevData.avatar_position,
        }));
      } else {
        setFormData((prevData) => ({ ...prevData, template: "" }));
      }
      return;
    }

    if (name === "image_mode") {
      setFormData((prevData) => ({
        ...prevData,
        [name]: value,
        provider: value === "AI" ? "DALL-E" : "bing",
      }));
    } else if (name === "avatar_selection") {
      setFormData((prevData) => ({
        ...prevData,
        [name]: value,
        voice_id: value ? "" : prevData.voice_id,
      }));
    } else {
      setFormData((prevData) => ({ ...prevData, [name]: value }));
    }
  };

  useEffect(() => {
    let current = true;
    Promise.all([getAvatars(), getVoices(), getTemplates()]).then(([{ data: avatarData }, { data: voiceData }, { data: templateData }]) => {
      if (!current) return;
      setAvatars(Array.isArray(avatarData) ? avatarData : []);
      setVoices(Array.isArray(voiceData) ? voiceData : []);
      setTemplates(Array.isArray(templateData) ? templateData : []);
      setOptionsLoading(false);
    });
    return () => { current = false; };
  }, []);

  const settingsForTemplate = Object.fromEntries(
    Object.entries(formData).filter(([field]) => field !== "template")
  );

  const selectedTemplate = templates.find(
    (t) => String(t.id) === String(formData.template)
  );

  const dropTemplate = (updater) => {
    setTemplates(updater);
    setFormData((prevData) => ({ ...prevData, template: "" }));
  };

  const handleTemplateSaved = (saved) => {
    setTemplates((prevTemplates) => [...prevTemplates, saved]);
    setFormData((prevData) => ({ ...prevData, template: saved.id }));
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (formData.image_mode === "AI" && !isBuiltinVisualProvider(formData.provider) && (visualProvidersLoading || visualProvidersError || !visualProviders.some((provider) => provider.name === formData.provider))) {
      toast.error("Choose an available visual provider before generating.");
      return;
    }
    if (formData.message.trim() === "") {
      toast.error("You need to add a prompt!");
      return;
    }
    setIsLoading(true);

    const result = await generateVideo(formData);
    if (!result.ok) { setIsLoading(false); return; }
    const response = result.data;

    if (!response?.video?.id) {
      toast.error("Could not start the generation, please try again.");
      setIsLoading(false);
      return;
    }

    toast.info("Generation started, this usually takes a few minutes...");

    pollRef.current = pollVideo(response.video.id);
    const { outcome, video } = await pollRef.current.promise;

    setIsLoading(false);

    if (outcome !== "SETTLED") {
      toast.error(
        "Lost track of the generation. Check your videos page in a few minutes."
      );
      return;
    }

    if (video.status === "FAILED") {
      toast.error("The generation failed, please try again.");
      return;
    }

    setVideo_id(video.id);
    setOpen(true);
    toast.success("Video generated successfully!");
  };

  const voiceGroups = voices.reduce((groups, voice) => {
    const group = ttsProviderNames[voice.provider] || voice.provider || "Other voices";
    (groups[group] ||= []).push(voice);
    return groups;
  }, {});
  const selectedVoice = voices.find((voice) => String(voice.id) === String(formData.voice_id));
  const selectedVisualProvider = visualProviders.find((provider) => provider.name === formData.provider);
  const unavailableVisualProvider = formData.image_mode === "AI" && !isBuiltinVisualProvider(formData.provider) && (visualProvidersLoading || Boolean(visualProvidersError) || !selectedVisualProvider);
  const selectedAvatar = avatars.find((avatar) => String(avatar.id) === String(formData.avatar_selection));
  const examples = [
    ["Explainer", "Create a short explainer about how solar panels turn sunlight into electricity. Use simple language and everyday examples."],
    ["Travel story", "Create a relaxing travel video about a weekend in the Greek islands, with seaside villages, local food, and sunset views."],
    ["Product intro", "Introduce a reusable water bottle for people who love the outdoors. Focus on durability, everyday use, and reducing waste."],
  ];
  const field = (name, label, children, hint) => (
    <div>
      <label htmlFor={name} className="block text-sm font-medium text-gray-900 dark:text-gray-100">{label}</label>
      {children}
      {hint ? <p className="mt-2 text-xs leading-relaxed text-gray-500 dark:text-gray-400">{hint}</p> : null}
    </div>
  );
  const select = (name, children, disabled = false) => <select id={name} name={name} value={formData[name]} onChange={handleInputChange} disabled={disabled} className={inputClassName}>{children}</select>;

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:py-12">
      <ProceedModal open={open} setOpen={isOpenFunction} video_id={video_id} />
      <SaveTemplateModal showModal={savingTemplate} setShowModal={setSavingTemplate} settings={settingsForTemplate} onSaved={handleTemplateSaved} />
      <DeleteModal showModal={deletingTemplate} setShowModal={setDeletingTemplate} id={selectedTemplate?.id} name={selectedTemplate?.title} setItems={dropTemplate} deleteFunction={deleteTemplate} />
      <header className="mb-8">
        <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"><RiSparkling2Line aria-hidden="true" />VIDEO STUDIO</div>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl dark:text-white">Turn your idea into a video</h1>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-gray-500 dark:text-gray-400">Tell your story, choose its voice and visuals, then make it yours in the editor.</p>
      </header>

      <form onSubmit={handleGenerate} className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <fieldset disabled={isLoading} className="min-w-0 space-y-6">
          <section aria-labelledby="story-heading" className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-6 dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-5 flex items-center gap-3"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-50 text-sm font-semibold text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">1</span><h2 id="story-heading" className="text-lg font-semibold">Your story</h2></div>
            <div className="mb-5">
              <label htmlFor="template" className="block text-sm font-medium">Start from a template</label>
              <div className="flex items-center gap-2">
                {select("template", <><option value="">Start fresh</option>{templates.map((template) => <option key={template.id} value={template.id}>{template.title}</option>)}</>, optionsLoading)}
                {selectedTemplate ? <button type="button" aria-label="Delete template" title={`Delete ${selectedTemplate.title}`} onClick={() => setDeletingTemplate(true)} className="mt-2 rounded-xl border border-red-200 px-3 py-3 text-sm text-red-600 hover:bg-red-50 dark:border-red-900 dark:text-red-400">Delete</button> : null}
              </div>
            </div>
            {field("message", "Your prompt", <textarea id="message" name="message" rows={7} required value={formData.message} onChange={handleInputChange} className={`${inputClassName} resize-y leading-relaxed`} placeholder="What is your video about? Describe the story, tone, and details you want to include." />, "A clear topic and a few specific details help shape the script.")}
            <div className="mt-4 flex flex-wrap items-center gap-2"><span className="text-xs text-gray-400">Try an idea</span>{examples.map(([label, prompt]) => <button key={label} type="button" onClick={() => setFormData((previous) => ({ ...previous, message: prompt, template: "" }))} className="rounded-full border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-blue-900/30">{label}</button>)}</div>
          </section>

          <section aria-labelledby="look-heading" className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-6 dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-5 flex items-center gap-3"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-50 text-sm font-semibold text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">2</span><h2 id="look-heading" className="text-lg font-semibold">Voice and visuals</h2></div>
            <label className="mb-5 flex cursor-pointer items-center gap-3 rounded-xl bg-gray-50 p-3 dark:bg-gray-900/40"><input id="narration" name="narration" type="checkbox" checked={formData.narration} onChange={handleInputChange} className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" /><span><span className="block text-sm font-medium">Narration</span><span className="block text-xs text-gray-500 dark:text-gray-400">Add a voice-over to tell your story.</span></span></label>
            <div className="grid gap-5 sm:grid-cols-2">
              {field("avatar_selection", "Presenter", select("avatar_selection", <><option value="">No avatar</option>{avatars.map((avatar) => <option key={avatar.id} value={avatar.id}>{avatar.name}</option>)}</>, optionsLoading || !formData.narration), "An avatar uses its assigned voice.")}
              {!formData.avatar_selection ? field("voice_id", "Voice", select("voice_id", <><option value="">{optionsLoading ? "Loading voices..." : "Any available voice"}</option>{Object.entries(voiceGroups).map(([provider, group]) => <optgroup key={provider} label={provider}>{group.map((voice) => <option key={voice.id} value={voice.id}>{voice.name}</option>)}</optgroup>)}</>, optionsLoading || !formData.narration), !formData.narration ? "Narration is off. Your video will use clips only." : !optionsLoading && voices.length === 0 ? <span>No voices available. <Link to="/api-keys/" className="text-blue-600 underline dark:text-blue-400">Check your provider settings</Link>.</span> : "Choose a voice or let us pick from your available voices.") : <div className="rounded-xl bg-blue-50 p-4 text-sm text-blue-700 dark:bg-blue-900/20 dark:text-blue-300">{selectedAvatar?.name || "Your presenter"} will narrate using its assigned voice.</div>}
              {field("image_mode", "Visuals", select("image_mode", <><option value="WEB">Web images</option><option value="AI">AI-generated visuals</option></>))}
              {field("provider", "Visual provider", select("provider", formData.image_mode === "AI" ? <>
                <optgroup label="Built-in providers">{Object.entries(visualProviderNames).map(([name, label]) => <option key={name} value={name}>{label}</option>)}</optgroup>
                {["VIDEO", "IMAGE"].map((type) => visualProviders.some((provider) => provider.output_type === type) ? <optgroup key={type} label={type === "VIDEO" ? "Custom video providers" : "Custom image providers"}>{visualProviders.filter((provider) => provider.output_type === type).map((provider) => <option key={provider.id} value={provider.name}>{provider.name}</option>)}</optgroup> : null)}
                {!isBuiltinVisualProvider(formData.provider) && !visualProviders.some((provider) => provider.name === formData.provider) ? <option value={formData.provider} disabled>{formData.provider} ({visualProvidersLoading ? "loading" : "unavailable"})</option> : null}
              </> : <><option value="bing">Bing</option><option value="google">Google</option></>), formData.image_mode === "AI" ? <span>
                {visualProvidersLoading ? "Loading custom providers… " : visualProvidersError ? <><span className="text-amber-700 dark:text-amber-400">Custom providers could not be loaded. </span><button type="button" onClick={() => setProviderReload((previous) => previous + 1)} className="text-blue-600 underline dark:text-blue-400">Try again</button>{" · "}</> : null}
                {!visualProvidersLoading && !visualProvidersError && !isBuiltinVisualProvider(formData.provider) && !visualProviders.some((provider) => provider.name === formData.provider) ? <span className="text-amber-700 dark:text-amber-400">This saved provider is unavailable. Choose another provider. </span> : null}
                <Link to="/api-keys/?section=visual" className="text-blue-600 underline dark:text-blue-400">Manage custom images and videos</Link>
              </span> : null)}
            </div>
          </section>

          <section className="rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <button type="button" aria-expanded={settings} aria-controls="generation-settings" onClick={() => setSettings((previous) => !previous)} className="flex w-full items-center gap-3 rounded-2xl p-5 text-left focus:outline-none focus:ring-2 focus:ring-blue-500 sm:p-6"><RiSettings3Line aria-hidden="true" className="h-5 w-5 text-gray-400" /><span className="flex-1"><span className="block text-sm font-semibold">Advanced settings</span><span className="mt-1 block text-xs text-gray-500 dark:text-gray-400">Audience, tone, model, music, and subtitles</span></span><RiArrowDownSLine aria-hidden="true" className={`h-5 w-5 text-gray-400 transition-transform ${settings ? "rotate-180" : ""}`} /></button>
            <div id="generation-settings" hidden={!settings} className={`${settings ? "grid" : "hidden"} gap-5 border-t border-gray-100 p-5 sm:grid-cols-2 sm:p-6 dark:border-gray-700`}>
              {field("target_audience", "Target audience", <input id="target_audience" name="target_audience" value={formData.target_audience} onChange={handleInputChange} className={inputClassName} placeholder="e.g. curious beginners" />)}
              {field("genre", "Genre", <input id="genre" name="genre" value={formData.genre} onChange={handleInputChange} className={inputClassName} placeholder="e.g. documentary" />)}
              {field("gpt_model", "Script model", select("gpt_model", <><optgroup label="OpenAI">
                          <option value="gpt-5.4-mini">gpt-5.4-mini</option>
                          <option value="gpt-5.4">gpt-5.4</option>
                          <option value="gpt-5.4-nano">gpt-5.4-nano</option>
                          <option value="gpt-5.5">gpt-5.5</option>
                          <option value="gpt-5.6-luna">gpt-5.6-luna</option>
                          <option value="gpt-5.6-sol">gpt-5.6-sol</option>
                          <option value="gpt-5.6-terra">gpt-5.6-terra</option>
                          <option value="gpt-6-astra">gpt-6-astra</option>
                          <option value="gpt-5">gpt-5</option>
                          <option value="gpt-5-mini">gpt-5-mini</option>
                          <option value="gpt-5-nano">gpt-5-nano</option>
                          <option value="gpt-5.1">gpt-5.1</option>
                          <option value="gpt-5.2">gpt-5.2</option>
                          <option value="gpt-5.3-chat-latest">
                            gpt-5.3-chat-latest
                          </option>
                          <option value="gpt-4.1">gpt-4.1</option>
                          <option value="gpt-4.1-mini">gpt-4.1-mini</option>
                          <option value="gpt-4.1-nano">gpt-4.1-nano</option>
                          <option value="gpt-4o">gpt-4o</option>
                          <option value="gpt-4o-mini">gpt-4o-mini</option>
                          <option value="gpt-4-turbo">gpt-4-turbo</option>
                          <option value="gpt-4">gpt-4</option>
                          <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                          <option value="o3">o3</option>
                          <option value="o3-mini">o3-mini</option>
                          <option value="o4-mini">o4-mini</option>
                          <option value="o1">o1</option>
                        </optgroup>
                        <optgroup label="Anthropic">
                          <option value="claude-3-5-sonnet-20240620">
                            claude 3-5
                          </option>
                        </optgroup>
                        <optgroup label="Google">
                          <option value="gemini-1.5-pro">gemini-1.5-pro</option>
                          <option value="gemini-1.5-flash">
                            gemini-1.5-flash
                          </option>
                          <option value="gemini-1.0-pro">gemini-1.0-pro</option>
                        </optgroup>
                      </>))}
              {field("music", "Music URL", <input type="url" id="music" name="music" value={formData.music} onChange={handleInputChange} className={inputClassName} placeholder="https://www.youtube.com/watch?v=..." />, "Optional background music.")}
              <label className="flex items-center gap-3 text-sm"><input id="subtitles" name="subtitles" type="checkbox" checked={formData.subtitles && formData.narration} disabled={!formData.narration} onChange={handleInputChange} className="h-4 w-4 rounded border-gray-300 text-blue-600" />Include subtitles</label>
            </div>
          </section>
        </fieldset>

        <aside aria-labelledby="summary-heading" className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm lg:sticky lg:top-6 dark:border-gray-700 dark:bg-gray-800">
          <div className="mb-5 rounded-xl bg-gradient-to-br from-blue-50 to-indigo-100 p-5 dark:from-blue-950 dark:to-indigo-950"><RiSparkling2Line aria-hidden="true" className="mb-3 h-7 w-7 text-blue-600 dark:text-blue-300" /><h2 id="summary-heading" className="text-lg font-semibold">Your video</h2><p className="mt-1 text-sm leading-relaxed text-gray-500 dark:text-gray-400">A first draft you can edit and refine.</p></div>
          <dl className="space-y-4 text-sm">
            <div className="flex items-start gap-3"><RiVolumeUpLine aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-gray-400" /><div><dt className="text-xs text-gray-500 dark:text-gray-400">Narration</dt><dd className="mt-1 font-medium">{!formData.narration ? "Clips only" : selectedAvatar ? selectedAvatar.name : selectedVoice ? `${selectedVoice.name} · ${ttsProviderNames[selectedVoice.provider] || selectedVoice.provider}` : "Any available voice"}</dd></div></div>
            <div className="flex items-start gap-3"><RiImageLine aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-gray-400" /><div><dt className="text-xs text-gray-500 dark:text-gray-400">Visuals</dt><dd className="mt-1 font-medium">{formData.image_mode === "AI" ? (isBuiltinVisualProvider(formData.provider) ? visualProviderNames[formData.provider] : `${formData.provider} · ${selectedVisualProvider?.output_type === "VIDEO" ? "Video clips" : "Images"}`) : "Web images"}</dd></div></div>
          </dl>
          <div className="mt-6 border-t border-gray-100 pt-5 dark:border-gray-700">
            <button type="submit" disabled={isLoading || !formData.message.trim() || optionsLoading || unavailableVisualProvider} className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-300 disabled:cursor-not-allowed disabled:opacity-50">{isLoading ? <><span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />Generating...</> : <>Generate video<RiArrowRightLine aria-hidden="true" className="h-4 w-4" /></>}</button>
            <button type="button" disabled={isLoading} onClick={() => setSavingTemplate(true)} className="mt-3 w-full rounded-xl border border-gray-200 px-4 py-3 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700">Save as template</button>
            <p role={isLoading ? "status" : undefined} className="mt-4 text-center text-xs leading-relaxed text-gray-500 dark:text-gray-400">{isLoading ? "We’re creating your script, narration, and scenes. This usually takes a few minutes." : "Generate first, then review your scenes before rendering."}</p>
          </div>
        </aside>
      </form>
    </main>
  );
};

export default Home;
