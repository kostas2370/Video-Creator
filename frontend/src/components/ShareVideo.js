import { useEffect, useState } from "react";
import { HiOutlineLink } from "react-icons/hi2";
import { createVideoShare, getVideoShare, revokeVideoShare } from "../api/apiService";
import { toolbarAction } from "./VideoToolbar";
import { EditorDialog, editorButton, editorInput, editorSecondaryButton } from "./ui/EditorDialog";

export function ShareVideo({ video }) {
  const [open, setOpen] = useState(false);
  const [share, setShare] = useState(null);
  const [days, setDays] = useState("");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const url = share?.active ? new URL(share.path, window.location.origin).href : "";

  useEffect(() => {
    if (!open) return;
    let current = true;
    setLoading(true);
    setShare(null);
    setError("");
    setCopied(false);
    getVideoShare(video.id).then(result => {
      if (!current) return;
      if (result.ok) setShare(result.data);
      else setError(result.message || "Sharing details could not be loaded. Try again.");
      setLoading(false);
    });
    return () => { current = false; };
  }, [open, video.id]);

  const changeSharing = async () => {
    setBusy(true);
    setError("");
    setCopied(false);
    const result = share.active
      ? await revokeVideoShare(video.id)
      : await createVideoShare(video.id, { expires_in_days: days ? Number(days) : null });
    if (result.ok) setShare(share.active ? { active: false } : result.data);
    else setError(result.message || "Sharing could not be updated. Try again.");
    setBusy(false);
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setError("");
    } catch {
      setError("Select the link and copy it manually.");
    }
  };

  return <>
    <button type="button" onClick={() => setOpen(true)} aria-haspopup="dialog" className={toolbarAction} title="Share a public viewing link"><HiOutlineLink aria-hidden="true" className="h-4 w-4" />Share link</button>
    <EditorDialog open={open} onClose={() => setOpen(false)} title="Share your video" description="Anyone with the link can watch, without signing in." busy={busy} maxWidth="max-w-xl">
      <div className="space-y-5">
        <p className="text-sm leading-relaxed text-gray-500 dark:text-gray-400">Your latest export, saved title, description, and tags appear on a Viddie viewing page. Changes to those details and future exports update the same link.</p>
        {loading && <p role="status">Loading sharing details…</p>}
        {error && <p role="alert" className="text-sm text-red-600 dark:text-red-300">{error}</p>}
        {!loading && share && (share.active ? <>
          <label className="block text-sm font-semibold">Public viewing link<input readOnly value={url} onFocus={event => event.target.select()} className={`${editorInput} mt-2`} /></label>
          <div className="flex flex-wrap gap-2"><button type="button" onClick={copy} className={editorButton}>{copied ? "Copied!" : "Copy link"}</button><a href={url} target="_blank" rel="noreferrer" className={editorSecondaryButton}>Open page</a></div>
          <p className="text-sm text-gray-500 dark:text-gray-400">{share.expires_at ? `Expires ${new Date(share.expires_at).toLocaleString()}.` : "This link has no expiry."} You can stop sharing at any time.</p>
          <button type="button" disabled={busy} onClick={changeSharing} className={editorSecondaryButton}>{busy ? "Stopping…" : "Stop sharing"}</button>
        </> : <>
          {!video.output && <p className="text-sm">Export your video to create a viewing link.</p>}
          <label className="block text-sm font-semibold">Link expires<select value={days} onChange={event => setDays(event.target.value)} disabled={busy || !video.output} className={`${editorInput} mt-2`}><option value="">Never</option><option value="1">In 1 day</option><option value="7">In 7 days</option><option value="30">In 30 days</option></select></label>
          <button type="button" disabled={busy || !video.output} onClick={changeSharing} className={editorButton}>{busy ? "Creating…" : "Create share link"}</button>
        </>)}
      </div>
    </EditorDialog>
  </>;
}
