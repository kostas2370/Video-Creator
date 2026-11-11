// @vitest-environment happy-dom
// @vitest-environment-options {"settings":{"disableIframePageLoading":true}}
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

vi.mock("../api/apiService", () => ({ searchMusicWithAI: vi.fn(), importSearchMusic: vi.fn() }));
import { searchMusicWithAI, importSearchMusic } from "../api/apiService";
import { AIMusicPicker } from "./AIMusicPicker";

const track = { key: "ai:abcdefghijk", title: "Curious piano", channel: "Piano uploader", duration: 120, origin: "youtube", reason: "Supports the lesson", source_url: "https://www.youtube.com/watch?v=abcdefghijk", license_url: "https://support.google.com/youtube/answer/2797468", attribution: "Credit Piano uploader" };
const result = { brief: { mood: "Curious", instruments: "Piano", tempo: "Medium" }, tracks: [track] };
beforeEach(() => { vi.clearAllMocks(); searchMusicWithAI.mockResolvedValue({ ok: true, data: result }); importSearchMusic.mockResolvedValue({ ok: true }); });
afterEach(cleanup);

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
