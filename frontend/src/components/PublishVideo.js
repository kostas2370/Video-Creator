import React, { useEffect, useRef, useState } from "react";
import { HiOutlineShare } from "react-icons/hi2";
import {
  connectSocialAccount, disconnectSocialAccount, getPostingContext, getPublishJobs,
  getSocialConnections, publishVideo, refreshPublishStatus,
} from "../api/apiService";
import { EditorDialog, editorButton, editorInput } from "./ui/EditorDialog";
import { PublishingAccounts } from "./PublishingAccounts";
import { youtubeTags, youtubeTagLength, descriptionBytes } from "../utils/youtubeMetadata";
import { toolbarAction } from "./VideoToolbar";

const active = new Set(["QUEUED", "UPLOADING", "PROCESSING", "PUBLISHING"]);
const statuses = { QUEUED: "Waiting to upload", UPLOADING: "Uploading", PROCESSING: "Platform processing",
  PUBLISHING: "Publishing", PUBLISHED: "Upload completed", FAILED: "Upload failed", NEEDS_CHECK: "Check the platform before trying again" };
const privacyNames = { private: "Private", unlisted: "Unlisted", public: "Public", SELF_ONLY: "Only me",
  MUTUAL_FOLLOW_FRIENDS: "Friends", FOLLOWER_OF_CREATOR: "Followers", PUBLIC_TO_EVERYONE: "Everyone" };
const blankOptions = video => ({ title: video.title || "", caption: video.description || "", tags: (video.tags?.youtube || []).join(", "), privacy: "", made_for_kids: "",
  synthetic: video.video_type === "AI", allow_comment: false, allow_duet: false, allow_stitch: false,
  own_brand: false, branded_content: false, music_consent: false, share_to_feed: false, confirmed: false });

