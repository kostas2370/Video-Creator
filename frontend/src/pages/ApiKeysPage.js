import React, { useEffect, useState } from "react";
import { toast } from "react-toastify";
import { RiEyeLine, RiEyeOffLine } from "react-icons/ri";

import { getApiKeys, updateApiKeys, deleteApiKeys } from "../api/apiService";
import { ClearApiKeysModal } from "../components/ClearApiKeysModal";
import { useAxiosPrivate } from "../hooks/useAxiosPrivate";

// The field names are the serializer's, so each input patches straight through. The
// labels are the ones the Provider choices use on the backend — worth keeping in step.
const KEY_GROUPS = [
  {
    title: "Text and voice",
    description: "Script writing and voice-over.",
    fields: [
      { name: "openai_key", label: "OpenAI" },
      { name: "anthropic_key", label: "Anthropic" },
      { name: "gemini_key", label: "Google Gemini" },
      { name: "elevenlabs_key", label: "ElevenLabs" },
      { name: "sixtydb_key", label: "60dB" },
    ],
  },
  {
    title: "Images",
    description: "The pictures behind each scene.",
    fields: [
      { name: "diffusion_key", label: "Stable Diffusion" },
      { name: "midjourney_key", label: "Midjourney" },
      { name: "google_search_key", label: "Google Custom Search" },
      {
        name: "google_search_engine_id",
        label: "Google Search engine id",
        hint: "The cx of your custom search engine, not a key.",
      },
    ],
  },
  {
    title: "Twitch",
    description: "Looking up the clips a Twitch video is built from.",
    fields: [
      { name: "twitch_client_id", label: "Twitch client id" },
      {
        name: "twitch_client_secret",
        label: "Twitch client secret",
        hint: "Both the id and the secret are needed.",
      },
    ],
  },
];

const KEY_FIELDS = KEY_GROUPS.flatMap((group) =>
  group.fields.map((field) => field.name)
);

const EMPTY_KEYS = Object.fromEntries(KEY_FIELDS.map((name) => [name, ""]));

// What ApiKeys.mask on the backend makes of a key, which is all this page ever sees.
const MASK_EXAMPLE = "sk-••••••••ijkl";

