// @vitest-environment happy-dom
import React from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
const stream = vi.hoisted(() => ({ options: null, close: vi.fn() }));
vi.mock("../hooks/useAxiosPrivate", () => ({ useAxiosPrivate: () => ({}) }));
vi.mock("../api/subscribeUpdates", () => ({ subscribeUpdates: vi.fn((path, options) => { stream.options = options; return stream.close; }) }));
vi.mock("../api/apiService", () => ({ searchClipTranscript: vi.fn(), saveClip: vi.fn(), draftClipHashtags: vi.fn(), saveClipHashtags: vi.fn(), getClipProject: vi.fn(), getClip: vi.fn(), getClipProjectProgress: vi.fn(), getClipProjects: vi.fn(), createClipProject: vi.fn(), createClip: vi.fn(), deleteClip: vi.fn(), deleteClipProject: vi.fn(), downloadClip: vi.fn(), exportClips: vi.fn(), retryClipProject: vi.fn() }));
import * as api from "../api/apiService";
import { ClipEditor } from "./ClipEditor";
import { ClipHashtags } from "./ClipHashtags";
import ClipsPage from "../pages/ClipsPage";
import { clipFixture, projectFixture } from "../test/clipsFixtures";

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  api.getClipProject.mockResolvedValue({ ok: true, data: projectFixture() });
  api.getClipProjects.mockResolvedValue({ ok: true, data: { results: [], next: null } });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.useRealTimers(); });

it("reviews generated hashtags before saving and preserves edits after a failed save", async () => {
  const onSaved = vi.fn();
  api.draftClipHashtags.mockResolvedValue({ ok: true, data: { hashtags: ["Interview", "HarryPotter"] } });
  api.saveClipHashtags.mockResolvedValue({ ok: false, message: "Hashtags changed in another session." });
  render(<ClipHashtags projectId="project-1" clip={clipFixture()} onSaved={onSaved} />);
  fireEvent.click(screen.getByText("Hashtags", { exact: true }));
  fireEvent.click(screen.getByRole("button", { name: "Generate hashtags" }));
  await screen.findByText("Review the suggestions, then save.");
  expect(api.saveClipHashtags).not.toHaveBeenCalled();
  const user = userEvent.setup();
  const input = screen.getByLabelText("Hashtags for A useful interview moment");
  await user.clear(input); await user.type(input, "#Interview #MyEdit");
  fireEvent.click(screen.getByRole("button", { name: "Save hashtags" }));
  await screen.findByRole("alert");
  expect(input.value).toBe("#Interview #MyEdit");
  expect(api.saveClipHashtags).toHaveBeenCalledWith("project-1", "clip-1", ["Interview", "MyEdit"], []);
  expect(onSaved).not.toHaveBeenCalled();
});

