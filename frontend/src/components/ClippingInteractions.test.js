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
  fireEvent.change(screen.getByLabelText("Start (seconds)"), { target: { value: "2" } });
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
  fireEvent.click(screen.getByRole("button", { name: "YouTube link", exact: true }));
  fireEvent.change(screen.getByLabelText(/YouTube video link/), { target: { value: "https://youtu.be/abcdefghijk" } });
  fireEvent.change(screen.getByPlaceholderText(/practical business advice/), { target: { value: "Funny moments" } });
  fireEvent.click(screen.getByRole("button", { name: "Find short clips" }));
  await waitFor(() => expect(api.createClipProject).toHaveBeenCalledTimes(1));
  const data = api.createClipProject.mock.calls[0][0];
  expect(data.get("youtube_url")).toBe("https://youtu.be/abcdefghijk");
  expect(data.get("extraction_prompt")).toBe("Funny moments");
  expect(data.has("source")).toBe(false);
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
  fireEvent.click(screen.getByRole("button", { name: "YouTube link", exact: true }));
  fireEvent.change(screen.getByLabelText(/YouTube video link/), { target: { value: "https://youtu.be/abcdefghijk" } });
  fireEvent.change(screen.getByLabelText("Process from (seconds)"), { target: { value: "600" } });
  fireEvent.change(screen.getByLabelText("Process until (seconds)"), { target: { value: "1800" } });
  fireEvent.click(screen.getByRole("button", { name: "Find short clips" }));
  await waitFor(() => expect(api.createClipProject).toHaveBeenCalledTimes(1));
  const data = api.createClipProject.mock.calls[0][0];
  expect(data.get("range_start")).toBe("600");
  expect(data.get("range_end")).toBe("1800");
});

it("finds clips by a natural-language request and only creates the chosen result", async () => {
  api.searchClipTranscript.mockResolvedValue({ ok: true, data: { clips: [{ title: "Business advice", reason: "Explains how to start", start: 2, end: 14.8 }] } });
  api.createClip.mockResolvedValue({ ok: true, data: clipFixture({ id: "clip-found", title: "Business advice", start: 2, end: 14.8 }) });
  render(<MemoryRouter initialEntries={["/clips/project-1/"]}><Routes><Route path="/clips/:projectId/" element={<ClipsPage />} /></Routes></MemoryRouter>);
  await screen.findByText("Full video transcript");
  fireEvent.click(screen.getByText("Full video transcript"));
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
  fireEvent.click(screen.getByText("Full video transcript"));
  fireEvent.change(screen.getByLabelText("Describe the moment you want"), { target: { value: "Unusual story" } });
  await userEvent.click(screen.getByRole("button", { name: "Find matching clips" }));
  await screen.findByText("Provider unavailable");
  expect(screen.getByLabelText("Describe the moment you want").value).toBe("Unusual story");
  await userEvent.click(screen.getByRole("button", { name: "Find matching clips" }));
  await screen.findByText(/No matching moments found/);
});
