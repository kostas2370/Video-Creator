import React, { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "react-toastify";
import {
  getCustomTtsProviders,
  createCustomTtsProvider,
  updateCustomTtsProvider,
  deleteCustomTtsProvider,
  refreshCustomTtsProviderVoices,
} from "../api/apiService";

const primaryButton = "rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-300 disabled:opacity-60";
const secondaryButton = "rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium hover:bg-gray-100 focus:outline-none focus:ring-4 focus:ring-gray-200 disabled:opacity-60 dark:border-gray-600 dark:hover:bg-gray-700";
const inputClass = "mt-1 block w-full rounded-lg border border-gray-300 bg-gray-50 p-2.5 text-sm text-gray-900 focus:border-blue-600 focus:ring-blue-600 disabled:opacity-60 dark:border-gray-600 dark:bg-gray-700 dark:text-white";
const authNames = { bearer: "Bearer token", header: "Custom header", basic: "Basic authentication", none: "No authentication" };
const emptyProvider = {
  name: "", endpoint_url: "", auth_type: "bearer", auth_header_name: "",
  voices_url: "", text_field_name: "text", voice_field_name: "voice_id",
};

export function CustomTtsProviders({ useServiceKeys = false, onUseOwnKeys, isSwitching = false }) {
  const [providers, setProviders] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [editor, setEditor] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [refreshMessages, setRefreshMessages] = useState({});

  const load = useCallback(async () => {
    setIsLoading(true);
    const result = await getCustomTtsProviders();
    if (result.ok) {
      setProviders(Array.isArray(result.data) ? result.data : result.data.results ?? []);
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
    const result = await deleteCustomTtsProvider(provider.id);
    setBusyId(null);
    if (!result.ok) {
      toast.error(`Provider could not be deleted: ${result.message}`);
      return;
    }
    setProviders((previous) => previous.filter((item) => item.id !== provider.id));
    setDeletingId(null);
    toast.success("Custom voice provider deleted");
  };

  const refresh = async (provider) => {
    setBusyId(provider.id);
    const result = await refreshCustomTtsProviderVoices(provider.id);
    setBusyId(null);
    if (result.ok) {
      setRefreshMessages((previous) => ({ ...previous, [provider.id]: "Voice import queued. New voices will appear after it finishes." }));
      toast.success("Voice refresh queued. Voices will appear when the import finishes.");
    } else {
      toast.error(`Voice refresh could not be queued: ${result.message}`);
    }
  };

  return (
    <section aria-labelledby="custom-tts-heading" className="mx-auto max-w-3xl px-4 pb-6 md:px-6">
      <div className="rounded-lg bg-white p-4 shadow dark:border dark:border-gray-700 dark:bg-gray-800">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 id="custom-tts-heading" className="text-lg font-semibold">Custom voice providers</h2>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Connect your own text-to-speech service. Its voices are available when “Use my own keys” is on.
            </p>
          </div>
          <button type="button" className={primaryButton} disabled={isLoading || Boolean(editor) || busyId !== null || Boolean(loadError)} onClick={() => { setDeletingId(null); setEditor({}); }}>
            Add provider
          </button>
        </div>

        {useServiceKeys && !isLoading ? (
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-blue-100 bg-blue-50 p-3 dark:border-blue-900 dark:bg-blue-950">
            <p className="text-sm text-blue-900 dark:text-blue-200">Your custom voices are hidden while service keys are selected.</p>
            {onUseOwnKeys ? <button type="button" className={secondaryButton} disabled={isSwitching} onClick={onUseOwnKeys}>{isSwitching ? "Switching..." : "Use my own keys"}</button> : null}
          </div>
        ) : null}

        {isLoading ? <p role="status" className="mt-4 text-sm">Loading custom providers...</p> : loadError ? (
          <div role="alert" className="mt-4">
            <p className="mb-2 text-sm text-red-600 dark:text-red-400">Providers could not be loaded: {loadError}</p>
            <button type="button" className={secondaryButton} onClick={load}>Try again</button>
          </div>
        ) : providers.length === 0 && !editor ? (
          <div className="mt-5 rounded-lg border border-dashed border-gray-300 bg-gray-50 p-5 dark:border-gray-600 dark:bg-gray-900/30">
            <p className="font-medium">No custom providers yet</p>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Connect a voice service in three steps:</p>
            <ol className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
              {["Add the speech URL", "Choose authentication", "Import your voices"].map((step, index) => <li key={step} className="flex items-center gap-2"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-blue-700 dark:bg-blue-900 dark:text-blue-200">{index + 1}</span>{step}</li>)}
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
              <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${provider.voices_url ? "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300" : "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"}`}>{provider.voices_url ? "Voices URL configured" : "Needs voices URL"}</span>
              </div>
              <p className="mt-1 break-all text-sm text-gray-500 dark:text-gray-400">{provider.endpoint_url}</p>
              <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                {authNames[provider.auth_type]}{provider.auth_type !== "none" ? ` · ${provider.api_key ? "Credential saved" : "No credential saved"}` : ""}
              </p>
              {refreshMessages[provider.id] ? <p role="status" className="mt-3 rounded-lg bg-blue-50 p-3 text-sm text-blue-800 dark:bg-blue-900/30 dark:text-blue-200">{refreshMessages[provider.id]}</p> : null}
              {!provider.voices_url ? <p className="mt-2 text-sm text-amber-700 dark:text-amber-400">Add a voices URL to import voices for generation.</p> : null}
              {deletingId === provider.id ? (
                <div className="mt-3" role="group" aria-label={`Delete ${provider.name}`}>
                  <p className="mb-3 text-sm">Delete this provider and its imported voices?</p>
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
                  <button type="button" className={secondaryButton} disabled={!provider.voices_url || busyId !== null || Boolean(editor)} onClick={() => refresh(provider)}>
                    {busyId === provider.id ? "Queueing..." : "Refresh voices"}
                  </button>
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
  const [clearCredential, setClearCredential] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errors, setErrors] = useState({});
  const [errorMessage, setErrorMessage] = useState("");
  const [showCredential, setShowCredential] = useState(false);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const formRef = useRef(null);
  const hasChanges = Object.entries(draft).some(([name, value]) => value !== (provider[name] ?? emptyProvider[name])) || Boolean(credential) || clearCredential;

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
    if (!isEditing && ["OPENAI", "ELEVENLABS", "SIXTYDB"].includes(data.name)) {
      setErrors({ name: "Choose a name different from the built-in providers." });
      return;
    }
    if (isEditing) delete data.name;
    if (clearCredential) data.api_key = "";
    else if (credential.trim()) data.api_key = credential.trim();
    setIsSaving(true);
    setErrorMessage("");
    const result = isEditing ? await updateCustomTtsProvider(provider.id, data) : await createCustomTtsProvider(data);
    setIsSaving(false);
    if (!result.ok) {
      setErrors(typeof result.errors === "object" && result.errors !== null ? result.errors : {});
      setErrorMessage(result.message);
      return;
    }
    toast.success(isEditing ? "Custom voice provider saved" : "Custom voice provider added");
    onSaved(result.data);
  };

  const field = (name, label, options = {}) => (
    <div>
      <label htmlFor={`custom-tts-${name}`} className="text-sm font-medium">{label}</label>
      <input id={`custom-tts-${name}`} name={name} value={draft[name]} onChange={(event) => change(name, event.target.value)}
        className={inputClass} aria-invalid={Boolean(errors[name])} aria-describedby={errors[name] ? `custom-tts-${name}-error` : undefined} {...options} />
      {errors[name] ? <p id={`custom-tts-${name}-error`} className="mt-1 text-sm text-red-600 dark:text-red-400">{[].concat(errors[name]).join(" ")}</p> : null}
    </div>
  );

  return (
    <form ref={formRef} onSubmit={submit} aria-label={isEditing ? `Edit ${provider.name}` : "Add custom voice provider"} className="mt-4 space-y-5">
      <h3 className="font-semibold">{isEditing ? `Edit ${provider.name}` : "Add custom voice provider"}</h3>
      <p className="text-sm text-gray-500 dark:text-gray-400">{isEditing ? "Update the connection below. Your saved credential stays in place unless you replace or clear it." : "Have your service’s speech URL and credentials ready. You can add a voices URL now or later."}</p>
      <fieldset disabled={isSaving} className="space-y-5">
        <div className="space-y-4">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">1. Connection</h4>
        {field("name", "Provider name", { required: true, maxLength: 50, disabled: isEditing, placeholder: "My voice service" })}
        {isEditing ? <p className="text-xs text-gray-500 dark:text-gray-400">To use a different provider name, add a new provider.</p> : null}
        {field("endpoint_url", "Speech endpoint URL", { type: "url", required: true, maxLength: 200, placeholder: "https://example.com/synthesize" })}
        </div>
        <div className="space-y-4 border-t border-gray-200 pt-5 dark:border-gray-700">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">2. Authentication</h4>
        <div>
          <label htmlFor="custom-tts-auth_type" className="text-sm font-medium">Authentication</label>
          <select id="custom-tts-auth_type" value={draft.auth_type} onChange={(event) => change("auth_type", event.target.value)} className={inputClass}>
            {Object.entries(authNames).map(([value, name]) => <option key={value} value={value}>{name}</option>)}
          </select>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400">{draft.auth_type === "bearer" ? "Use the token supplied by your voice service." : draft.auth_type === "header" ? "Enter the header name and key specified by your voice service." : draft.auth_type === "basic" ? "Enter your username and password separated by a colon." : "No credential will be sent with speech requests."}</p>
        {draft.auth_type === "header" ? field("auth_header_name", "Authentication header name", { required: true, maxLength: 100, placeholder: "x-api-key" }) : null}
        {draft.auth_type !== "none" ? (
          <div>
            <label htmlFor="custom-tts-api_key" className="text-sm font-medium">{draft.auth_type === "basic" ? "Credentials (username:password)" : "API key or token"}</label>
            <div className="flex items-center gap-2">
            <input id="custom-tts-api_key" type={showCredential ? "text" : "password"} autoComplete="new-password" value={credential} disabled={clearCredential}
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
        <div className="space-y-3 border-t border-gray-200 pt-5 dark:border-gray-700">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">3. Voices</h4>
        {field("voices_url", "Voices URL (optional)", { type: "url", maxLength: 500, placeholder: "https://example.com/voices" })}
        <p className="text-xs text-gray-500 dark:text-gray-400">Provide a URL that lists voices without authentication to make this provider available in the voice selector.</p>
        </div>
        <details className="rounded-lg bg-gray-50 p-3 dark:bg-gray-900/40">
          <summary className="cursor-pointer text-sm font-medium">Advanced: request field names</summary>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Keep these defaults unless your service expects different field names.</p>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            {field("text_field_name", "Text field name", { required: true, maxLength: 50 })}
            {field("voice_field_name", "Voice ID field name", { required: true, maxLength: 50 })}
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