it("rebases captions after trimming and keeps unsaved edits when saving fails", async () => {
  api.saveClip.mockResolvedValue({ ok: false, message: "Reload before saving; your edits are still here." });
  render(<ClipEditor project={projectFixture()} clip={clipFixture()} onSaved={vi.fn()} onClose={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Start (minutes)"), { target: { value: String(2 / 60) } });
  fireEvent.change(screen.getByLabelText("Clip title"), { target: { value: "My edited title" } });
  fireEvent.submit(screen.getByRole("button", { name: "Save clip", exact: true }).closest("form"));
  await screen.findByRole("alert");
  const changes = api.saveClip.mock.calls[0][2];
  expect(changes.start).toBe(2);
  expect(changes.words[0]).toEqual({ text: "Word2", start: 0, end: 0.8 });
  expect(screen.getByLabelText("Clip title").value).toBe("My edited title");
});

it("reconciles server events without overwriting an open editor or polling the full transcript", async () => {
  render(<MemoryRouter initialEntries={["/clips/project-1/"]}><Routes><Route path="/clips/:projectId/" element={<ClipsPage />} /></Routes></MemoryRouter>);
  await screen.findByRole("heading", { name: "Interview", exact: true });
  fireEvent.click(screen.getByRole("button", { name: "Preview & edit" }));
  fireEvent.change(screen.getByLabelText("Clip title"), { target: { value: "My unsaved edit" } });
  const updated = clipFixture({ title: "Remote update", revision: "new-revision" });
  api.getClip.mockResolvedValue({ ok: true, data: updated });
  await act(async () => { await stream.options.onUpdate({ id: "project-1", status: "READY", has_transcript: true, clips: [{ id: updated.id, revision: updated.revision, status: "READY", hashtags: [] }] }); });
  await screen.findByRole("heading", { name: "Remote update" });
  expect(screen.getByLabelText("Clip title").value).toBe("My unsaved edit");
  expect(api.getClip).toHaveBeenCalledTimes(1);
  const fullLoads = api.getClipProject.mock.calls.length;
  vi.useFakeTimers();
  await act(async () => { vi.advanceTimersByTime(15000); });
  expect(api.getClipProject).toHaveBeenCalledTimes(fullLoads);
  vi.useRealTimers();
  cleanup(); expect(stream.close).toHaveBeenCalled();
});

it("submits a YouTube link and optional extraction brief without requiring a file", async () => {
  api.createClipProject.mockResolvedValue({ ok: true, data: { id: "imported" } });
  render(<MemoryRouter initialEntries={["/clips/"]}><Routes><Route path="/clips/" element={<ClipsPage />} /><Route path="/clips/:projectId/" element={<p>Source saved</p>} /></Routes></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", { name: "New project", exact: true }));
  fireEvent.click(screen.getByRole("button", { name: "YouTube link", exact: true }));
  fireEvent.change(screen.getByLabelText(/YouTube video link/), { target: { value: "https://youtu.be/abcdefghijk" } });
  fireEvent.change(screen.getByPlaceholderText(/practical business advice/), { target: { value: "Funny moments" } });
  fireEvent.change(screen.getByLabelText("Clip focus"), { target: { value: "funny" } });
  fireEvent.change(screen.getByLabelText("Selection mode"), { target: { value: "fast" } });
  expect(screen.getByText(/without an extra ranking review/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Find short clips" }));
  await waitFor(() => expect(api.createClipProject).toHaveBeenCalledTimes(1));
  const data = api.createClipProject.mock.calls[0][0];
  expect(data.get("youtube_url")).toBe("https://youtu.be/abcdefghijk");
  expect(data.get("extraction_prompt")).toBe("Funny moments");
  expect(data.get("clip_focus")).toBe("funny");
  expect(data.get("selection_mode")).toBe("fast");
  expect(data.has("source")).toBe(false);
  expect(data.has("range_end")).toBe(false);
  expect(data.get("min_duration")).toBe("30");
  expect(data.get("max_duration")).toBe("60");
  await screen.findByText("Source saved");
});

it("saves clip and caption timestamps with more than three decimal places", async () => {
  const onSaved = vi.fn();
  api.saveClip.mockResolvedValue({ ok: true, data: clipFixture() });
  const clip = clipFixture({ start: 0.1234, end: 12.1234, words: [{ text: "Hello", start: 0.0001, end: 0.5678 }] });
  render(<ClipEditor project={projectFixture()} clip={clip} onSaved={onSaved} onClose={vi.fn()} />);
  await userEvent.click(screen.getByRole("button", { name: "Save clip", exact: true }));
  await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
  expect(api.saveClip.mock.calls[0][2].start).toBe(0.1234);
});

it("switches clip editors without losing drafts and closes after a successful save", async () => {
  const second = clipFixture({ id: "clip-2", title: "Second moment" });
  api.getClipProject.mockResolvedValue({ ok: true, data: projectFixture({ clips: [clipFixture(), second] }) });
  api.saveClip.mockResolvedValue({ ok: true, data: clipFixture({ title: "My draft" }) });
  render(<MemoryRouter initialEntries={["/clips/project-1/"]}><Routes><Route path="/clips/:projectId/" element={<ClipsPage />} /></Routes></MemoryRouter>);
  await screen.findByRole("heading", { name: "Second moment" });
  await userEvent.click(screen.getAllByRole("button", { name: "Preview & edit" })[0]);
  fireEvent.change(screen.getByLabelText("Clip title"), { target: { value: "My draft" } });
  await userEvent.click(screen.getAllByRole("button", { name: "Preview & edit" })[1]);
  expect(screen.getByLabelText("Clip title").value).toBe("Second moment");
  await userEvent.click(screen.getAllByRole("button", { name: "Preview & edit" })[0]);
  expect(screen.getByLabelText("Clip title").value).toBe("My draft");
  await userEvent.click(screen.getByRole("button", { name: "Save clip", exact: true }));
  await waitFor(() => expect(screen.queryByRole("region", { name: "Clip editor" })).toBeNull());
  await userEvent.click(screen.getAllByRole("button", { name: "Preview & edit" })[1]);
  expect(screen.getByLabelText("Clip title").value).toBe("Second moment");
});

it("submits the optional source range alongside a YouTube import", async () => {
  api.createClipProject.mockResolvedValue({ ok: true, data: { id: "imported" } });
  render(<MemoryRouter initialEntries={["/clips/"]}><Routes><Route path="/clips/" element={<ClipsPage />} /><Route path="/clips/:projectId/" element={<p>Source saved</p>} /></Routes></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", { name: "New project", exact: true }));
  fireEvent.click(screen.getByRole("button", { name: "YouTube link", exact: true }));
  fireEvent.change(screen.getByLabelText(/YouTube video link/), { target: { value: "https://youtu.be/abcdefghijk" } });
  expect(screen.getByLabelText("Process until (minutes)").hasAttribute("max")).toBe(false);
  fireEvent.change(screen.getByLabelText("Process from (minutes)"), { target: { value: "130" } });
  fireEvent.change(screen.getByLabelText("Process until (minutes)"), { target: { value: "180" } });
  fireEvent.change(screen.getByLabelText("Minimum clip length (minutes)"), { target: { value: "0.75" } });
  fireEvent.change(screen.getByLabelText("Maximum clip length (minutes)"), { target: { value: "1.5" } });
  fireEvent.click(screen.getByRole("button", { name: "Find short clips" }));
  await waitFor(() => expect(api.createClipProject).toHaveBeenCalledTimes(1));
  const data = api.createClipProject.mock.calls[0][0];
  expect(data.get("range_start")).toBe("7800");
  expect(data.get("range_end")).toBe("10800");
  expect(data.get("min_duration")).toBe("45");
  expect(data.get("max_duration")).toBe("90");
  expect(data.get("clip_focus")).toBe("general");
  expect(data.get("selection_mode")).toBe("balanced");
});

it("explains strict selection and shows saved preferences in the project", async () => {
  render(<MemoryRouter initialEntries={["/clips/"]}><Routes><Route path="/clips/" element={<ClipsPage />} /></Routes></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", { name: "New project", exact: true }));
  fireEvent.change(screen.getByLabelText("Selection mode"), { target: { value: "strict" } });
  expect(screen.getByText(/May return fewer clips or none/)).toBeTruthy();
  cleanup();
  api.getClipProject.mockResolvedValue({ ok: true, data: projectFixture({ clip_focus: "stories", selection_mode: "strict" }) });
  render(<MemoryRouter initialEntries={["/clips/project-1/"]}><Routes><Route path="/clips/:projectId/" element={<ClipsPage />} /></Routes></MemoryRouter>);
  await screen.findByText(/Stories · Strict selection/);
});

it("finds clips by a natural-language request and only creates the chosen result", async () => {
  api.searchClipTranscript.mockResolvedValue({ ok: true, data: { clips: [{ title: "Business advice", reason: "Explains how to start", start: 2, end: 14.8 }] } });
  api.createClip.mockResolvedValue({ ok: true, data: clipFixture({ id: "clip-found", title: "Business advice", start: 2, end: 14.8 }) });
  render(<MemoryRouter initialEntries={["/clips/project-1/"]}><Routes><Route path="/clips/:projectId/" element={<ClipsPage />} /></Routes></MemoryRouter>);
  await screen.findByText("Full video transcript");
  await userEvent.click(screen.getByRole("button", { name: "Transcript & AI search" }));
  fireEvent.change(screen.getByLabelText("Describe the moment you want"), { target: { value: "Find advice for starting a business" } });
  await userEvent.click(screen.getByRole("button", { name: "Find matching clips" }));
  await screen.findByRole("heading", { name: "Business advice" });
  expect(api.searchClipTranscript).toHaveBeenCalledWith("project-1", "Find advice for starting a business");
  expect(api.createClip).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: "Add and edit clip" }));
  await waitFor(() => expect(screen.getByLabelText("Clip title").value).toBe("Business advice"));
  expect(api.createClip).toHaveBeenCalledWith("project-1", { title: "Business advice", start: 2, end: 14.8 });
});

it("keeps the AI search query after failure and explains when there are no matches", async () => {
  api.searchClipTranscript.mockResolvedValueOnce({ ok: false, message: "Provider unavailable" }).mockResolvedValueOnce({ ok: true, data: { clips: [] } });
  render(<MemoryRouter initialEntries={["/clips/project-1/"]}><Routes><Route path="/clips/:projectId/" element={<ClipsPage />} /></Routes></MemoryRouter>);
  await screen.findByText("Full video transcript");
  await userEvent.click(screen.getByRole("button", { name: "Transcript & AI search" }));
  fireEvent.change(screen.getByLabelText("Describe the moment you want"), { target: { value: "Unusual story" } });
  await userEvent.click(screen.getByRole("button", { name: "Find matching clips" }));
  await screen.findByText("Provider unavailable");
  expect(screen.getByLabelText("Describe the moment you want").value).toBe("Unusual story");
  await userEvent.click(screen.getByRole("button", { name: "Find matching clips" }));
  await screen.findByText(/No matching moments found/);
});

it("keeps an unsaved clip draft when switching between workspace views", async () => {
  render(<MemoryRouter initialEntries={["/clips/project-1/"]}><Routes><Route path="/clips/:projectId/" element={<ClipsPage />} /></Routes></MemoryRouter>);
  await screen.findByRole("heading", { name: "Review your clips" });
  await userEvent.click(screen.getByRole("button", { name: "Preview & edit" }));
  fireEvent.change(screen.getByLabelText("Clip title"), { target: { value: "Keep this draft" } });
  await userEvent.click(screen.getByRole("button", { name: "Transcript & AI search" }));
  expect(screen.getByRole("button", { name: "Transcript & AI search" }).getAttribute("aria-pressed")).toBe("true");
  await userEvent.click(screen.getByRole("button", { name: /^Clips/ }));
  expect(screen.getByLabelText("Clip title").value).toBe("Keep this draft");
});

it("opens on the project library and keeps creation behind New project", async () => {
  api.getClipProjects.mockResolvedValue({ ok: true, data: { count: 1, results: [{ id: "project-1", title: "Interview", status: "READY", duration: 1200, clip_total: 4, export_total: 2 }], next: null } });
  render(<MemoryRouter initialEntries={["/clips/"]}><Routes><Route path="/clips/" element={<ClipsPage />} /></Routes></MemoryRouter>);
  await screen.findByRole("heading", { name: "Interview" });
  expect(screen.queryByLabelText("Source video")).toBeNull();
  expect(screen.getByRole("link", { name: /Interview/ }).textContent).toContain("4clips");
  await userEvent.click(screen.getByRole("button", { name: "New project" }));
  expect(screen.getByLabelText("Source video")).toBeTruthy();
  await userEvent.click(screen.getByRole("button", { name: "Back to projects" }));
  expect(screen.getByLabelText("Search projects")).toBeTruthy();
});

it("searches and filters projects through the server", async () => {
  render(<MemoryRouter initialEntries={["/clips/"]}><Routes><Route path="/clips/" element={<ClipsPage />} /></Routes></MemoryRouter>);
  fireEvent.change(screen.getByLabelText("Search projects"), { target: { value: "Podcast" } });
  fireEvent.change(screen.getByLabelText("Status"), { target: { value: "READY" } });
  await waitFor(() => expect(api.getClipProjects).toHaveBeenLastCalledWith(1, { search: "Podcast", status: "READY" }));
});

it("saves and clears the manual uploaded marker without changing export details", async () => {
  const original = clipFixture({ status: "COMPLETED", output: "/api/clips/output/" });
  api.getClipProject.mockResolvedValue({ ok: true, data: projectFixture({ clips: [original] }) });
  api.saveClip.mockImplementation(async (projectId, clipId, changes) => {
    const updated = { ...original, uploaded: changes.uploaded, revision: changes.uploaded ? "marked" : "cleared" };
    api.getClipProject.mockResolvedValue({ ok: true, data: projectFixture({ clips: [updated] }) });
    return { ok: true, data: updated };
  });
  render(<MemoryRouter initialEntries={["/clips/project-1/"]}><Routes><Route path="/clips/:projectId/" element={<ClipsPage />} /></Routes></MemoryRouter>);
  const marker = await screen.findByRole("checkbox", { name: `Uploaded ${original.title}` });
  expect(marker.checked).toBe(false);
  await userEvent.click(marker);
  await waitFor(() => expect(marker.checked).toBe(true));
  expect(api.saveClip).toHaveBeenLastCalledWith("project-1", original.id, { uploaded: true, revision: original.revision });
  expect(screen.getByRole("button", { name: "Download" })).toBeTruthy();
  await userEvent.click(marker);
  await waitFor(() => expect(marker.checked).toBe(false));
  expect(api.saveClip).toHaveBeenLastCalledWith("project-1", original.id, { uploaded: false, revision: "marked" });
});

it("keeps the saved uploaded marker unchanged when saving fails", async () => {
  api.saveClip.mockResolvedValue({ ok: false, message: "Could not save uploaded marker." });
  render(<MemoryRouter initialEntries={["/clips/project-1/"]}><Routes><Route path="/clips/:projectId/" element={<ClipsPage />} /></Routes></MemoryRouter>);
  const marker = await screen.findByRole("checkbox", { name: "Uploaded A useful interview moment" });
  await userEvent.click(marker);
  expect((await screen.findByRole("alert")).textContent).toBe("Could not save uploaded marker.");
  expect(marker.checked).toBe(false);
});


it("keeps the final preview time visible and restarts when replaying", () => {
  const { container } = render(<ClipEditor project={projectFixture()} clip={clipFixture()} onSaved={vi.fn()} onClose={vi.fn()} />);
  const video = container.querySelector("video:not([aria-hidden])");
  video.currentTime = 12.2;
  fireEvent.timeUpdate(video);
  expect(video.currentTime).toBe(12);
  expect(screen.getByText("0:12 / 0:12")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Play", exact: true }));
  expect(video.currentTime).toBe(0);
  expect(video.play).toHaveBeenCalled();
});

it("shows End of video while a YouTube duration is unknown and updates from progress", async () => {
  const pending = projectFixture({ status: "DOWNLOADING", duration: 0, range_start: 7800, range_end: null, words: [], clips: [] });
  api.getClipProject.mockResolvedValue({ ok: true, data: pending });
  render(<MemoryRouter initialEntries={["/clips/project-1/"]}><Routes><Route path="/clips/:projectId/" element={<ClipsPage />} /></Routes></MemoryRouter>);
  await screen.findByText(/Processing range: 130:00–End of video/);
  expect(screen.getByText("Source duration pending…")).toBeTruthy();
  await act(async () => stream.options.onUpdate({ ...pending, duration: 10800, status: "TRANSCRIBING", has_transcript: false }));
  expect(screen.getByText(/Processing range: 130:00–180:00/)).toBeTruthy();
});