export function PublishVideo({ video, disabled = false, onEditDetails }) {
  const [open, setOpen] = useState(() => new URLSearchParams(window.location.search).has("publishing"));
  const [connections, setConnections] = useState({ platforms: [], accounts: [] });
  const [accountId, setAccountId] = useState("");
  const [context, setContext] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [options, setOptions] = useState(() => blankOptions(video));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const requestId = useRef(null);
  const contextGeneration = useRef(0);
  const account = connections.accounts.find(item => item.id === accountId);
  const platform = account?.platform;
  useEffect(() => {
    setOptions(previous => ({ ...previous, title: video.title || "", tags: (video.tags?.youtube || []).join(", "), ...(platform === "youtube" ? { caption: video.description || "" } : {}) }));
  }, [video.title, video.description, video.tags, platform]);
  const parsedTags = youtubeTags(options.tags);
  const invalidYouTube = platform === "youtube" && (youtubeTagLength(parsedTags) > 500 || parsedTags.length > 20 || parsedTags.some(tag => Array.from(tag).length > 80) || descriptionBytes(options.caption) > 5000);
  const ready = video.status === "COMPLETED" && video.output;

  const load = async () => {
    const [linked, history] = await Promise.all([getSocialConnections(), getPublishJobs(video.id)]);
    if (linked.ok) {
      setConnections(linked.data);
      const available = linked.data.accounts.filter(account => !account.needs_reconnect);
      if (available.length === 1) setAccountId(previous => previous || available[0].id);
    }
    if (history.ok) setJobs(history.data);
    if (!linked.ok || !history.ok) setError(linked.message || history.message || "Publishing details could not be loaded.");
  };
  useEffect(() => {
    if (!open) return;
    let current = true;
    setLoading(true);
    load().finally(() => { if (current) setLoading(false); });
    const result = new URLSearchParams(window.location.search).get("publishing");
    if (result === "failed") setError("The account connection did not finish. Check the developer app setup and try connecting again.");
    if (result === "tiktok_sandbox_required") setError("This TikTok account is not enabled for testing. The app owner must add it under Sandbox settings → Target users, then connect it again.");
    return () => { current = false; };
    // Reload once when this video's publishing dialog opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, video.id]);
  useEffect(() => {
    if (!open || !jobs.some(job => active.has(job.status))) return;
    let current = true;
    const timer = setInterval(async () => {
      const result = await getPublishJobs(video.id);
      if (current && result.ok) setJobs(result.data);
    }, 4000);
    return () => { current = false; clearInterval(timer); };
  }, [open, video.id, jobs]);
  useEffect(() => {
    const generation = ++contextGeneration.current;
    setContext(null);
    setOptions({ ...blankOptions(video), ...(platform !== "youtube" ? { caption: "" } : {}) });
    requestId.current = null;
    setSubmitted(false);
    if (!accountId) return;
    getPostingContext(accountId).then(result => {
      if (contextGeneration.current !== generation) return;
      if (result.ok) setContext(result.data);
      else setError(result.message || "This account is not ready to publish. Reconnect it and try again.");
    });
    // Changes to the selected account require fresh privacy and interaction choices.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accountId, video.id]);
  const change = event => {
    const { name, value, checked, type } = event.target;
    setOptions(previous => ({
      ...previous, [name]: type === "checkbox" ? checked : value,
      ...(["own_brand", "branded_content"].includes(name) ? { music_consent: false } : {}),
      ...(name === "branded_content" && checked && previous.privacy === "SELF_ONLY" ? { privacy: "" } : {}),
    }));
  };
  const connect = async name => {
    setBusy("connect"); setError("");
    const result = await connectSocialAccount(name, video.id);
    if (result.ok) window.location.assign(result.data.url);
    else { setError(result.message); setBusy(""); }
  };
  const disconnect = async id => {
    setBusy("disconnect"); setError("");
    const result = await disconnectSocialAccount(id);
    if (result.ok) { if (accountId === id) setAccountId(""); await load(); }
    else setError(result.message);
    setBusy("");
  };
  const submit = async event => {
    event.preventDefault();
    if (!ready || busy || submitted || !context || invalidYouTube) return;
    setBusy("publish"); setError("");
    requestId.current ||= crypto.randomUUID();
    const payload = { ...options, account: accountId, video: video.id, request_id: requestId.current, export_updated_at: video.updated_at };
    if (platform === "youtube") {
      payload.made_for_kids = options.made_for_kids === "yes";
      payload.tags = parsedTags;
    } else { delete payload.made_for_kids; delete payload.tags; }
    const result = await publishVideo(payload);
    if (result.ok) { setSubmitted(true); await load(); }
    else setError(result.message);
    setBusy("");
  };
  const refresh = async job => {
    setBusy("refresh"); setError("");
    const result = await refreshPublishStatus(job.id);
    if (!result.ok) setError(result.message);
    await load(); setBusy("");
  };
  const check = (name, label, extra = {}) => <label className="flex items-start gap-2 text-sm"><input type="checkbox" name={name} checked={!!options[name]} onChange={change} className="mt-1 rounded" {...extra} /><span>{label}</span></label>;

  return <>
    <button type="button" disabled={disabled || !ready} title={ready ? "Upload the last exported video to a connected account" : "Export your video before publishing"} onClick={() => setOpen(true)} className={toolbarAction}><HiOutlineShare aria-hidden="true" className="h-4 w-4" />Publish</button>
    <EditorDialog open={open} onClose={() => setOpen(false)} title="Ready to share?" description="Prepare your post, choose your audience, and publish your latest export." busy={!!busy} maxWidth="max-w-4xl" footer={<div className="space-y-3">
      {error && <p role="alert" className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <div className="flex flex-wrap items-center justify-between gap-3"><div className="min-w-0 text-xs text-gray-500 dark:text-gray-400">{submitted ? "Upload requested · follow its status below" : account ? <><span className="font-semibold text-gray-800 dark:text-gray-200">{account.display_name}</span><span className="ml-2">{privacyNames[options.privacy] || "Choose visibility"}</span></> : "Connect an account to get started"}</div><div className="flex gap-2"><button type="button" disabled={!!busy} onClick={() => setOpen(false)} className="rounded-xl px-4 py-3 text-sm font-medium text-gray-500 dark:text-gray-300">{submitted ? "Done" : "Cancel"}</button><button type="submit" form="publish-video-form" disabled={!ready || !account || !context || !!busy || submitted || invalidYouTube} className={editorButton}>{busy === "publish" ? "Starting upload…" : account ? `Publish to ${account.platform === "youtube" ? "YouTube" : account.platform === "tiktok" ? "TikTok" : "Instagram"}` : "Publish video"}</button></div></div>
    </div>}>
      <div className="space-y-6">
        <section className="grid gap-4 rounded-2xl border border-gray-200 bg-gray-50 p-4 sm:grid-cols-[minmax(0,240px)_1fr] dark:border-gray-700 dark:bg-gray-900/50" aria-label="Export preview">
          {video.output && <video src={video.output} controls preload="metadata" className="max-h-44 w-full rounded-xl bg-black" />}
          <div className="self-center"><p className="text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">Your latest export</p><h3 className="mt-2 break-words text-lg font-semibold">{video.title}</h3><p className="mt-2 text-sm leading-6 text-gray-500 dark:text-gray-400">Preview the video before sharing. If you've edited the project, export again to include your changes.</p></div>
        </section>
        {loading && <p role="status">Loading connected accounts…</p>}
        <details className="rounded-xl border border-gray-200 p-4 dark:border-gray-700" open={connections.accounts.length === 0}><summary className="cursor-pointer text-sm font-semibold">Connected accounts <span className="ml-2 font-normal text-gray-500">{connections.accounts.length} available</span></summary><div className="mt-4"><PublishingAccounts connections={connections} busy={!!busy} onConnect={connect} onDisconnect={disconnect} /></div></details>
        {connections.accounts.length > 0 && <form id="publish-video-form" onSubmit={submit} className="space-y-4">
          <div><p className="text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">Prepare your post</p><h3 className="mt-1 text-xl font-semibold">Make it yours</h3></div>
          <fieldset disabled={!!busy || submitted} className="space-y-4">
            <label className="block text-sm">Publish to<select required value={accountId} onChange={event => { setError(""); setAccountId(event.target.value); }} className={`${editorInput} mt-1`}><option value="">Choose an account</option>{connections.accounts.map(row => <option key={row.id} value={row.id} disabled={row.needs_reconnect}>{row.platform} · {row.display_name}{row.needs_reconnect ? " · Reconnect required" : ""}</option>)}</select></label>
            {account && <>
              {platform === "tiktok" && <p className="text-sm">Posting as <strong>{context?.creator_nickname || account.display_name}</strong>{context?.max_video_post_duration_sec ? ` · Up to ${context.max_video_post_duration_sec} seconds` : ""}</p>}
              {platform === "youtube" && <section className="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900/40" aria-label="Saved video details">
                <div className="flex items-center justify-between gap-3"><h3 className="text-sm font-semibold">Video details</h3><button type="button" onClick={() => { setOpen(false); onEditDetails?.(); }} className="text-sm font-semibold text-blue-600 dark:text-blue-400">Edit details</button></div>
                <p className="mt-3 break-words font-semibold">{options.title}</p>
                <p className="mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap break-words text-sm text-gray-600 dark:text-gray-300">{options.caption || "No description yet. Add one in Video details."}</p>
                <div className="mt-3 flex flex-wrap gap-2">{parsedTags.map(tag => <span key={tag} className="rounded-lg bg-white px-2 py-1 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-300">{tag}</span>)}</div>
                {!parsedTags.length && <p className="mt-3 text-xs text-gray-500">No YouTube tags saved.</p>}
                {invalidYouTube && <p role="alert" className="mt-3 text-sm text-amber-700 dark:text-amber-400">These details exceed YouTube's limits. Use Edit details to shorten the tags or description.</p>}
                <p className="mt-3 text-xs text-gray-500">Publishing uses the details saved with this project.</p>
              </section>}
              {platform === "youtube" && <div className="text-sm text-gray-500">
                {video.cover || video.thumbnail ? <><img src={video.cover || video.thumbnail} alt="Thumbnail to upload to YouTube" className="mb-2 max-h-36 rounded-lg" /><p>Your saved thumbnail will be uploaded with this video. Your channel needs access to custom thumbnails.</p></> : <p>No saved thumbnail. YouTube will choose a frame automatically. Create a cover first to use a custom thumbnail.</p>}
              </div>}
              {platform !== "youtube" && <label className="block text-sm">Caption and hashtags<textarea name="caption" value={options.caption} rows={4} maxLength={2200} onChange={change} className={`${editorInput} mt-1`} /></label>}
              <div className="border-t border-gray-200 pt-4 dark:border-gray-700"><h3 className="font-semibold">Audience & visibility</h3><p className="mt-1 text-xs text-gray-500">Choose who can watch this upload.</p></div>
              {platform !== "instagram" && <label className="block text-sm">Visibility<select required name="privacy" value={options.privacy} onChange={change} className={`${editorInput} mt-1`}><option value="">Choose visibility</option>{(context?.privacy_level_options || []).map(value => <option key={value} value={value} disabled={platform === "tiktok" && options.branded_content && value === "SELF_ONLY"}>{privacyNames[value] || value}</option>)}</select></label>}
              {platform === "youtube" && <label className="block text-sm">Audience<select required name="made_for_kids" value={options.made_for_kids} onChange={change} className={`${editorInput} mt-1`}><option value="">Is this video made for kids?</option><option value="yes">Yes, made for kids</option><option value="no">No, not made for kids</option></select></label>}
              {platform !== "instagram" && check("synthetic", "This video includes realistic altered or AI-generated content")}
              {platform === "instagram" && <><p className="text-sm text-gray-500">This will publish a Reel with your account's audience settings.</p>{check("share_to_feed", "Also share the Reel to my feed")}</>}
              {platform === "tiktok" && <div className="space-y-3">
                {["comment", "duet", "stitch"].map(name => <React.Fragment key={name}>{check(`allow_${name}`, `Allow ${name}${context?.[`${name}_disabled`] ? " (disabled in your TikTok settings)" : ""}`, { disabled: !!context?.[`${name}_disabled`] })}</React.Fragment>)}
                {check("own_brand", "This promotes my own brand or business")}
                {check("branded_content", "This promotes another brand (cannot be private)")}
                {(options.own_brand || options.branded_content) && <p className="text-xs text-gray-500">This video will be labeled {options.branded_content ? "Paid partnership" : "Promotional content"}.</p>}
                {check("music_consent", <span>By posting, I agree to TikTok's <a href="https://www.tiktok.com/legal/page/global/music-usage-confirmation/en" target="_blank" rel="noreferrer" className="text-blue-600 underline">Music Usage Confirmation</a>{options.branded_content && <> and <a href="https://www.tiktok.com/legal/page/global/bc-policy/en" target="_blank" rel="noreferrer" className="text-blue-600 underline">Branded Content Policy</a></>}</span>, { required: true })}
              </div>}
              {check("confirmed", `I reviewed this export and want to upload it to ${account.display_name}.`, { required: true })}
            </>}
          </fieldset>
          {submitted && <p role="status" className="text-sm text-emerald-600">Request saved. Follow its status below. Use Start another post to publish to another account.</p>}
          {submitted && <button type="button" onClick={() => { requestId.current = null; setSubmitted(false); setAccountId(""); }} className="text-sm text-blue-600 underline">Start another post</button>}
        </form>}
        {jobs.length > 0 && <section className="space-y-3" aria-label="Publishing history"><h3 className="font-semibold">Publishing history</h3>{jobs.map(job => <article key={job.id} className="rounded-xl border border-gray-200 p-3 text-sm dark:border-gray-700"><p className="font-medium">{job.platform} · {job.account_name}</p><p role="status" className="mt-1">{statuses[job.status] || job.status}</p>{job.error && <p className="mt-1 text-amber-700 dark:text-amber-400">{job.error}</p>}{job.warning && <p className="mt-1 text-amber-700 dark:text-amber-400">{job.warning}</p>}{job.url && <a href={job.url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-blue-600 underline">View on platform</a>}{(active.has(job.status) || job.status === "NEEDS_CHECK") && <button type="button" disabled={!!busy} onClick={() => refresh(job)} className="ml-3 text-blue-600 underline">Refresh status</button>}</article>)}</section>}
      </div>
    </EditorDialog>
  </>;
}