export const ApiKeys = () => {
  // What the server holds, masked (`sk-••••••••ijkl`) — never the key itself, so an
  // input can be pre-filled with it. It goes in the placeholder instead.
  const [saved, setSaved] = useState(EMPTY_KEYS);
  // Only the fields the user has actually typed into. Anything absent is left untouched
  // by the PATCH, which is what keeps saving one key from wiping the other ten.
  const [drafts, setDrafts] = useState({});
  const [revealed, setRevealed] = useState({});
  const [useServiceKeys, setUseServiceKeys] = useState(true);
  const [updatedAt, setUpdatedAt] = useState(null);

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [showClearModal, setShowClearModal] = useState(false);

  useAxiosPrivate();

  const applyResponse = (data) => {
    setSaved(
      Object.fromEntries(KEY_FIELDS.map((name) => [name, data[name] ?? ""]))
    );
    setUseServiceKeys(Boolean(data.use_service_api_keys));
    setUpdatedAt(data.updated_at ?? null);
  };

  useEffect(() => {
    let isCurrent = true;

    getApiKeys().then((result) => {
      if (!isCurrent) return;
      if (result.ok) {
        applyResponse(result.data);
      } else {
        toast.error(`Your keys could not be loaded — ${result.message}`);
      }
      setIsLoading(false);
    });

    return () => {
      isCurrent = false;
    };
  }, []);

  // A field only counts as changed when it says something new: emptying an input that
  // was already empty is not a request to clear anything.
  const changed = Object.entries(drafts).filter(([name, value]) =>
    value.trim() === "" ? Boolean(saved[name]) : true
  );
  const isDirty = changed.length > 0;

  const handleChange = (name, value) =>
    setDrafts((previous) => ({ ...previous, [name]: value }));

  const handleClearField = (name) => {
    setDrafts((previous) => ({ ...previous, [name]: "" }));
    setRevealed((previous) => ({ ...previous, [name]: false }));
  };

  const handleDiscard = () => {
    setDrafts({});
    setRevealed({});
  };

  const handleSave = async (event) => {
    event.preventDefault();

    if (!isDirty) return;

    setIsSaving(true);
    const result = await updateApiKeys(
      Object.fromEntries(changed.map(([name, value]) => [name, value.trim()]))
    );
    setIsSaving(false);

    if (!result.ok) {
      toast.error(`Nothing was saved — ${result.message}`);
      return;
    }

    applyResponse(result.data);
    setDrafts({});
    setRevealed({});
    toast.success(
      changed.length === 1 ? "Key saved" : `${changed.length} keys saved`
    );
  };

  const handleModeChange = async (nextUseServiceKeys) => {
    // Optimistic: the switch has to move under the cursor. It is put back if the
    // request is refused, so the page never claims a mode the backend did not take.
    const previous = useServiceKeys;
    setUseServiceKeys(nextUseServiceKeys);
    setIsSwitching(true);

    const result = await updateApiKeys({
      use_service_api_keys: nextUseServiceKeys,
    });
    setIsSwitching(false);

    if (!result.ok) {
      setUseServiceKeys(previous);
      toast.error(`The switch did not take — ${result.message}`);
      return;
    }

    applyResponse(result.data);
    toast.success(
      nextUseServiceKeys
        ? "Generation now spends the service keys"
        : "Generation now spends your own keys"
    );
  };

  const handleClearAll = async () => {
    setIsClearing(true);
    const result = await deleteApiKeys();
    setIsClearing(false);

    if (!result.ok) {
      toast.error(`Your keys are still there — ${result.message}`);
      return;
    }

    // The row is gone; the next GET recreates an empty one. Mirroring that here saves
    // a round trip and keeps the placeholders from still showing masked keys.
    setSaved(EMPTY_KEYS);
    setDrafts({});
    setRevealed({});
    setUpdatedAt(null);
    setShowClearModal(false);
    toast.success("Every key was removed");
  };

  if (isLoading) {
    return (
      <div className="p-4 md:p-6">
        <p className="text-gray-500 dark:text-gray-400">Loading your keys...</p>
      </div>
    );
  }

  return (
    <>
      <ClearApiKeysModal
        showModal={showClearModal}
        setShowModal={setShowClearModal}
        onConfirm={handleClearAll}
        isClearing={isClearing}
      />

      <form className="p-4 md:p-6 max-w-3xl mx-auto" onSubmit={handleSave}>
        <div className="mb-6">
          <h1 className="text-2xl font-bold">API keys</h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Keys are stored encrypted and are never sent back to this page — an
            already saved one only ever shows as {MASK_EXAMPLE}.
          </p>
        </div>

        <div className="mb-6 bg-white dark:bg-gray-800 dark:border dark:border-gray-700 rounded-lg shadow p-4">
          <div className="flex flex-wrap gap-4 items-start justify-between">
            <div>
              <h2 className="text-lg font-semibold">Which keys get spent</h2>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                {useServiceKeys
                  ? "Generation spends the service keys. Anything below is kept, but unused."
                  : "Generation spends the keys below. A provider left empty has no key to spend, and the steps that need it will fail."}
              </p>
            </div>

            <label className="inline-flex items-center cursor-pointer shrink-0">
              <input
                type="checkbox"
                className="sr-only peer"
                checked={!useServiceKeys}
                disabled={isSwitching}
                onChange={(e) => handleModeChange(!e.target.checked)}
              />
              <div className="relative w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600 peer-disabled:opacity-60"></div>
              <span className="ms-3 text-sm font-medium">Use my own keys</span>
            </label>
          </div>
        </div>

        {KEY_GROUPS.map((group) => (
          <div
            key={group.title}
            className="mb-6 bg-white dark:bg-gray-800 dark:border dark:border-gray-700 rounded-lg shadow p-4"
          >
            <h2 className="text-lg font-semibold">{group.title}</h2>
            <p className="mb-4 text-sm text-gray-600 dark:text-gray-400">
              {group.description}
            </p>

            <div className="space-y-4">
              {group.fields.map((field) => (
                <KeyField
                  key={field.name}
                  field={field}
                  saved={saved[field.name]}
                  draft={drafts[field.name]}
                  isRevealed={Boolean(revealed[field.name])}
                  onChange={(value) => handleChange(field.name, value)}
                  onClear={() => handleClearField(field.name)}
                  onToggleReveal={() =>
                    setRevealed((previous) => ({
                      ...previous,
                      [field.name]: !previous[field.name],
                    }))
                  }
                />
              ))}
            </div>
          </div>
        ))}

        <div className="flex flex-wrap gap-3 items-center justify-between">
          <button
            type="button"
            onClick={() => setShowClearModal(true)}
            className="py-2.5 px-5 text-sm font-medium text-red-600 bg-white rounded-lg border border-red-200 hover:bg-red-50 focus:ring-4 focus:outline-none focus:ring-red-300 dark:bg-gray-800 dark:text-red-400 dark:border-red-900 dark:hover:bg-gray-700"
          >
            Remove all my keys
          </button>

          <div className="flex flex-wrap gap-3 items-center">
            {updatedAt ? (
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Last saved {new Date(updatedAt).toLocaleString()}
              </span>
            ) : null}

            {isDirty ? (
              <button
                type="button"
                onClick={handleDiscard}
                className="py-2.5 px-5 text-sm font-medium text-gray-500 bg-white rounded-lg border border-gray-200 hover:bg-gray-100 hover:text-gray-900 focus:ring-4 focus:outline-none focus:ring-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-500 dark:hover:text-white dark:hover:bg-gray-600"
              >
                Discard changes
              </button>
            ) : null}

            <button
              type="submit"
              disabled={!isDirty || isSaving}
              className="text-white bg-blue-600 hover:bg-blue-700 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center disabled:opacity-60 dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
            >
              {isSaving
                ? "Saving..."
                : isDirty
                ? `Save ${changed.length} change${changed.length === 1 ? "" : "s"}`
                : "Save"}
            </button>
          </div>
        </div>
      </form>
    </>
  );
};

