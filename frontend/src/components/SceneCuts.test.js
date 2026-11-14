// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
vi.mock("../api/apiService", () => ({ getVideoPreview: vi.fn(), updateSceneCuts: vi.fn(), updateVideoCuts: vi.fn() }));
import { getVideoPreview, updateSceneCuts, updateVideoCuts } from "../api/apiService";
import { SceneCuts, VideoCuts } from "./SceneCuts";
const scene = { id: "scene", cuts: {}, timing: { duration: 10 } };
const video = { id: "video", status: "READY", scenes: [scene] };
afterEach(() => { cleanup(); vi.clearAllMocks(); });
it("splits, removes, undoes and saves main-editor cuts while preserving a failed save", async () => {
  getVideoPreview.mockResolvedValue({ ok: true, data: { size: [160, 90], duration: 10, captions: [], segments: [{ id: "scene", kind: "scene", start: 0, duration: 10, base_duration: 10, label: "Scene 1" }] } });
  updateSceneCuts.mockResolvedValueOnce({ ok: false, message: "Please retry" }).mockResolvedValueOnce({ ok: true });
  const onSaved = vi.fn();
  render(<SceneCuts scene={scene} video={video} index={0} onSaved={onSaved} />);
  fireEvent.click(screen.getByRole("button", { name: "Cut scene", exact: true }));
  const slider = await screen.findByLabelText("Preview playhead");
  await waitFor(() => expect(slider.max).toBe("10"));
  fireEvent.change(slider, { target: { value: "2" } });
  fireEvent.click(screen.getByRole("button", { name: "Split at playhead" }));
  fireEvent.change(slider, { target: { value: "6" } });
  fireEvent.click(screen.getByRole("button", { name: "Split at playhead" }));
  fireEvent.click(screen.getByRole("button", { name: /Section 2/ }));
  fireEvent.click(screen.getByRole("button", { name: "Remove selected section" }));
  expect(slider.max).toBe("6");
  fireEvent.click(screen.getByRole("button", { name: "Undo cut" }));
  expect(slider.max).toBe("10");
  fireEvent.click(screen.getByRole("button", { name: /Section 2/ }));
  fireEvent.click(screen.getByRole("button", { name: "Remove selected section" }));
  fireEvent.click(screen.getByRole("button", { name: "Save cuts" }));
  expect((await screen.findByRole("alert")).textContent).toBe("Please retry");
  expect(slider.max).toBe("6");
  expect(updateSceneCuts).toHaveBeenLastCalledWith("scene", { source_duration: 10, previous: {}, sections: [{ start: 0, end: 2 }, { start: 6, end: 10 }] });
  fireEvent.click(screen.getByRole("button", { name: "Save cuts" }));
  await waitFor(() => expect(onSaved).toHaveBeenCalled());
});

