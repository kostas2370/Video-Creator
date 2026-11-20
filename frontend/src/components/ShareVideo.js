import { useEffect, useState } from "react";
import { HiOutlineLink, HiOutlinePlay, HiOutlineGlobeAlt, HiOutlineClock, HiOutlineSquare2Stack, HiOutlineCheck, HiArrowUpRight, HiOutlineLockClosed } from "react-icons/hi2";
import { createVideoShare, getVideoShare, revokeVideoShare } from "../api/apiService";
import { EditorDialog } from "./ui/EditorDialog";
import "./ShareVideo.css";

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
    <button type="button" onClick={() => setOpen(true)} aria-label="Share link" aria-haspopup="dialog" className="share-toolbar-button" title="Share a public viewing link"><HiOutlineLink aria-hidden="true" /></button>
    <EditorDialog open={open} onClose={() => setOpen(false)} title="Share your video" description="Good stories are meant to be seen." busy={busy} maxWidth="max-w-xl" panelClassName="share-dialog" icon={HiOutlineLink}
      footer={!loading && share && <div className="share-modal-footer">
        {share.active ? <><button type="button" disabled={busy} onClick={changeSharing} className="share-stop">{busy ? "Stopping…" : "Stop sharing"}</button><button type="button" disabled={busy} onClick={() => setOpen(false)} className="share-primary">Done<HiOutlineCheck aria-hidden="true" /></button></> : <button type="button" disabled={busy || !video.output} onClick={changeSharing} className="share-primary share-full">{busy ? "Creating…" : "Create share link"}<HiOutlineLink aria-hidden="true" /></button>}
      </div>}>
      <div className="share-modal-content">
        <div className="share-preview">
          <span className="share-preview-art" aria-hidden="true"><HiOutlinePlay /></span>
          <div><span className="share-section-label">YOUR VIDEO</span><h3>{video.title || "Untitled video"}</h3><p>Latest export · Viddie viewing page</p></div>
        </div>
        {loading && <p role="status" className="share-loading">Loading sharing details…</p>}
        {error && <p role="alert" className="share-error">{error}</p>}
        {!loading && share && <>
          <div className="share-access"><span className="share-access-icon">{share.active ? <HiOutlineGlobeAlt aria-hidden="true" /> : <HiOutlineLockClosed aria-hidden="true" />}</span><div><h4>{share.active ? "Anyone with the link" : "Ready when you are"}</h4><p>{share.active ? "Watch without an account or sign-in." : "Create a link to let anyone watch without signing in."}</p></div><span className={`share-status ${share.active ? "is-live" : ""}`}><span />{share.active ? "Live" : "Off"}</span></div>
          {share.active ? <>
            <label className="share-field-label" htmlFor={`share-link-${video.id}`}>Public viewing link</label>
            <div className="share-link-box"><HiOutlineLink aria-hidden="true" /><input id={`share-link-${video.id}`} readOnly value={url} onFocus={event => event.target.select()} /><button type="button" onClick={copy} aria-label={copied ? "Copied!" : "Copy link"} className={copied ? "is-copied" : ""}>{copied ? <HiOutlineCheck aria-hidden="true" /> : <HiOutlineSquare2Stack aria-hidden="true" />}<span>{copied ? "Copied!" : "Copy link"}</span></button></div>
            <div className="share-link-meta"><span><HiOutlineClock aria-hidden="true" />{share.expires_at ? `Expires ${new Date(share.expires_at).toLocaleString()}` : "No expiration"}</span><a href={url} target="_blank" rel="noreferrer">Preview page <HiArrowUpRight aria-hidden="true" /></a></div>
          </> : <>
            {!video.output && <p className="share-export-note">Export your video to create a viewing link.</p>}
            <div className="share-expiry"><HiOutlineClock aria-hidden="true" /><div><label htmlFor={`share-expiry-${video.id}`}>Link expires</label><p>Choose how long it stays available.</p></div><select id={`share-expiry-${video.id}`} value={days} onChange={event => setDays(event.target.value)} disabled={busy || !video.output}><option value="">Never</option><option value="1">In 1 day</option><option value="7">In 7 days</option><option value="30">In 30 days</option></select></div>
          </>}
          <p className="share-footnote">Includes your title, description, and tags. Saved details and future exports update the same link. You can stop sharing at any time.</p>
        </>}
      </div>
    </EditorDialog>
  </>;
}
