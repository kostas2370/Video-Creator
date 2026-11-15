import React from "react";
import { PromptTools } from "./PromptTools";

const examples = [
  ["Explainer", "Create a short explainer about how solar panels turn sunlight into electricity. Use simple language and everyday examples."],
  ["Travel story", "Create a relaxing travel video about a weekend in the Greek islands, with seaside villages, local food, and sunset views."],
  ["Product intro", "Introduce a reusable water bottle for people who love the outdoors. Focus on durability, everyday use, and reducing waste."],
];

export function GenerationIdeaStep({ form, onChange, disabled, templateControl }) {
  return <section aria-labelledby="story-heading" className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-7 dark:border-gray-700 dark:bg-gray-800">
    <div className="mb-5"><h2 id="story-heading" className="text-xl font-semibold tracking-tight">Start with your idea</h2><p id="prompt-help" className="mt-1 text-sm text-gray-500 dark:text-gray-400">Describe the topic, what happens, and the tone you want.</p></div>
    <div className="overflow-hidden rounded-2xl border border-gray-300 bg-gray-50 focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-400/20 dark:border-gray-600 dark:bg-gray-900/50">
      <label htmlFor="message" className="block px-4 pt-4 text-xs font-semibold text-gray-500 dark:text-gray-400">Your prompt</label>
      <textarea id="message" name="message" aria-describedby="prompt-help" rows={5} maxLength={2000} required value={form.message} disabled={disabled} onChange={event => onChange(event.target.value)} className="block w-full resize-y border-0 bg-transparent px-4 pb-3 pt-2 text-base leading-7 text-gray-900 outline-none placeholder:text-gray-400 focus:ring-0 disabled:opacity-60 dark:text-white" placeholder="A curious fox finds a lantern that reveals a hidden forest. Warm, playful, and full of wonder…" />
      <div className="flex items-center justify-between gap-2 border-t border-gray-200 px-4 py-2 text-xs text-gray-400 dark:border-gray-700"><span>You can refine the script in your storyboard.</span><span className="shrink-0 tabular-nums" aria-label="Prompt character count">{form.message.length}/2000</span></div>
    </div>
    <PromptTools kind="video" value={form.message} preferences={{ target_audience: form.target_audience, genre: form.genre, gpt_model: form.gpt_model }} disabled={disabled} onUseIdea={idea => onChange(idea.prompt)} onUseRewrite={onChange} />
    {!form.message.trim() && <div className="mt-5 flex flex-wrap items-center gap-2"><span className="mr-1 text-xs text-gray-400">Or try</span>{examples.map(([label, prompt]) => <button key={label} type="button" disabled={disabled} onClick={() => onChange(prompt)} className="rounded-full bg-gray-100 px-3 py-1.5 text-xs text-gray-600 hover:bg-blue-50 hover:text-blue-700 disabled:opacity-40 dark:bg-gray-700/50 dark:text-gray-300 dark:hover:bg-blue-900/40">{label}</button>)}</div>}
    <details className="mt-5 border-t border-gray-100 pt-4 dark:border-gray-700"><summary className="cursor-pointer text-xs font-medium text-gray-500 dark:text-gray-400">Use a saved template</summary><div className="mt-3">{templateControl}</div></details>
  </section>;
}
