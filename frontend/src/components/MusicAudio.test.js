// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

vi.mock("../api/apiService", () => ({ uploadMusic: vi.fn(), removeMusic: vi.fn(), updateMusicAudio: vi.fn() }));
vi.mock("./LibraryPicker", () => ({ LibraryPicker: () => null }));
vi.mock("react-toastify", () => ({ toast: { success: vi.fn() } }));
import { uploadMusic } from "../api/apiService";
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
});
