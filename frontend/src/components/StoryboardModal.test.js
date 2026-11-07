// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { StoryboardModal } from "./StoryboardModal";
import * as api from "../api/apiService";

vi.mock("./GenerationCost", () => ({ GenerationCost: () => <div>Estimated cost</div> }));
vi.mock("./DeleteDraftProject", () => ({ DeleteDraftProject: () => <button type="button">Delete draft project</button> }));
vi.mock("./ui/EditorDialog", async importOriginal => ({
  ...await importOriginal(),
  EditorDialog: ({ children, footer }) => <div>{children}{footer}</div>,
}));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const shot = {
  sentence: "A clean room still feels cluttered.", image_description: "A tidy room with exposed cords.",
  shot_plan: { camera_movement: "PUSH_IN", shot_size: "WIDE", target_duration: 4 },
};
const video = {
  id: "video-1", mode: "AI", settings: { narration: true },
  gpt_answer: { title: "A calmer room", scenes: [{ scene: "Opening", sentences: [shot] }] },
};
const renderEditor = () => render(<MemoryRouter><StoryboardModal open video={video} onClose={vi.fn()} onApproved={vi.fn()} /></MemoryRouter>);

it("starts with compact scene cards and keeps advanced controls collapsed when editing", () => {
  renderEditor();
  const scene = screen.getByText("Scene 1: Opening").closest("details");
  expect(scene.open).toBe(false);
  expect(screen.getByText(shot.sentence, { selector: "p" })).toBeTruthy();
  expect(screen.getByText("Motion")).toBeTruthy();
  fireEvent.click(scene.querySelector("summary"));
  expect(scene.open).toBe(true);
  expect(screen.getByText("Motion, diagrams & shot settings").closest("details").open).toBe(false);
  expect(screen.getByText("Project settings & character continuity").closest("details").open).toBe(false);
  expect(screen.getByText("Revise storyboard with AI").closest("details").open).toBe(false);
});

it("preserves advanced settings when approving a narration edit", async () => {
  const approve = vi.spyOn(api, "approveScript").mockResolvedValue({ ok: true, data: { video } });
  renderEditor();
  fireEvent.click(screen.getByText("Scene 1: Opening").closest("summary"));
  fireEvent.change(screen.getByLabelText("Narration"), { target: { value: "Edited narration" } });
  fireEvent.submit(screen.getByLabelText("Video title").closest("form"));
  await waitFor(() => expect(approve).toHaveBeenCalledOnce());
  const submitted = approve.mock.calls[0][1].scenes[0].sentences[0];
  expect(submitted.sentence).toBe("Edited narration");
  expect(submitted.shot_plan).toEqual(shot.shot_plan);
});

it("opens collapsed fields when browser validation finds an error", () => {
  renderEditor();
  const input = screen.getByLabelText("Narration");
  expect(input.closest("details").open).toBe(false);
  fireEvent.invalid(input);
  expect(input.closest("details").open).toBe(true);
});
