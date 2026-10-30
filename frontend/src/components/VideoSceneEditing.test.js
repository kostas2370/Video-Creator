// @vitest-environment happy-dom
import React from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SceneTextEditor } from "./SceneTextEditor";
vi.mock("../api/apiService", () => ({ getVideo: vi.fn(), updateScene: vi.fn(), generateScene: vi.fn() }));
vi.mock("../api/subscribeUpdates", () => ({ subscribeUpdates: (_, { load, onUpdate }) => { let active = true; load().then(result => { if (active && result.ok) onUpdate(result.data); }); return () => { active = false; }; } }));
vi.mock("react-toastify", () => ({ toast: { success: vi.fn(), warning: vi.fn(), error: vi.fn() } }));
vi.mock("./Scene", () => ({ Scene: ({ scene, index, textDraft, onTextDraftChange, onTextSave, onTextRewrite, timingDisabled }) => <SceneTextEditor scene={scene} index={index} draft={textDraft} onDraftChange={onTextDraftChange} onSave={onTextSave} onRewrite={onTextRewrite} disabled={timingDisabled} /> }));
vi.mock("./MusicAudio", () => ({ MusicAudio: () => null }));
vi.mock("./VideoNotes", () => ({ VideoNotes: () => null }));
vi.mock("./RecentlyDeletedScenes", () => ({ RecentlyDeletedScenes: () => null }));
vi.mock("./PublishVideo", () => ({ PublishVideo: () => null }));
vi.mock("./VideoDetails", () => ({ VideoDetails: () => null }));
import * as api from "../api/apiService";
import { Video } from "../pages/VideoPage";
let project;
beforeEach(() => {
  vi.clearAllMocks(); localStorage.clear(); sessionStorage.clear();
  project = { id: "video-1", title: "Sample project", status: "READY", video_type: "AI", settings: { video_format: "LANDSCAPE" }, extra_duration: 0, scenes: [{ id: "first", video: "video-1", position: 1, text: "Original", narration_status: "available", timing: { duration: 3 }, audio_settings: {} }] };
  api.getVideo.mockImplementation(async () => ({ ok: true, data: project }));
});
afterEach(cleanup);
function openEditor() {
  render(<MemoryRouter initialEntries={["/videos/video-1/"]}><Routes><Route path="/videos/:videoId/" element={<Video />} /></Routes></MemoryRouter>);
}
it("saves inline through the existing scene API and locks export until it completes", async () => {
  let complete;
  api.updateScene.mockImplementation(() => new Promise(resolve => { complete = resolve; }));
  openEditor();
  const input = await screen.findByLabelText("Script for scene 1");
  fireEvent.change(input, { target: { value: "Updated script" } });
  fireEvent.click(screen.getByRole("button", { name: "Save text" }));
  expect(api.updateScene).toHaveBeenCalledWith("first", { text: "Updated script" });
  expect(screen.getByRole("button", { name: "Export video" }).disabled).toBe(true);
  await act(async () => {
    project = { ...project, scenes: [{ ...project.scenes[0], text: "Updated script" }] };
    complete({ ok: true, data: project.scenes[0] });
  });
  await waitFor(() => expect(screen.getByRole("button", { name: "Export video" }).disabled).toBe(false));
  expect(screen.getByLabelText("Script for scene 1").value).toBe("Updated script");
  expect(screen.queryByRole("button", { name: "Discard changes" })).toBeNull();
});
it("keeps a generated rewrite as an unsaved draft without calling the update API", async () => {
  api.generateScene.mockResolvedValue({ ok: true, data: { text: "Suggested rewrite" } });
  openEditor();
  await screen.findByLabelText("Script for scene 1");
  fireEvent.click(screen.getByText("Rewrite with AI"));
  fireEvent.change(screen.getByLabelText("Rewrite instructions"), { target: { value: "Shorten it" } });
  fireEvent.click(screen.getByRole("button", { name: "Generate rewrite" }));
  await waitFor(() => expect(screen.getByLabelText("Script for scene 1").value).toBe("Suggested rewrite"));
  expect(api.generateScene).toHaveBeenCalledWith("first", { text: "Shorten it" });
  expect(api.updateScene).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Save text" }).disabled).toBe(false);
});
