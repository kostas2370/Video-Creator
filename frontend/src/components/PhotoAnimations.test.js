// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { BulkAutoMotion, SceneMotion } from "./SceneMotion";

const scene = { id: "00000000-0000-0000-0000-000000000001", scene_image: { file: "/photo.png" }, motion_style: "NONE", timing: { base_duration: 2 } };
beforeEach(() => {
  window.matchMedia = vi.fn(() => ({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }));
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({ measureText: text => ({ width: text.length * 500 }) });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it("saves a preset and particle preference without changing the photo", async () => {
  const save = vi.fn().mockResolvedValue(true);
  render(<SceneMotion scene={scene} index={0} onChange={save} videoFormat="PORTRAIT" />);
  fireEvent.click(screen.getByRole("button", { name: "Edit motion for scene 1" }));
  fireEvent.click(screen.getByRole("button", { name: /Playful Punchy/ }));
  fireEvent.click(screen.getByRole("checkbox", { name: "Decorative particles" }));
  fireEvent.click(screen.getByRole("button", { name: "Save animation" }));
  await waitFor(() => expect(save).toHaveBeenCalledWith(scene, { motion_style: "NONE", motion_intensity: "SUBTLE", animation_preset: "PLAYFUL", animation_accents: false }));
});

it("applies the selected style across photos and keeps a failed save open for retry", async () => {
  const apply = vi.fn().mockResolvedValue(false);
  render(<BulkAutoMotion scenes={[scene, { scene_image: { file: "/clip.mp4" } }]} onApply={apply} />);
  fireEvent.click(screen.getByRole("button", { name: "Animate all photos" }));
  expect(screen.getByText("Apply to 1 image scene.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: /Calm Gentle/ }));
  fireEvent.click(screen.getByRole("button", { name: "Apply animation" }));
  await waitFor(() => expect(apply).toHaveBeenCalledWith("SUBTLE", "CALM", true));
  expect(await screen.findByRole("alert")).toBeTruthy();
});

it("does not offer animation controls for a video clip", () => {
  render(<SceneMotion scene={{ ...scene, scene_image: { file: "/clip.mp4" } }} index={0} />);
  expect(screen.queryByRole("button")).toBeNull();
});
