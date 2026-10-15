import React, { useEffect, useState } from "react";
import { tokenMetric } from "../utils/usage";
import { getUsage } from "../api/apiService";
import { useAxiosPrivate } from "../hooks/useAxiosPrivate";

const number = value => (value ?? 0).toLocaleString();
const services = { text: "Text / GPT", images: "Images", tts: "Voice / TTS", video: "Video" };
const providers = { OPENAI: "OpenAI", ANTHROPIC: "Anthropic", GEMINI: "Gemini", ELEVENLABS: "ElevenLabs", SIXTYDB: "60dB", STABLE_DIFFUSION: "Stable Diffusion", MIDJOURNEY: "Midjourney" };
const card = "rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800";

function TokenValue({ row, field }) {
  const { label, note } = tokenMetric(row, field);
  return <>{label}{note && <span className="block text-xs font-normal text-amber-600 dark:text-amber-400">{note}</span>}</>;
}

export function Usage() {
  useAxiosPrivate();
  const [period, setPeriod] = useState("30");
  const [refresh, setRefresh] = useState(0);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    getUsage(period).then(result => {
      if (!active) return;
      if (result.ok) setData(result.data);
      else setError(result.message || "Usage could not be loaded.");
      setLoading(false);
    });
    return () => { active = false; };
  }, [period, refresh]);

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">AI usage</h1>
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Consumption from your generation requests in Video Creator.</p>
        </div>
        <div className="flex items-center gap-3">
          <label htmlFor="usage-period" className="sr-only">Usage period</label>
          <select id="usage-period" value={period} onChange={event => setPeriod(event.target.value)} className="rounded-xl border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800">
            <option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="all">All time</option>
          </select>
          <button type="button" disabled={loading} onClick={() => setRefresh(value => value + 1)} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">Refresh</button>
        </div>
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400">Tokens are reported by providers. Voice services are measured in characters; images and video also have their own units. These are usage measurements, not a billing estimate. Only requests made after tracking was enabled are included.</p>
      {loading ? <p role="status">Loading usage…</p> : error ? <p role="alert" className="text-red-600 dark:text-red-400">{error}</p> : data && <>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className={card}><p className="text-sm text-gray-500 dark:text-gray-400">Reported tokens</p><p className="mt-2 text-3xl font-semibold"><TokenValue row={data.totals} field="total_tokens" /></p></div>
          {[["TTS characters", data.totals.characters], ["Images generated", data.totals.images], ["Generation requests", data.totals.requests]].map(([label, value]) => <div key={label} className={card}><p className="text-sm text-gray-500 dark:text-gray-400">{label}</p><p className="mt-2 text-3xl font-semibold">{number(value)}</p></div>)}
        </div>
        {data.breakdown.length === 0 ? <div className={card}><h2 className="font-semibold">No usage recorded in this period</h2><p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Generate a script, image, voice-over, or video clip, then refresh to see your usage.</p></div> : <div className={`${card} overflow-x-auto`}>
          <h2 className="mb-4 text-lg font-semibold">By service and model</h2>
          <table className="w-full whitespace-nowrap text-left text-sm">
            <caption className="sr-only">Provider consumption for the selected period</caption>
            <thead className="text-gray-500 dark:text-gray-400"><tr>{["Service", "Provider / model", "API keys", "Requests", "Input tokens", "Output tokens", "Total tokens", "Other units"].map(label => <th key={label} scope="col" className="px-3 pb-3 font-medium">{label}</th>)}</tr></thead>
            <tbody>{data.breakdown.map(row => <tr key={[row.service, row.provider, row.model, row.key_source].join(":")} className="border-t border-gray-100 dark:border-gray-700">
              <th scope="row" className="px-3 py-4 font-medium">{services[row.service]}</th>
              <td className="px-3 py-4">{providers[row.provider] || row.provider}<span className="block text-xs text-gray-500 dark:text-gray-400">{row.model || "Model not reported"}</span></td>
              <td className="px-3 py-4">{row.key_source === "service" ? "Service" : "Personal"}</td>
              <td className="px-3 py-4">{number(row.requests)}</td>
              {["input_tokens", "output_tokens", "total_tokens"].map(field => <td key={field} className="px-3 py-4"><TokenValue row={row} field={field} /></td>)}
              <td className="px-3 py-4">{row.service === "tts" ? `${number(row.characters)} characters` : row.service === "images" ? `${number(row.images)} images` : row.service === "video" && row.seconds ? `${number(row.seconds)} seconds` : "—"}</td>
            </tr>)}</tbody>
          </table>
        </div>}
        {data.first_recorded_at && <p className="text-xs text-gray-500 dark:text-gray-400">First recorded request: {new Date(data.first_recorded_at).toLocaleString()}</p>}
      </>}
    </main>
  );
}
