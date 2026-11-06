// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Scene } from "./Scene";
import { hasStillImage } from "./SceneMotion";
import { SceneDiagramPreview } from "./SceneDiagramPreview";

const overlay = { kind: "diagram", start: 0, end: null, opacity: 1, diagram: {
  template: "steps", title: "How banking works", items: [
    { label: "Loan created", detail: "A new deposit" },
    { label: "Loan repaid", detail: "Principal disappears" },
  ],
} };
const scene = { id: "banking", text: "Banks create deposits", video: "test", narration_status: "disabled", timing: { duration: 8 }, overlays: [overlay] };
afterEach(cleanup);

it.each([undefined, { file: "/media/diagram-backdrop.png", prompt: "Unused photo prompt" }])("shows and edits a complete text diagram without a photo (%j)", scene_image => {
  render(<Scene scene={{ ...scene, scene_image }} index={0} onMotion={vi.fn()} video_format="PORTRAIT" />);
  expect(screen.getByText("Loan created")).toBeTruthy();
  expect(screen.getByText("Loan repaid")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Edit text diagram for scene 1" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Edit visual" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Add visual" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Edit motion for scene 1" })).toBeNull();
  expect(screen.queryByText("Visual prompt")).toBeNull();
  fireEvent.change(screen.getByLabelText("Diagram preview time"), { target: { value: "0" } });
  expect(screen.queryByText("Loan repaid")).toBeNull();
});

it("shows the complete diagram in a storyboard thumbnail", () => {
  render(<SceneDiagramPreview scene={scene} videoFormat="PORTRAIT" />);
  expect(screen.getByText("Loan repaid")).toBeTruthy();
  expect(screen.queryByRole("slider")).toBeNull();
});

it("keeps photo controls for text overlays and temporary or translucent diagrams", () => {
  const photo = { file: "/media/photo.jpg" };
  for (const overlays of [[{ kind: "title" }], [{ ...overlay, start: 1 }], [{ ...overlay, end: 4 }], [{ ...overlay, opacity: .5 }]]) {
    expect(hasStillImage({ ...scene, scene_image: photo, overlays })).toBe(true);
  }
  expect(hasStillImage({ ...scene, scene_image: photo })).toBe(false);
  render(<Scene scene={{ ...scene, scene_image: photo, overlays: [{ ...overlay, start: 1 }] }} onMotion={vi.fn()} />);
  expect(screen.getByRole("button", { name: "Edit visual" })).toBeTruthy();
  fireEvent.click(screen.getByRole("tab", { name: "Style" }));
  expect(screen.getByRole("button", { name: "Edit motion for scene 1" })).toBeTruthy();
});
