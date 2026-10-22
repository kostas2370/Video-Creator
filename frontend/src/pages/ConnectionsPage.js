import React, { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { HiOutlineArrowLeft, HiOutlineShieldCheck } from "react-icons/hi2";
import { connectSocialAccount, disconnectSocialAccount, getSocialConnections } from "../api/apiService";
import { PublishingAccounts } from "../components/PublishingAccounts";
import { EditorDialog, editorButton } from "../components/ui/EditorDialog";

const callbackMessages = {
  connected: "Account connected. You’re ready to publish.",
  failed: "The connection did not finish. Try again, or check the platform’s app setup if this continues.",
  tiktok_sandbox_required: "This TikTok account is not enabled for testing. The app owner must add it under Sandbox settings → Target users, then connect it again.",
};

export function Connections() {
  const [params, setParams] = useSearchParams();
  const video = params.get("video");
  const returnVideo = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(video || "") ? video : undefined;
  const [connections, setConnections] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pendingDisconnect, setPendingDisconnect] = useState(null);
  const actionPending = useRef(false);
  const callback = callbackMessages[params.get("publishing")];
  const callbackFailed = params.get("publishing") !== "connected";

  useEffect(() => {
    let current = true;
    setLoading(true);
    setError("");
    async function load() {
      try {
        const result = await getSocialConnections();
        if (!current) return;
        if (result.ok) setConnections(result.data);
        else setError(result.message || "Your connections could not be loaded.");
      } catch {
        if (current) setError("Your connections could not be loaded. Please try again.");
      } finally {
        if (current) setLoading(false);
      }
    }
    load();
    return () => { current = false; };
  }, [reload]);

  const connect = async platform => {
    if (actionPending.current) return;
    actionPending.current = true;
    setBusy(platform); setError(""); setNotice("");
    try {
      const result = await connectSocialAccount(platform, returnVideo);
      if (result.ok) window.location.assign(result.data.url);
      else setError(result.message || "Could not start this connection. Please try again.");
    } catch {
      setError("Could not start this connection. Please try again.");
    } finally {
      actionPending.current = false;
      setBusy("");
    }
  };
  const disconnect = async () => {
    if (actionPending.current || !pendingDisconnect) return;
    actionPending.current = true;
    setBusy("disconnect"); setError(""); setNotice("");
    try {
      const result = await disconnectSocialAccount(pendingDisconnect.id);
      if (result.ok) {
        setConnections(current => ({ ...current, accounts: current.accounts.filter(account => account.id !== pendingDisconnect.id) }));
        setNotice(`${pendingDisconnect.display_name} disconnected.`);
        setPendingDisconnect(null);
      } else setError(result.message || "Could not disconnect this account. Please try again.");
    } catch {
      setError("Could not disconnect this account. Please try again.");
    } finally {
      actionPending.current = false;
      setBusy("");
    }
  };

  return <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
    {returnVideo && <Link to={`/videos/${returnVideo}/?publishing=open`} className="mb-6 inline-flex min-h-11 items-center gap-2 text-sm font-medium text-blue-600 dark:text-blue-400"><HiOutlineArrowLeft aria-hidden="true" />Back to publishing</Link>}
    <header className="mb-8"><p className="mb-2 text-xs font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-400">Your audience, connected</p><h1 className="text-3xl font-bold tracking-tight">Connections</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-400">Connect your accounts once, then choose where to publish from any video. Manage your YouTube channels, TikTok accounts, and Instagram accounts here.</p></header>
    {callback && <div role={callbackFailed ? "alert" : "status"} className={`mb-5 flex items-start justify-between gap-3 rounded-xl p-4 text-sm ${callbackFailed ? "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-300" : "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"}`}><p>{callback}</p><button type="button" aria-label="Dismiss connection result" className="min-h-6 min-w-6 shrink-0" onClick={() => setParams(previous => { const next = new URLSearchParams(previous); next.delete("publishing"); return next; }, { replace: true })}>×</button></div>}
    {notice && <p role="status" className="mb-5 rounded-xl bg-blue-50 p-4 text-sm text-blue-700 dark:bg-blue-950 dark:text-blue-300">{notice}</p>}
    {error && !pendingDisconnect && <div role="alert" className="mb-5 rounded-xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{error}{!connections && <button type="button" onClick={() => setReload(value => value + 1)} className="ml-3 min-h-11 underline">Try again</button>}</div>}
    {loading ? <p role="status" className="py-12 text-center text-sm text-gray-500 dark:text-gray-400">Loading your connections…</p> : connections && <PublishingAccounts connections={connections} busy={busy} onConnect={connect} onDisconnect={account => { setError(""); setPendingDisconnect(account); }} />}
    <aside className="mt-8 flex items-start gap-3 rounded-2xl border border-gray-200 p-5 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400"><HiOutlineShieldCheck aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-blue-500" /><div><p className="font-medium text-gray-700 dark:text-gray-200">You stay in control</p><p className="mt-1 leading-6">Sign in securely on each platform. Viddie never asks for your social account password. Nothing is posted until you review a video and confirm publishing.</p></div></aside>
    <EditorDialog open={!!pendingDisconnect} onClose={() => { setPendingDisconnect(null); setError(""); }} title="Disconnect account?" description={`Remove ${pendingDisconnect?.display_name || "this account"} from Viddie.`} busy={!!busy} maxWidth="max-w-lg">
      <p className="text-sm leading-6 text-gray-600 dark:text-gray-300">Queued uploads for this account will be cancelled. Uploads already in progress may finish. Videos already published will stay on the platform. You can connect this account again anytime.</p>
      {error && <p role="alert" className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>}
      <div className="mt-6 flex flex-wrap justify-end gap-3"><button type="button" disabled={!!busy} onClick={() => setPendingDisconnect(null)} className="min-h-11 rounded-xl border border-gray-200 px-4 py-3 text-sm dark:border-gray-600">Keep connected</button><button type="button" disabled={!!busy} onClick={disconnect} className={editorButton}>{busy ? "Disconnecting…" : "Disconnect account"}</button></div>
    </EditorDialog>
  </main>;
}