const KeyField = ({
  field,
  saved,
  draft,
  isRevealed,
  onChange,
  onClear,
  onToggleReveal,
}) => {
  const isStagedForClearing = draft === "" && Boolean(saved);
  const hasDraft = draft !== undefined && draft !== "";

  return (
    <div>
      <div className="flex flex-wrap gap-2 items-center justify-between mb-2">
        <label
          htmlFor={field.name}
          className="text-sm font-medium text-gray-900 dark:text-white"
        >
          {field.label}
        </label>

        {isStagedForClearing ? (
          <span className="text-xs font-medium text-amber-600 dark:text-amber-400">
            Will be cleared on save
          </span>
        ) : hasDraft ? (
          <span className="text-xs font-medium text-blue-600 dark:text-blue-400">
            Not saved yet
          </span>
        ) : saved ? (
          <span className="text-xs font-medium text-green-600 dark:text-green-400">
            Saved
          </span>
        ) : (
          <span className="text-xs font-medium text-gray-400 dark:text-gray-500">
            Not set
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <input
            id={field.name}
            name={field.name}
            type={isRevealed ? "text" : "password"}
            autoComplete="off"
            spellCheck="false"
            value={draft ?? ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={saved || "Not set"}
            className="bg-gray-50 border border-gray-300 text-gray-900 rounded-lg focus:ring-blue-600 focus:border-blue-600 block w-full p-2.5 pr-10 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
          />
          <button
            type="button"
            onClick={onToggleReveal}
            aria-label={isRevealed ? "Hide what you typed" : "Show what you typed"}
            title={isRevealed ? "Hide what you typed" : "Show what you typed"}
            className="absolute inset-y-0 right-0 flex items-center px-3 text-gray-400 hover:text-gray-700 dark:hover:text-white"
          >
            {isRevealed ? (
              <RiEyeOffLine className="h-5 w-5" />
            ) : (
              <RiEyeLine className="h-5 w-5" />
            )}
          </button>
        </div>

        {saved && !isStagedForClearing ? (
          <button
            type="button"
            onClick={onClear}
            className="py-2.5 px-3 text-sm font-medium text-gray-500 bg-white rounded-lg border border-gray-200 hover:bg-gray-100 hover:text-gray-900 focus:ring-4 focus:outline-none focus:ring-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-500 dark:hover:text-white dark:hover:bg-gray-600"
          >
            Clear
          </button>
        ) : null}
      </div>

      {field.hint ? (
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          {field.hint}
        </p>
      ) : null}
    </div>
  );
};
