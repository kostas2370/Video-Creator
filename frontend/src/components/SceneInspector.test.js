// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
vi.mock("./VideoPreview", () => ({ VideoPreview: ({ selectedSceneId }) => <div role="status">Saved preview: {selectedSceneId}</div> }));
vi.mock("./SceneCuts", () => ({ SceneCuts: () => null }));
import { Scene } from "./Scene";
const scene = { id: "first", text: "A fox explores", video: "video-1", scene_image: { file: "/fox.jpg" }, narration_status: "disabled", timing: { duration: 4 }, audio_settings: {} };
afterEach(cleanup);
it("starts with composed playback and keeps everyday editing tools directly accessible", async () => {
  render(<Scene video={{ id: "video-1", status: "READY", scenes: [scene] }} scene={scene} manual onTiming={vi.fn()} />);
  expect(await screen.findByText("Saved preview: first")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Preview scene" }).getAttribute("aria-pressed")).toBe("true");
  expect(screen.getAllByRole("tab").map(tab => tab.textContent)).toEqual(["Script", "Visual", "Audio", "Captions", "Timing"]);
  expect(screen.queryByRole("heading", { name: "Scene audio" })).toBeNull();
  fireEvent.click(screen.getByRole("tab", { name: "Audio" }));
  expect(screen.getByRole("heading", { name: "Scene audio" })).toBeTruthy();
  fireEvent.click(screen.getByRole("tab", { name: "Captions" }));
  expect(screen.getByRole("heading", { name: "Scene captions" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Edit captions for scene 1" }).disabled).toBe(true);
  expect(screen.getByText("Add narration or a voiceover in Audio to edit timed captions.")).toBeTruthy();
  expect(screen.getByText("Saved preview: first")).toBeTruthy();
  expect(screen.getByRole("button", { name: /Overlays & motion/ }).getAttribute("aria-expanded")).toBe("false");
  fireEvent.click(screen.getByRole("button", { name: "Scene visual" }));
  expect(screen.getByRole("img", { name: "Scene 1 visual" })).toBeTruthy();
});
it("uses the source canvas while processing instead of opening an unavailable preview", () => {
  render(<Scene video={{ id: "video-1", status: "GENERATION", scenes: [scene] }} scene={scene} />);
  expect(screen.getByRole("button", { name: "Scene visual" }).getAttribute("aria-pressed")).toBe("true");
  expect(screen.queryByText("Saved preview: first")).toBeNull();
});

it("opens Audio directly from the missing-narration shortcut", () => {
  render(<Scene scene={{ ...scene, narration_status: "missing" }} onTiming={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Narration needs attention → Open audio" }));
  expect(screen.getByRole("tab", { name: "Audio" }).getAttribute("aria-selected")).toBe("true");
  expect(screen.getByRole("button", { name: "Retry narration" })).toBeTruthy();
});
