// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

vi.mock("../api/apiService", () => ({ uploadMusic: vi.fn(), removeMusic: vi.fn(), updateMusicAudio: vi.fn(), autoSelectMusic: vi.fn() }));
vi.mock("./LibraryPicker", () => ({ LibraryPicker: () => null }));
vi.mock("react-toastify", () => ({ toast: { success: vi.fn() } }));
import { uploadMusic, autoSelectMusic } from "../api/apiService";
import { toast } from "react-toastify";
import { MusicAudio } from "./MusicAudio";

beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

it("imports a YouTube link and refreshes the editor after saving", async () => {
  const onSaved = vi.fn();
  uploadMusic.mockResolvedValue({ ok: true });
  render(<MusicAudio video={{ id: "video-1", music: "Current song" }} onSaved={onSaved} />);
  fireEvent.click(screen.getByRole("button", { name: "From YouTube" }));
  fireEvent.change(screen.getByLabelText("YouTube link"), { target: { value: "https://youtu.be/abcdefghijk" } });
  fireEvent.click(screen.getByRole("button", { name: "Use this music" }));
  await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
  expect(uploadMusic.mock.calls[0][0]).toBe("video-1");
  expect(uploadMusic.mock.calls[0][1].get("youtube_url")).toBe("https://youtu.be/abcdefghijk");
  expect(uploadMusic.mock.calls[0][1].has("file")).toBe(false);
  expect(toast.success).toHaveBeenCalledWith("Music added and saved to library");
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
});

it("keeps the link and current song visible when an import fails", async () => {
  const onSaved = vi.fn();
  uploadMusic.mockResolvedValue({ ok: false, message: "This audio is unavailable." });
  render(<MusicAudio video={{ id: "video-1", music: "Current song" }} onSaved={onSaved} />);
  fireEvent.click(screen.getByRole("button", { name: "From YouTube" }));
  fireEvent.change(screen.getByLabelText("YouTube link"), { target: { value: "https://youtu.be/abcdefghijk" } });
  fireEvent.click(screen.getByRole("button", { name: "Use this music" }));
  expect((await screen.findByRole("alert")).textContent).toBe("This audio is unavailable.");
  expect(screen.getByLabelText("YouTube link").value).toBe("https://youtu.be/abcdefghijk");
  expect(screen.getByText("Current song")).toBeTruthy();
  expect(onSaved).not.toHaveBeenCalled();
});

it("disables link imports while editing is locked", () => {
  render(<MusicAudio video={{ id: "video-1" }} disabled onSaved={vi.fn()} />);
  expect(screen.getByRole("button", { name: "From YouTube" }).disabled).toBe(true);
  expect(screen.getByRole("button", { name: "Auto-select music" }).disabled).toBe(true);
});

it("automatically selects catalog music and refreshes the editor", async () => {
  const onSaved = vi.fn();
  autoSelectMusic.mockResolvedValue({ ok: true, data: { track: { title: "Calm piano" } } });
  render(<MusicAudio video={{ id: "video-1" }} onSaved={onSaved} />);
  fireEvent.click(screen.getByRole("button", { name: "Auto-select music" }));
  await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
  expect(autoSelectMusic).toHaveBeenCalledWith("video-1");
  expect(toast.success).toHaveBeenCalledWith("Music selected: Calm piano");
});

it("keeps the existing music and explains failed automatic selection", async () => {
  const onSaved = vi.fn();
  autoSelectMusic.mockResolvedValue({ ok: false, message: "No general music is available yet." });
  render(<MusicAudio video={{ id: "video-1", music: "Current song" }} onSaved={onSaved} />);
  fireEvent.click(screen.getByRole("button", { name: "Auto-select music" }));
  expect((await screen.findByRole("alert")).textContent).toBe("No general music is available yet.");
  expect(screen.getByText("Current song")).toBeTruthy();
  expect(onSaved).not.toHaveBeenCalled();
});

it("shows track metadata, an on-demand preview and saved attribution", () => {
  render(<MusicAudio video={{ id: "video", music: "f22e597b-8bd7-4aa4-801d-ca4f25ebcaf9", music_details: { title: "Quiet morning", artist: "Piano artist", file: "/media/music/song.mp3", source_url: "https://example.test/song", license_url: "https://example.test/license", attribution: "Credit Piano artist" } }} onSaved={vi.fn()} />);
  expect(screen.getByText("Quiet morning")).toBeTruthy();
  expect(screen.getByText("Piano artist")).toBeTruthy();
  const audio = screen.getByLabelText("Preview soundtrack: Quiet morning");
  expect(audio.getAttribute("preload")).toBe("none");
  expect(audio.getAttribute("src")).toBe("/media/music/song.mp3");
  expect(screen.getByRole("link", { name: "License information", hidden: true }).getAttribute("href")).toBe("https://example.test/license");
  expect(screen.queryByText("f22e597b-8bd7-4aa4-801d-ca4f25ebcaf9")).toBeNull();
});

it("explains missing license metadata without exposing the music identifier", () => {
  render(<MusicAudio video={{ id: "video", music: "f22e597b-8bd7-4aa4-801d-ca4f25ebcaf9" }} onSaved={vi.fn()} />);
  expect(screen.getByText("Selected soundtrack")).toBeTruthy();
  expect(screen.getByText(/No license information saved/)).toBeTruthy();
});
