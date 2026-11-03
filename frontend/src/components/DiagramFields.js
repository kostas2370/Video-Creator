import { diagramTemplates, newDiagram } from "../utils/diagrams";

const input = "mt-1 w-full rounded-lg border border-gray-300 bg-white p-2 text-sm dark:border-gray-600 dark:bg-gray-900";

export function DiagramFields({ value, onChange, optional = false }) {
  const update = changes => onChange({ ...value, ...changes });
  const updateItem = (index, changes) => update({ items: value.items.map((item, i) => i === index ? { ...item, ...changes } : item) });
  const selectTemplate = template => {
    if (!template) { onChange(null); return; }
    const current = value || newDiagram(template);
    onChange({ ...current, template, items: current.items.slice(0, diagramTemplates[template].maxItems) });
  };
  return <div className="space-y-3">
    <label className="block text-sm font-medium">Educational animation
      <select className={input} value={value?.template || ""} onChange={event => selectTemplate(event.target.value)}>
        {optional && <option value="">None</option>}
        {Object.entries(diagramTemplates).map(([key, { label }]) => <option key={key} value={key}>{label}</option>)}
      </select>
    </label>
    <p className="text-xs text-gray-500 dark:text-gray-400">Reveals information over the scene using shapes and text. Uses no video-generation credits. Timing is spread across the scene, not synchronized to individual words.</p>
    {value && <>
      <label className="block text-sm">Diagram heading<input className={input} maxLength={60} value={value.title} onChange={event => update({ title: event.target.value })} /></label>
      {value.items.map((item, index) => <div key={index} className="space-y-2 rounded-lg border border-gray-200 p-3 dark:border-gray-600">
        <label className="block text-sm">Item {index + 1}<input required className={input} maxLength={40} value={item.label} onChange={event => updateItem(index, { label: event.target.value })} /></label>
        <label className="block text-sm">Detail {index + 1}<textarea className={input} rows={2} maxLength={90} value={item.detail} onChange={event => updateItem(index, { detail: event.target.value })} /></label>
        {value.items.length > 2 && <button type="button" className="text-xs text-red-600" onClick={() => update({ items: value.items.filter((_, i) => i !== index) })}>Remove item {index + 1}</button>}
      </div>)}
      {value.items.length < diagramTemplates[value.template].maxItems && <button type="button" className="text-sm text-blue-600 dark:text-blue-300" onClick={() => update({ items: [...value.items, { label: "", detail: "" }] })}>Add item</button>}
    </>}
  </div>;
}
