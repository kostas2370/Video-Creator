import React, { useId } from "react";
import { useDraftSection } from "../hooks/useCreationDraft";
import { IdeaGenerator } from "./IdeaGenerator";
import { PromptRewrite } from "./PromptRewrite";

export function PromptTools({ kind, value, preferences, disabled, onUseIdea, onUseRewrite }) {
  const [saved, updateSaved] = useDraftSection(`prompt-tools:${kind}`, { active: "" });
  const id = useId();
  const close = () => updateSaved({ active: "" });
  const tools = [
    { key: "ideas", label: "Find ideas", disabled },
    { key: "rewrite", label: "Rewrite with AI", disabled: disabled || !value.trim() },
  ];

  return (
    <section aria-label="Prompt assistance" className="mt-3">
      <div className="flex flex-wrap items-center gap-2">
        {tools.map(tool => (
          <button
            key={tool.key}
            type="button"
            aria-expanded={saved.active === tool.key}
            aria-controls={`${id}-${tool.key}`}
            disabled={tool.disabled}
            onClick={() => updateSaved({ active: saved.active === tool.key ? "" : tool.key })}
            className={`rounded-lg border px-3 py-2 text-xs font-semibold transition disabled:opacity-40 ${saved.active === tool.key ? "border-indigo-300 bg-indigo-50 text-indigo-700 dark:border-indigo-600 dark:bg-indigo-500/15 dark:text-indigo-200" : "border-gray-200 text-gray-600 hover:border-indigo-300 hover:text-indigo-600 dark:border-gray-600 dark:text-gray-300 dark:hover:text-indigo-200"}`}
          >
            {tool.label}
          </button>
        ))}
        <span className="text-xs text-gray-400">Optional AI help</span>
      </div>
      <div
        id={`${id}-ideas`}
        hidden={saved.active !== "ideas"}
        className="mt-3 rounded-xl bg-gray-50 p-4 dark:bg-gray-900/40"
      >
        <IdeaGenerator
          kind={kind}
          seed={value}
          preferences={preferences}
          disabled={disabled}
          onUse={idea => {
            onUseIdea(idea);
            close();
          }}
        />
      </div>
      <div
        id={`${id}-rewrite`}
        hidden={saved.active !== "rewrite"}
        className="mt-3 rounded-xl bg-gray-50 p-4 dark:bg-gray-900/40"
      >
        <PromptRewrite
          embedded
          kind={kind}
          value={value}
          preferences={preferences}
          disabled={disabled}
          onUse={text => {
            onUseRewrite(text);
            close();
          }}
        />
      </div>
    </section>
  );
}
