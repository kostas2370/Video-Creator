import React, { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "react-toastify";
import {
  getCustomVisualProviders,
  createCustomVisualProvider,
  updateCustomVisualProvider,
  deleteCustomVisualProvider,
} from "../api/apiService";

const primaryButton = "rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-300 disabled:opacity-60";
const secondaryButton = "rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium hover:bg-gray-100 focus:outline-none focus:ring-4 focus:ring-gray-200 disabled:opacity-60 dark:border-gray-600 dark:hover:bg-gray-700";
const inputClass = "mt-1 block w-full rounded-lg border border-gray-300 bg-gray-50 p-2.5 text-sm text-gray-900 focus:border-blue-600 focus:ring-blue-600 disabled:opacity-60 dark:border-gray-600 dark:bg-gray-700 dark:text-white";
const authNames = { bearer: "Bearer token", header: "Custom header", basic: "Basic authentication", none: "No authentication" };
const emptyProvider = {
  name: "", endpoint_url: "", auth_type: "bearer", auth_header_name: "",
  output_type: "VIDEO", prompt_field_name: "prompt",
};

export function CustomVisualProviders() {
  const [providers, setProviders] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [editor, setEditor] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    const result = await getCustomVisualProviders();
    if (result.ok) {
      setProviders(Array.isArray(result.data) ? result.data : result.data?.results ?? []);
      setLoadError("");
    } else {
      setLoadError(result.message);
    }
    setIsLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const saved = (provider) => {
    setProviders((previous) => editor.id
      ? previous.map((item) => item.id === provider.id ? provider : item)
      : [...previous, provider]);
    setEditor(null);
  };

  const remove = async (provider) => {
    setBusyId(provider.id);
    const result = await deleteCustomVisualProvider(provider.id);
    setBusyId(null);
    if (!result.ok) {
      toast.error(`Provider could not be deleted: ${result.message}`);
      return;
    }
    setProviders((previous) => previous.filter((item) => item.id !== provider.id));
    setDeletingId(null);
    toast.success("Custom visual provider deleted");
  };

  return (
    <section aria-labelledby="custom-visual-heading" className="mx-auto max-w-3xl px-4 pb-6 md:px-6">
      <div className="rounded-lg bg-white p-4 shadow dark:border dark:border-gray-700 dark:bg-gray-800">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 id="custom-visual-heading" className="text-lg font-semibold">Custom image and video providers</h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Connect an image or video service, then select it under AI-generated visuals.
            </p>
          </div>
          <button type="button" className={primaryButton} disabled={isLoading || Boolean(editor) || busyId !== null || Boolean(loadError)} onClick={() => { setDeletingId(null); setEditor({}); }}>
            Add provider
          </button>
        </div>

        {isLoading ? <p role="status" className="mt-4 text-sm">Loading custom providers...</p> : loadError ? (
          <div role="alert" className="mt-4">
            <p className="mb-2 text-sm text-red-600 dark:text-red-400">Providers could not be loaded: {loadError}</p>
            <button type="button" className={secondaryButton} onClick={load}>Try again</button>
          </div>
        ) : providers.length === 0 && !editor ? (
          <div className="mt-5 rounded-lg border border-dashed border-gray-300 bg-gray-50 p-5 dark:border-gray-600 dark:bg-gray-900/30">
            <p className="font-medium">No custom providers yet</p>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Connect a visual service in three steps:</p>
            <ol className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
              {["Choose images or videos", "Add the generation URL", "Set request options"].map((step, index) => <li key={step} className="flex items-center gap-2"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-blue-700 dark:bg-blue-900 dark:text-blue-200">{index + 1}</span>{step}</li>)}
            </ol>
          </div>
        ) : null}

        {editor && !editor.id ? <ProviderForm key={editor.id ?? "new"} provider={editor} onSaved={saved} onCancel={() => setEditor(null)} /> : null}

        <ul className="mt-4 space-y-3">
          {providers.map((provider) => (
            <li key={provider.id} className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
              {editor?.id === provider.id ? <ProviderForm provider={editor} onSaved={saved} onCancel={() => setEditor(null)} /> : <>
              <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-semibold break-words">{provider.name}</h3>
              <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">{provider.output_type === "VIDEO" ? "Video" : "Image"}</span>
              </div>
              <p className="mt-1 break-all text-sm text-gray-500 dark:text-gray-400">{provider.endpoint_url}</p>
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                {authNames[provider.auth_type]}{provider.auth_type !== "none" ? ` · ${provider.api_key ? "Credential saved" : "No credential saved"}` : ""}
              </p>
              {deletingId === provider.id ? (
                <div className="mt-3" role="group" aria-label={`Delete ${provider.name}`}>
                  <p className="mb-3 text-sm">Delete this provider? Existing generated media will remain. New generation using this provider will no longer work.</p>
                  <div className="flex flex-wrap gap-2">
                    <button type="button" disabled={busyId !== null} className={secondaryButton} onClick={() => setDeletingId(null)}>Cancel deletion</button>
                    <button type="button" disabled={busyId !== null} className={`${primaryButton} bg-red-600 hover:bg-red-700`} onClick={() => remove(provider)}>
                      {busyId === provider.id ? "Deleting..." : "Delete provider"}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" className={secondaryButton} disabled={Boolean(editor) || busyId !== null} onClick={() => { setDeletingId(null); setEditor(provider); }}>Edit</button>
                  <button type="button" className={`${secondaryButton} text-red-600 dark:text-red-400`} disabled={Boolean(editor) || busyId !== null} onClick={() => setDeletingId(provider.id)}>Delete</button>
                </div>
              )}
              </>}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function ProviderForm({ provider, onSaved, onCancel }) {
  const isEditing = Boolean(provider.id);
  const [draft, setDraft] = useState(() => Object.fromEntries(Object.entries(emptyProvider).map(([name, value]) => [name, provider[name] ?? value])));
  const [credential, setCredential] = useState("");
  const initialParameters = JSON.stringify(provider.extra_parameters ?? {}, null, 2);
  const [parameters, setParameters] = useState(initialParameters);
  const [clearCredential, setClearCredential] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errors, setErrors] = useState({});
  const [errorMessage, setErrorMessage] = useState("");
  const [showCredential, setShowCredential] = useState(false);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const formRef = useRef(null);
  const hasChanges = Object.entries(draft).some(([name, value]) => value !== (provider[name] ?? emptyProvider[name])) || parameters !== initialParameters || Boolean(credential) || clearCredential;

  useEffect(() => {
    formRef.current?.querySelector("input:not(:disabled)")?.focus();
  }, []);

  const cancel = () => {
    if (hasChanges) setConfirmDiscard(true);
    else onCancel();
  };

  const change = (name, value) => {
    setDraft((previous) => ({ ...previous, [name]: value }));
    setErrors((previous) => ({ ...previous, [name]: undefined }));
  };

  const submit = async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(Object.entries(draft).map(([name, value]) => [name, value.trim()]));
    try {
      data.extra_parameters = JSON.parse(parameters.trim() || "{}");
      if (data.extra_parameters === null || Array.isArray(data.extra_parameters) || typeof data.extra_parameters !== "object") throw new Error("Expected an object");
    } catch {
      setErrors({ extra_parameters: "Enter a valid JSON object, for example {\"model\": \"my-model\", \"seed\": 42}." });
      return;
    }
    if (!isEditing && ["openai", "stable_diffusion", "midjourney", "dall-e", "sora", "stable-diffusion", "bing", "google"].includes(data.name.toLowerCase())) {
      setErrors({ name: "Choose a name different from the built-in providers." });
      return;
    }
    if (isEditing) delete data.name;
    if (clearCredential) data.api_key = "";
    else if (credential.trim()) data.api_key = credential.trim();
    setIsSaving(true);
    setErrorMessage("");
    const result = isEditing ? await updateCustomVisualProvider(provider.id, data) : await createCustomVisualProvider(data);
    setIsSaving(false);
    if (!result.ok) {
      setErrors(typeof result.errors === "object" && result.errors !== null ? result.errors : {});
      setErrorMessage(result.message);
      return;
    }
    toast.success(isEditing ? "Custom visual provider saved" : "Custom visual provider added");
    onSaved(result.data);
  };

  const field = (name, label, options = {}) => (
    <div>
      <label htmlFor={`custom-visual-${name}`} className="text-sm font-medium">{label}</label>
      <input id={`custom-visual-${name}`} name={name} value={draft[name]} onChange={(event) => change(name, event.target.value)}
        className={inputClass} aria-invalid={Boolean(errors[name])} aria-describedby={errors[name] ? `custom-visual-${name}-error` : undefined} {...options} />
      {errors[name] ? <p id={`custom-visual-${name}-error`} className="mt-1 text-sm text-red-600 dark:text-red-400">{[].concat(errors[name]).join(" ")}</p> : null}
    </div>
  );

  return (
    <form ref={formRef} onSubmit={submit} aria-label={isEditing ? `Edit ${provider.name}` : "Add custom visual provider"} className="mt-4 space-y-5">
      <h3 className="font-semibold">{isEditing ? `Edit ${provider.name}` : "Add custom visual provider"}</h3>
      <p className="text-sm text-gray-500 dark:text-gray-400">{isEditing ? "Update the connection below. Your saved credential stays in place unless you replace or clear it." : "Choose the output type and enter your service’s generation URL."}</p>
      <fieldset disabled={isSaving} className="space-y-5">
        <div className="space-y-4">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">1. Connection</h4>
        {field("name", "Provider name", { required: true, maxLength: 50, disabled: isEditing, placeholder: "My video service" })}
        {isEditing ? <p className="text-xs text-gray-500 dark:text-gray-400">To use a different provider name, add a new provider.</p> : null}
        <div>
          <label htmlFor="custom-visual-output_type" className="text-sm font-medium">Output type</label>
          <select id="custom-visual-output_type" value={draft.output_type} onChange={(event) => change("output_type", event.target.value)} className={inputClass}>
            <option value="VIDEO">Video clips</option><option value="IMAGE">Still images</option>
          </select>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{draft.output_type === "VIDEO" ? "Your service must return a completed video or its URL. Services that return only a job ID are not supported yet." : "Your service must return image bytes or an image URL."}</p>
        </div>
        {field("endpoint_url", "Generation endpoint URL", { type: "url", required: true, maxLength: 500, placeholder: "https://example.com/generate" })}
        </div>
        <div className="space-y-4 border-t border-gray-200 pt-5 dark:border-gray-700">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">2. Authentication</h4>
        <div>
          <label htmlFor="custom-visual-auth_type" className="text-sm font-medium">Authentication</label>
          <select id="custom-visual-auth_type" value={draft.auth_type} onChange={(event) => change("auth_type", event.target.value)} className={inputClass}>
            {Object.entries(authNames).map(([value, name]) => <option key={value} value={value}>{name}</option>)}
          </select>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400">{draft.auth_type === "bearer" ? "Use the token supplied by your visual service." : draft.auth_type === "header" ? "Enter the header name and key specified by your visual service." : draft.auth_type === "basic" ? "Enter your username and password separated by a colon." : "No credential will be sent with generation requests."}</p>
        {draft.auth_type === "header" ? field("auth_header_name", "Authentication header name", { required: true, maxLength: 100, placeholder: "x-api-key" }) : null}
        {draft.auth_type !== "none" ? (
          <div>
            <label htmlFor="custom-visual-api_key" className="text-sm font-medium">{draft.auth_type === "basic" ? "Credentials (username:password)" : "API key or token"}</label>
            <div className="flex items-center gap-2">
            <input id="custom-visual-api_key" type={showCredential ? "text" : "password"} autoComplete="new-password" value={credential} disabled={clearCredential}
              onChange={(event) => setCredential(event.target.value)} className={inputClass} placeholder={provider.api_key ? "Saved credential — enter a replacement" : "Enter your credential"} />
            <button type="button" disabled={clearCredential} className={secondaryButton} aria-label={showCredential ? "Hide credential" : "Show credential"} aria-pressed={showCredential} onClick={() => setShowCredential((previous) => !previous)}>{showCredential ? "Hide" : "Show"}</button>
            </div>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{isEditing ? "Leave blank to keep the saved credential." : "Your credential is stored encrypted."}</p>
            {errors.api_key ? <p className="mt-1 text-sm text-red-600 dark:text-red-400">{[].concat(errors.api_key).join(" ")}</p> : null}
          </div>
        ) : null}
        {isEditing && provider.api_key ? (
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={clearCredential} onChange={(event) => setClearCredential(event.target.checked)} />
            Clear saved credential on save
          </label>
        ) : null}
        </div>
        <details className="rounded-lg bg-gray-50 p-3 dark:bg-gray-900/40">
          <summary className="cursor-pointer text-sm font-medium">Advanced: request settings</summary>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Keep these defaults unless your service expects different field names.</p>
          <div className="mt-3">{field("prompt_field_name", "Prompt field name", { required: true, maxLength: 50 })}</div>
          <div className="mt-4">
            <label htmlFor="custom-visual-extra_parameters" className="text-sm font-medium">Extra parameters (JSON)</label>
            <textarea id="custom-visual-extra_parameters" value={parameters} rows={5} spellCheck={false}
              onChange={(event) => { setParameters(event.target.value); setErrors((previous) => ({ ...previous, extra_parameters: undefined })); }}
              className={`${inputClass} font-mono`} aria-invalid={Boolean(errors.extra_parameters)} aria-describedby="custom-visual-extra_parameters-help custom-visual-extra_parameters-error" />
            <p id="custom-visual-extra_parameters-help" className="mt-1 text-xs text-gray-500 dark:text-gray-400">Add options such as model, seed, or duration. The prompt field takes precedence. Use {"{}"} to clear saved parameters.</p>
            <p id="custom-visual-extra_parameters-error" className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.extra_parameters ? [].concat(errors.extra_parameters).join(" ") : null}</p>
          </div>
        </details>
        {errorMessage ? <p role="alert" className="text-sm text-red-600 dark:text-red-400">Provider could not be saved: {errorMessage}</p> : null}
        {confirmDiscard ? <div role="group" aria-label="Discard unsaved changes" className="rounded-lg bg-amber-50 p-3 dark:bg-amber-900/20">
          <p className="mb-3 text-sm">Discard your unsaved changes?</p>
          <div className="flex flex-wrap gap-2"><button type="button" className={secondaryButton} onClick={() => setConfirmDiscard(false)}>Keep editing</button><button type="button" className={secondaryButton} onClick={onCancel}>Discard changes</button></div>
        </div> : null}
        <div className="flex flex-wrap justify-end gap-2 border-t border-gray-200 pt-4 dark:border-gray-700">
          <button type="button" className={secondaryButton} onClick={cancel}>Cancel</button>
          <button type="submit" disabled={isEditing && !hasChanges} className={primaryButton}>{isSaving ? "Saving..." : isEditing ? "Save provider" : "Add provider"}</button>
        </div>
      </fieldset>
    </form>
  );
}
