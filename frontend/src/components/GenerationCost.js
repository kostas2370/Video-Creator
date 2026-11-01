import React, { useEffect, useState } from "react";
import { getCostEstimate, getScenarioCostEstimate, getProjectCosts } from "../api/apiService";

export function formatCost(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "Price unavailable";
  const amount = Number(value);
  if (amount > 0 && amount < 0.0001) return "<$0.0001";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 4 }).format(amount);
}

export function estimateRange(estimate) {
  if (!estimate) return "Price unavailable";
  const low = formatCost(estimate.low_usd), high = formatCost(estimate.high_usd);
  return low === high ? low : `${low}–${high}`;
}

export function RecordedCost({ metrics }) {
  const requests = metrics?.requests || 0, priced = metrics?.requests_with_cost || 0;
  return <>{formatCost(metrics?.cost_usd)}{priced < requests && <span className="block text-xs font-normal text-amber-700 dark:text-amber-300">{priced} of {requests} requests priced · partial cost</span>}</>;
}

function EstimateDetails({ estimate }) {
  return <>
    <p className="font-semibold">{estimate.partial ? "Known subtotal" : estimate.scope === "scenario" ? "Estimated scenario cost" : estimate.scope === "generation" ? "Estimated generation cost" : "Estimated media cost"}: {estimateRange(estimate)} USD</p>
    <p className="mt-1">{estimate.scope === "scenario" ? "Planning range; actual tokens and retries change the cost." : estimate.scope === "generation" ? "Includes the scenario already drafted. Proceed only starts the remaining media." : "Planning estimate; image inputs and retries may add cost."}{estimate.partial && " Some prices are unavailable."}</p>
    <details className="mt-2"><summary className="cursor-pointer font-medium">Cost breakdown and assumptions</summary>
    <ul className="mt-2 space-y-2">{estimate.lines.map((line, index) => <li key={index}>
      <span className="font-medium">{line.label}: {estimateRange(line)}</span><span className="ml-1">· {line.provider}{line.model && ` / ${line.model}`}</span>
      <span className="block">{Object.entries(line.units).map(([unit, value]) => `${value.toLocaleString()} ${unit}`).join(" · ")}</span>
      {line.note && <span className="block">{line.note}</span>}
      {line.source && <a href={line.source} target="_blank" rel="noreferrer" className="underline">Pricing source</a>}
    </li>)}</ul>
    <p className="mt-2">{estimate.note} Rates checked {estimate.checked_at}. Estimates are not invoices.</p>
    </details>
  </>;
}

export function GenerationCost({ videoId, storyboard, sceneId, operation = "all", text, active = true, refresh = null, scenario }) {
  const requestKey = JSON.stringify(scenario || { video_id: videoId, ...(storyboard ? { storyboard } : {}), ...(sceneId ? { scene_id: sceneId } : {}), operation, ...(text !== undefined ? { text } : {}) });
  const isScenario = !!scenario;
  const key = JSON.stringify([requestKey, refresh, isScenario]);
  const [result, setResult] = useState(null);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!active || (!videoId && !isScenario)) return;
    let current = true;
    const timer = setTimeout(async () => {
      try {
        const response = await (isScenario ? getScenarioCostEstimate : getCostEstimate)(JSON.parse(requestKey));
        if (current) setResult({ key, data: response?.ok ? response.data : null });
      } catch { if (current) setResult({ key, data: null }); }
    }, 300);
    return () => { current = false; clearTimeout(timer); };
  }, [key, requestKey, videoId, active, retry, isScenario]);
  if (!active || (!videoId && !isScenario)) return null;
  return <aside aria-label="Generation cost estimate" className="mt-3 rounded-xl border border-gray-200 bg-gray-50 p-3 text-xs leading-relaxed text-gray-600 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300">
    {!result || result.key !== key ? <p role="status">Estimating generation cost…</p> : result.data ? <EstimateDetails estimate={result.data} /> : <p>Cost estimate unavailable. Generation may still incur provider charges. <button type="button" onClick={() => { setResult(null); setRetry(value => value + 1); }} className="underline">Retry estimate</button></p>}
  </aside>;
}

export function ProjectCosts({ videoId, refresh }) {
  const [result, setResult] = useState(null);
  useEffect(() => {
    let current = true;
    setResult(null);
    Promise.resolve().then(() => getProjectCosts(videoId)).then(response => { if (current) setResult({ id: videoId, data: response?.ok ? response.data : null }); }).catch(() => { if (current) setResult({ id: videoId, data: null }); });
    return () => { current = false; };
  }, [videoId, refresh]);
  const data = result?.id === videoId ? result.data : null;
  return <section aria-label="Project generation costs" className="mt-4 border-t border-gray-100 pt-4 text-sm dark:border-gray-700">
    <h2 className="font-semibold">Generation costs</h2>
    {!result || result.id !== videoId ? <p role="status" className="mt-2">Loading costs…</p> : !data ? <p className="mt-2 text-xs text-gray-500">Project costs could not be loaded.</p> : <>
      <dl className="mt-3 grid gap-3 sm:grid-cols-2"><div><dt>Original generation estimate{data.estimate?.partial && " · partial"}</dt><dd className="font-semibold">{data.estimate ? `${estimateRange(data.estimate)} USD` : "No saved estimate"}</dd></div><div><dt>Recorded generation cost · USD</dt><dd className="font-semibold"><RecordedCost metrics={data.recorded.totals} /></dd></div></dl>
      <p className="mt-3 text-xs">Scenario / script: {estimateRange(data.scenario)}{data.scenario?.partial && " · partial cost"}</p>
      <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">Recorded costs include scenario drafting, media generation, replacements and measured retries. Earlier scenario requests may be missing. These are estimates, not invoices.</p>
    </>}
  </section>;
}
