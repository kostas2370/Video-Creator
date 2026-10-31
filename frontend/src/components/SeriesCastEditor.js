import { useRef } from "react";
import { useDraftSection } from "../hooks/useCreationDraft";
import { editorInput } from "./ui/EditorDialog";
import { CharacterImageControls, characterImageUrl } from "./CharacterImageControls";
import { CharacterDescriptionDraft } from "./CharacterDescriptionDraft";
import { characterIsApproved, patchCharacter } from "../utils/series";

const fields = [
  { key: "wardrobe", label: "Default wardrobe", limit: 150, placeholder: "Clothes and accessories" },
  { key: "personality", label: "Personality & motivation", limit: 200, placeholder: "What they want, fear and believe" },
  { key: "relationships", label: "Starting relationships", limit: 200, placeholder: "Friends, rivals, family or secrets" },
];

export function SeriesCastEditor({ cast, onChange, visualStyle = "", premise = "", storyFormat = "GENERAL" }) {
  const [selection, setSelection] = useDraftSection("cast-selection", { active: cast[0]?.id || null });
  const active = selection.active;
  const setActive = value => setSelection({ active: value });
  const selected = cast.some(character => character.id === active) ? active : cast[0]?.id;
  const latest = useRef(cast);
  latest.current = cast;
  const patch = (id, values) => onChange(latest.current.map(character => character.id === id ? patchCharacter(character, values) : character));
  const add = () => {
    const character = { id: crypto.randomUUID(), name: "", appearance: "", wardrobe: "", personality: "", relationships: "" };
    onChange([...cast, character]); setActive(character.id);
  };
  return <section aria-label="Recurring characters" className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><h4 className="text-sm font-semibold">Your cast <span className="ml-2 font-normal text-gray-400">{cast.length}/6</span></h4><button type="button" disabled={cast.length >= 6} onClick={add} className="rounded-xl border border-gray-200 px-4 py-2 text-sm font-semibold disabled:opacity-50 dark:border-gray-700">Add character</button></div>
    {cast.length === 0 && <p className="rounded-2xl border border-dashed border-gray-200 p-8 text-center text-sm text-gray-500 dark:border-gray-700">Let AI design your cast, or add a character of your own.</p>}
    {cast.length > 0 && <div className="flex gap-2 overflow-x-auto pb-1" aria-label="Choose a character">{cast.map((character, index) => <button key={character.id} type="button" aria-label={`Edit character ${character.name || index + 1}`} aria-pressed={selected === character.id} onClick={() => setActive(character.id)} className={`flex shrink-0 items-center gap-3 rounded-2xl border px-4 py-3 text-left ${selected === character.id ? "border-indigo-400 bg-indigo-50 dark:border-indigo-500 dark:bg-indigo-900/40" : "border-gray-200 dark:border-gray-700"}`}>{character.image ? <img src={characterImageUrl(character.image)} alt="" className="h-10 w-10 rounded-xl object-cover" /> : <span aria-hidden="true" className="flex h-10 w-10 items-center justify-center rounded-xl bg-gray-100 text-lg font-semibold text-gray-400 dark:bg-gray-900">{character.name?.[0] || "+"}</span>}<span><span className="block text-sm font-semibold">{character.name || `Character ${index + 1}`}</span><span className="text-xs text-gray-500">{characterIsApproved(character, visualStyle) ? "Look approved" : "Needs a look"}</span></span></button>)}</div>}
    {cast.map((character, index) => <div key={character.id} hidden={selected !== character.id}>
      <fieldset className="space-y-5 rounded-2xl border border-gray-200 p-4 sm:p-5 dark:border-gray-700">
        <legend className="px-2 text-sm font-semibold">Character {index + 1}</legend>
        <div className="text-right"><button type="button" onClick={() => onChange(latest.current.filter(item => item.id !== character.id))} className="text-xs text-gray-500 hover:text-red-600">Remove character {index + 1}</button></div>
        <label className="block text-sm font-semibold">Character {index + 1} name<input required maxLength={60} value={character.name} onChange={event => patch(character.id, { name: event.target.value })} className={`${editorInput} mt-2`} placeholder="Give them a name, or let AI suggest one" /></label>
        <CharacterDescriptionDraft character={character} premise={premise} visualStyle={visualStyle} storyFormat={storyFormat} castNames={cast.map(item => item.name).filter(Boolean)} onUse={values => patch(character.id, values)} />
        <label className="block text-sm font-semibold">Fixed appearance<textarea required maxLength={300} rows={3} value={character.appearance} onChange={event => patch(character.id, { appearance: event.target.value })} placeholder="Describe their face, shape, colors and distinguishing features, or use AI above." className={`${editorInput} mt-2 font-normal`} /></label>
        <details className="rounded-xl border border-gray-100 p-4 dark:border-gray-700"><summary className="cursor-pointer text-sm font-semibold">Personality, wardrobe & relationships</summary><div className="mt-4 space-y-4">{fields.map(field => <label key={field.key} className="block text-sm font-semibold">{field.label}<textarea maxLength={field.limit} rows={2} value={character[field.key] || ""} onChange={event => patch(character.id, { [field.key]: event.target.value })} placeholder={field.placeholder} className={`${editorInput} mt-2 font-normal`} /></label>)}</div></details>
        <CharacterImageControls character={character} visualStyle={visualStyle} onPatch={values => patch(character.id, values)} />
      </fieldset>
    </div>)}
  </section>;
}