it("keeps the playhead on a split and supports frame stepping, keyboard cuts, undo and redo", async () => {
  getVideoPreview.mockResolvedValue({ ok: true, data: { size: [160, 90], duration: 10, captions: [], segments: [{ id: "scene", kind: "scene", start: 0, duration: 10, base_duration: 10, label: "Scene 1" }] } });
  render(<SceneCuts scene={scene} video={video} index={0} onSaved={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Cut scene", exact: true }));
  const timeline = await screen.findByRole("slider", { name: "Cut timeline playhead" });
  const slider = screen.getByLabelText("Preview playhead");
  fireEvent.change(slider, { target: { value: "2" } });
  fireEvent.keyDown(timeline, { key: "s" });
  expect(slider.value).toBe("2");
  expect(screen.getByRole("button", { name: /Section 2,/ }).getAttribute("aria-pressed")).toBe("true");
  fireEvent.keyDown(timeline, { key: "ArrowRight" });
  expect(Number(slider.value)).toBeCloseTo(2 + 1 / 24);
  fireEvent.keyDown(timeline, { key: "Delete" });
  expect(slider.max).toBe("2");
  fireEvent.keyDown(timeline, { key: "z", ctrlKey: true });
  expect(slider.max).toBe("10");
  fireEvent.keyDown(timeline, { key: "z", ctrlKey: true, shiftKey: true });
  expect(slider.max).toBe("2");
  fireEvent.click(screen.getByRole("button", { name: "Undo cut" }));
  fireEvent.click(screen.getByRole("button", { name: "Restore full scene" }));
  expect(slider.max).toBe("10");
  expect(screen.queryByRole("button", { name: /Section 2,/ })).toBeNull();
});

it("cuts across the full video, composes existing scene cuts, and preserves failed saves", async () => {
  const manifest = { size: [160, 90], duration: 10, captions: [], cut_source: { duration: 8, key: "source-key", sections: [{ start: 2, end: 5 }, { start: 5, end: 10 }] }, segments: [
    { id: "first", kind: "scene", start: 0, duration: 5, base_duration: 5, label: "Scene 1" },
    { id: "second", kind: "scene", start: 5, duration: 5, base_duration: 5, label: "Scene 2" },
  ] };
  getVideoPreview.mockResolvedValue({ ok: true, data: manifest });
  updateVideoCuts.mockResolvedValueOnce({ ok: false, message: "Timeline changed" }).mockResolvedValueOnce({ ok: true });
  const onSaved = vi.fn();
  render(<VideoCuts video={{ ...video, cuts: {} }} onSaved={onSaved} />);
  fireEvent.click(screen.getByRole("button", { name: "Cut video", exact: true }));
  const slider = await screen.findByLabelText("Preview playhead");
  await waitFor(() => expect(slider.max).toBe("8"));
  expect(screen.getByLabelText("Scenes in cut").textContent).toContain("Scene 2");
  fireEvent.change(slider, { target: { value: "4" } });
  fireEvent.click(screen.getByRole("button", { name: "Split at playhead" }));
  fireEvent.click(screen.getByRole("button", { name: /Section 1,/ }));
  fireEvent.click(screen.getByRole("button", { name: "Remove selected section" }));
  expect(slider.max).toBe("4");
  fireEvent.click(screen.getByRole("button", { name: "Save cuts" }));
  expect((await screen.findByRole("alert")).textContent).toBe("Timeline changed");
  expect(updateVideoCuts).toHaveBeenLastCalledWith("video", { source_duration: 8, source_key: "source-key", previous: {}, sections: [{ start: 4, end: 8 }] });
  expect(updateSceneCuts).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Restore full video" }));
  expect(slider.max).toBe("8");
  fireEvent.click(screen.getByRole("button", { name: "Save cuts" }));
  await waitFor(() => expect(onSaved).toHaveBeenCalled());
});
it("warns about obsolete video cuts and keeps the button available after a loading failure", async () => {
  getVideoPreview.mockResolvedValueOnce({ ok: false, message: "Please retry" }).mockResolvedValueOnce({ ok: true, data: { size: [160, 90], duration: 10, captions: [], cuts_stale: true, cut_source: { duration: 10, key: "new", sections: [{ start: 0, end: 10 }] }, segments: [{ id: "scene", start: 0, duration: 10, base_duration: 10, label: "Scene 1" }] } });
  render(<VideoCuts video={{ ...video, cuts: { source_key: "old", sections: [{ start: 1, end: 2 }] } }} />);
  fireEvent.click(screen.getByRole("button", { name: "Cut video", exact: true }));
  expect((await screen.findByRole("alert")).textContent).toBe("Please retry");
  fireEvent.click(screen.getByRole("button", { name: "Cut video", exact: true }));
  const slider = await screen.findByLabelText("Preview playhead");
  await waitFor(() => expect(slider.max).toBe("10"));
  expect(screen.getByText(/timeline changed since the last full-video cut/)).toBeTruthy();
});
