import { useState } from "react";
import { updateIcon, deleteIcon } from "../api/apiService";
import { IconLibrary } from "./IconLibrary";
import { IconUpload } from "./IconUpload";
import { DeleteModal } from "./DeleteModal";
import { EditorDialog, editorButton, editorInput } from "./ui/EditorDialog";

export function IconAssets() {
  const [selected, setSelected] = useState(null);
  const [version, setVersion] = useState(0);
  const refresh = () => { setSelected(null); setVersion(value => value + 1); };
  return <section role="tabpanel" id="Icon-panel" aria-labelledby="Icon-tab" className="space-y-5 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
    <p className="text-sm text-gray-500 dark:text-gray-400">Browse icons for your diagrams, or upload your own. Your uploads are private and available in the diagram editor.</p>
    <IconUpload key={version} onUploaded={icon => { setVersion(value => value + 1); setSelected(icon); }} />
    <IconLibrary refreshKey={version} onSelect={setSelected} />
    {selected && <IconDetails key={selected.key} icon={selected} onClose={() => setSelected(null)} onSaved={refresh} />}
  </section>;
}

function IconDetails({ icon, onClose, onSaved }) {
  const [name, setName] = useState(icon.name);
  const [description, setDescription] = useState(icon.description || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);
  const changed = name.trim() !== icon.name || description.trim() !== (icon.description || "");
  const save = async () => {
    if (busy || !changed || !name.trim()) return;
    setBusy(true); setError("");
    try {
      const response = await updateIcon(icon.key, { name: name.trim(), description: description.trim() });
      if (response.ok) onSaved();
      else setError(response.message || "Could not save this icon. Try again.");
    } catch { setError("Could not save this icon. Try again."); }
    finally { setBusy(false); }
  };
  return <>
    <EditorDialog open={!deleting} onClose={onClose} title={icon.name} description={icon.is_owner ? "Your private icon" : `${icon.collection} icon collection`} busy={busy} maxWidth="max-w-lg" footer={icon.is_owner && <div className="flex flex-wrap justify-between gap-3">
      <button type="button" disabled={busy} onClick={() => setDeleting(true)} className="rounded-xl px-3 py-3 text-sm text-red-600 dark:text-red-400">Delete icon</button>
      <button type="button" disabled={busy || !changed || !name.trim()} onClick={save} className={editorButton}>{busy ? "Saving…" : "Save changes"}</button>
    </div>}>
      <img src={icon.file} alt={icon.name} className="mx-auto mb-5 h-40 w-40 rounded-xl bg-slate-800 p-4" />
      {icon.is_owner ? <fieldset disabled={busy} className="space-y-4">
        <label className="block text-sm">Icon name<input value={name} maxLength={160} onChange={event => setName(event.target.value)} className={`${editorInput} mt-1`} /></label>
        <label className="block text-sm">Description<textarea value={description} maxLength={500} onChange={event => setDescription(event.target.value)} className={`${editorInput} mt-1`} /></label>
      </fieldset> : <div className="space-y-2 text-sm text-gray-500 dark:text-gray-400">
        {icon.description && <p>{icon.description}</p>}
        {icon.license && <p>License: {icon.license_url ? <a href={icon.license_url} target="_blank" rel="noreferrer" className="text-blue-600 underline dark:text-blue-300">{icon.license}</a> : icon.license}</p>}
        {icon.attribution && <p>{icon.attribution}</p>}
      </div>}
      {error && <p role="alert" className="mt-3 text-sm text-red-600">{error}</p>}
    </EditorDialog>
    <DeleteModal showModal={deleting} setShowModal={setDeleting} id={icon.key} deleteFunction={deleteIcon} mode="image" setItems={onSaved} name="icon" recoveryHint="This removes the icon from your library and from diagrams that use it. Already exported videos stay unchanged." />
  </>;
}
