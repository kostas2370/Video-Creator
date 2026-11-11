// @vitest-environment happy-dom
// @vitest-environment-options {"settings":{"disableIframePageLoading":true}}
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

vi.mock("../api/apiService", () => ({ searchMusicWithAI: vi.fn(), importSearchMusic: vi.fn(), recommendMusicWithAI: vi.fn() }));
import { searchMusicWithAI, importSearchMusic, recommendMusicWithAI } from "../api/apiService";
import { AIMusicPicker } from "./AIMusicPicker";

const track = { key: "ai:abcdefghijk", title: "Curious piano", channel: "Piano uploader", duration: 120, reason: "Supports the lesson", source_url: "https://www.youtube.com/watch?v=abcdefghijk", license_url: "https://support.google.com/youtube/answer/2797468", attribution: "Credit Piano uploader" };
const result = { brief: { mood: "Curious", instruments: "Piano", tempo: "Medium" }, tracks: [track] };
beforeEach(() => { vi.clearAllMocks(); searchMusicWithAI.mockResolvedValue({ ok: true, data: result }); importSearchMusic.mockResolvedValue({ ok: true }); });
afterEach(cleanup);

it("recommends editable preferences without searching until the user chooses Find music", async () => {
  recommendMusicWithAI.mockResolvedValue({ ok: true, data: { preferences: "Curious, soft piano, medium tempo, no vocals." } });
  render(<AIMusicPicker open onClose={vi.fn()} prompt="Science lesson" onSelected={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Recommend", exact: true }));
  await waitFor(() => expect(screen.getByLabelText("Music preferences (optional)").value).toBe("Curious, soft piano, medium tempo, no vocals."));
  expect(recommendMusicWithAI).toHaveBeenCalledWith(expect.objectContaining({ prompt: "Science lesson" }));
  expect(searchMusicWithAI).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Music preferences (optional)"), { target: { value: "Gentle piano, slower tempo" } });
  fireEvent.click(screen.getByRole("button", { name: "Find music" }));
  await screen.findByText("Curious piano");
  expect(searchMusicWithAI).toHaveBeenCalledWith(expect.objectContaining({ preferences: "Gentle piano, slower tempo" }));
});

it("preserves existing preferences if recommending fails", async () => {
  recommendMusicWithAI.mockResolvedValue({ ok: false, message: "Could not recommend music." });
  render(<AIMusicPicker open onClose={vi.fn()} videoId="video-1" onSaved={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Music preferences (optional)"), { target: { value: "Keep my piano preference" } });
  fireEvent.click(screen.getByRole("button", { name: "Recommend", exact: true }));
  expect((await screen.findByRole("alert")).textContent).toBe("Could not recommend music.");
  expect(screen.getByLabelText("Music preferences (optional)").value).toBe("Keep my piano preference");
  expect(recommendMusicWithAI).toHaveBeenCalledWith(expect.objectContaining({ video_id: "video-1" }));
});

it("shows a music brief and only loads YouTube preview after clicking Preview", async () => {
  render(<AIMusicPicker open onClose={vi.fn()} prompt="Science lesson" onSelected={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Music preferences (optional)"), { target: { value: "No vocals" } });
  fireEvent.click(screen.getByRole("button", { name: "Find music" }));
  await screen.findByText("Curious piano");
  expect(searchMusicWithAI).toHaveBeenCalledWith(expect.objectContaining({ prompt: "Science lesson", preferences: "No vocals" }));
  expect(screen.getByText("Curious · Piano · Medium")).toBeTruthy();
  expect(screen.queryByTitle("Preview Curious piano")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Preview" }));
  expect(screen.getByTitle("Preview Curious piano").getAttribute("src")).toBe("https://www.youtube-nocookie.com/embed/abcdefghijk");
});

it("saves the generation choice without importing or downloading audio", async () => {
  const onSelected = vi.fn(), onClose = vi.fn();
  render(<AIMusicPicker open onClose={onClose} prompt="Science lesson" onSelected={onSelected} />);
  fireEvent.click(screen.getByRole("button", { name: "Find music" }));
  fireEvent.click(await screen.findByRole("button", { name: "Use this music" }));
  expect(onSelected).toHaveBeenCalledWith(track);
  expect(onClose).toHaveBeenCalledOnce();
  expect(importSearchMusic).not.toHaveBeenCalled();
});

it("previews downloaded catalog audio without loading a YouTube player", async () => {
  searchMusicWithAI.mockResolvedValue({ ok: true, data: { ...result, tracks: [{ ...track, key: "catalog:track-1", file: "/media/catalog/piano.wav" }] } });
  render(<AIMusicPicker open onClose={vi.fn()} prompt="Science lesson" onSelected={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Find music" }));
  fireEvent.click(await screen.findByRole("button", { name: "Preview" }));
  expect(document.querySelector("audio").getAttribute("src")).toContain("/media/catalog/piano.wav");
  expect(screen.queryByTitle("Preview Curious piano")).toBeNull();
});

it("imports selected editor music into the current project and refreshes it", async () => {
  const onSaved = vi.fn();
  render(<AIMusicPicker open onClose={vi.fn()} videoId="video-1" onSaved={onSaved} />);
  fireEvent.click(screen.getByRole("button", { name: "Find music" }));
  fireEvent.click(await screen.findByRole("button", { name: "Use this music" }));
  await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
  expect(importSearchMusic).toHaveBeenCalledWith("video-1", "ai:abcdefghijk");
});

it("retains results and displays errors when the selected license is no longer valid", async () => {
  const onSaved = vi.fn(), onClose = vi.fn();
  importSearchMusic.mockResolvedValue({ ok: false, message: "This track is no longer Creative Commons." });
  render(<AIMusicPicker open onClose={onClose} videoId="video-1" onSaved={onSaved} />);
  fireEvent.click(screen.getByRole("button", { name: "Find music" }));
  fireEvent.click(await screen.findByRole("button", { name: "Use this music" }));
  expect((await screen.findByRole("alert")).textContent).toBe("This track is no longer Creative Commons.");
  expect(screen.getByText("Curious piano")).toBeTruthy();
  expect(onSaved).not.toHaveBeenCalled(); expect(onClose).not.toHaveBeenCalled();
});

it("explains search failures instead of presenting empty results as success", async () => {
  searchMusicWithAI.mockResolvedValue({ ok: false, message: "YouTube quota unavailable" });
  render(<AIMusicPicker open onClose={vi.fn()} prompt="Science" onSelected={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Find music" }));
  expect((await screen.findByRole("alert")).textContent).toBe("YouTube quota unavailable");
});
