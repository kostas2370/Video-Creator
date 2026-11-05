import { graphConnections, graphLevels } from "../utils/diagrams";

const input = "w-full rounded-lg border border-gray-300 bg-white p-2 text-sm dark:border-gray-600 dark:bg-gray-900";

export function DiagramConnections({ diagram, onChange }) {
  const edges = graphConnections(diagram);
  const canConnect = (source, target, replacing = -1) => {
    const others = edges.filter((_, index) => index !== replacing);
    if (source === target || others.some(edge => edge.source === source && edge.target === target)) return false;
    try { graphLevels(diagram.items.length, [...others, { source, target }]); return true; }
    catch { return false; }
  };
  const update = (index, change) => onChange(edges.map((edge, i) => i === index ? { ...edge, ...change } : edge));
  const choices = diagram.items.flatMap((_, source) => diagram.items.flatMap((_, target) => canConnect(source, target) ? [{ source, target, label: "" }] : []));
  const name = index => diagram.items[index].label || `Item ${index + 1}`;
  return <div className="space-y-3">
    <p className="text-xs text-gray-500 dark:text-gray-400">Arrows can branch from one item or merge into another. Loops are not supported.</p>
    {edges.map((edge, index) => <div key={index} className="space-y-2 rounded-lg border border-gray-200 p-3 dark:border-gray-600">
      <div className="flex items-center gap-2">
        <select className={input} aria-label={`From for arrow ${index + 1}`} value={edge.source} onChange={event => update(index, { source: Number(event.target.value) })}>
          {diagram.items.map((_, source) => canConnect(source, edge.target, index) && <option key={source} value={source}>{name(source)}</option>)}
        </select><span aria-hidden="true">→</span>
        <select className={input} aria-label={`To for arrow ${index + 1}`} value={edge.target} onChange={event => update(index, { target: Number(event.target.value) })}>
          {diagram.items.map((_, target) => canConnect(edge.source, target, index) && <option key={target} value={target}>{name(target)}</option>)}
        </select>
      </div>
      <input className={input} aria-label={`Label for arrow ${index + 1}`} placeholder="Arrow label (optional)" maxLength={30} value={edge.label || ""} onChange={event => update(index, { label: event.target.value })} />
      <button type="button" className="text-xs text-red-600" onClick={() => onChange(edges.filter((_, i) => i !== index))}>Remove arrow {index + 1}</button>
    </div>)}
    {edges.length < 8 && choices.length > 0 && <button type="button" className="text-sm text-blue-600 dark:text-blue-300" onClick={() => onChange([...edges, choices[0]])}>Add arrow</button>}
  </div>;
}
