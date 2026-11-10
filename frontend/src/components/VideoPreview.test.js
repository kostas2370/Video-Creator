// @vitest-environment happy-dom
import React from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { VideoPreview, Visual } from "./VideoPreview";

vi.mock("../api/apiService", () => ({ getVideoPreview: vi.fn() }));
import { getVideoPreview } from "../api/apiService";

vi.mock("./PhotoAnimationLayer", () => ({ PhotoAnimationLayer: () => <span>Particles</span> }));
vi.mock("./OverlayLayer", () => ({ OverlayLayer: ({ time, duration }) => <span>{time < duration ? "Diagram" : "Expired diagram"}</span> }));
afterEach(cleanup);

it("fades the complete scene including particles and diagrams without a photo", () => {
  const { container } = render(<Visual segment={{ duration: 2 }} size={[160, 90]} time={1} opacity={0.5} />);
  expect(container.firstChild.style.opacity).toBe("0.5");
  expect(container.firstChild.contains(screen.getByText("Diagram"))).toBe(true);
  expect(container.firstChild.contains(screen.getByText("Particles"))).toBe(true);
});

it("holds outgoing overlays on the last frame during a dissolve", () => {
  render(<Visual segment={{ duration: 2 }} size={[160, 90]} time={2} opacity={0.5} />);
  expect(screen.getByText("Diagram")).toBeTruthy();
  expect(screen.queryByText("Expired diagram")).toBeNull();
});

const manifest = {
  size: [160, 90], duration: 10, captions: [], segments: [
    { id: "first", label: "Scene 1", start: 0, duration: 4, base_duration: 4 },
    { id: "second", label: "Scene 2", start: 4, duration: 6, base_duration: 6 },
  ],
};
it("starts the compact player at the selected scene and follows selection changes", async () => {
  getVideoPreview.mockResolvedValue({ ok: true, data: manifest });
  const video = { id: "project", status: "READY", scenes: [] };
  const view = render(<VideoPreview video={video} selectedSceneId="second" compact />);
  await waitFor(() => expect(screen.getByLabelText("Preview playhead").value).toBe("4"));
  expect(screen.queryByRole("navigation", { name: "Preview timeline" })).toBeNull();
  view.rerender(<VideoPreview video={video} selectedSceneId="first" compact />);
  await waitFor(() => expect(screen.getByLabelText("Preview playhead").value).toBe("0"));
  expect(screen.getByRole("button", { name: "Play preview" })).toBeTruthy();
});
it("does not request a player manifest while scene changes are saving", () => {
  getVideoPreview.mockClear();
  render(<VideoPreview video={{ id: "project", status: "READY" }} disabled compact />);
  expect(screen.getByRole("status").textContent).toContain("once your changes are saved");
  expect(getVideoPreview).not.toHaveBeenCalled();
});

it("keeps the canvas mounted while refreshing and ignores metadata-only changes", async () => {
  getVideoPreview.mockResolvedValueOnce({ ok: true, data: manifest });
  const video = { id: "stable-project", status: "READY", updated_at: "first", scenes: [] };
  const view = render(<VideoPreview video={video} compact />);
  const canvas = await screen.findByRole("img", { name: "Scene 1 preview" });
  const calls = getVideoPreview.mock.calls.length;
  view.rerender(<VideoPreview video={{ ...video, updated_at: "second", title: "New title" }} compact />);
  expect(getVideoPreview.mock.calls.length).toBe(calls);
  getVideoPreview.mockReturnValueOnce(new Promise(() => {}));
  view.rerender(<VideoPreview video={video} compact disabled />);
  expect(screen.getByRole("img", { name: "Scene 1 preview" })).toBe(canvas);
  expect(screen.getByRole("button", { name: "Play preview" }).closest("fieldset").disabled).toBe(true);
  view.rerender(<VideoPreview video={video} compact />);
  expect(screen.getByRole("img", { name: "Scene 1 preview" })).toBe(canvas);
});

it("limits scene preview to the selected scene and replays from its start", async () => {
  getVideoPreview.mockResolvedValueOnce({ ok: true, data: manifest });
  let frame;
  vi.spyOn(globalThis, "requestAnimationFrame").mockImplementation(callback => { frame = callback; return 1; });
  vi.spyOn(globalThis, "cancelAnimationFrame").mockImplementation(() => {});
  try {
    render(<VideoPreview video={{ id: "scene-project", status: "READY", scenes: [] }} selectedSceneId="first" compact sceneOnly />);
    await waitFor(() => expect(screen.getByLabelText("Preview playhead").max).toBe("4"));
    expect(screen.getByLabelText("Preview playhead").value).toBe("0");
    fireEvent.click(screen.getByRole("button", { name: "Play preview" }));
    act(() => frame(performance.now() + 5000));
    expect(screen.getByLabelText("Preview playhead").value).toBe("4");
    expect(screen.getByRole("img", { name: "Scene 1 preview" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Play preview" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Play preview" }));
    expect(screen.getByLabelText("Preview playhead").value).toBe("0");
  } finally { vi.restoreAllMocks(); }
});
it("shows scene-relative time when previewing a later scene", async () => {
  getVideoPreview.mockResolvedValueOnce({ ok: true, data: manifest });
  render(<VideoPreview video={{ id: "later-scene", status: "READY", scenes: [] }} selectedSceneId="second" compact sceneOnly />);
  await waitFor(() => expect(screen.getByLabelText("Preview playhead").max).toBe("6"));
  expect(screen.getByLabelText("Preview playhead").value).toBe("0");
  fireEvent.change(screen.getByLabelText("Preview playhead"), { target: { value: "2" } });
  expect(screen.getByText("0:02 / 0:06")).toBeTruthy();
  expect(screen.getByRole("img", { name: "Scene 2 preview" })).toBeTruthy();
});

it("seeks across removed sections using joined output time and source caption timing", async () => {
  getVideoPreview.mockResolvedValueOnce({ ok: true, data: { ...manifest, playback_sections: [{ start: 1, end: 2 }, { start: 7, end: 10 }] } });
  render(<VideoPreview video={{ id: "cut-project", status: "READY", scenes: [] }} compact />);
  await waitFor(() => expect(screen.getByLabelText("Preview playhead").max).toBe("4"));
  const slider = screen.getByLabelText("Preview playhead");
  expect(slider.value).toBe("0");
  expect(screen.getByRole("img", { name: "Scene 1 preview" })).toBeTruthy();
  fireEvent.change(slider, { target: { value: "1.5" } });
  expect(screen.getByRole("img", { name: "Scene 2 preview" })).toBeTruthy();
  expect(screen.getByText("0:01 / 0:04")).toBeTruthy();
});
