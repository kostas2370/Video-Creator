// @vitest-environment happy-dom
import React, { useState } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { VisualEditingFields } from "./VisualEditingFields";
import { StoryboardModal } from "./StoryboardModal";
import { approveScript } from "../api/apiService";

vi.mock("./GenerationCost", () => ({ GenerationCost: () => null }));
vi.mock("../api/apiService", async importOriginal => ({ ...await importOriginal(), approveScript: vi.fn() }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

const editing = { motion_style: "ZOOM_IN", motion_intensity: "SUBTLE", transition_after: "CUT", transition_duration: .2, pause_after: 0, animation_preset: "EXPLAINER", animation_accents: false, overlays: [{ text: "A tiny hiding place", position: "top-center", start_fraction: .25, end_fraction: .75 }] };

it("reviews and submits shot purpose, animation, and label timing together", async () => {
  approveScript.mockResolvedValue({ ok: true, data: { video: { id: "video-1" } } });
  const video = { id: "video-1", mode: "AI", settings: { ai_scene_editing: true, visual_type: "IMAGE" }, gpt_answer: { title: "Cats", scenes: [{ scene: "Opening", sentences: [{ sentence: "Cats love boxes.", image_description: "A cat in a box", shot_plan: { role: "HOOK", visual_focus: "The cat peeking out" }, editing }] }] } };
  render(<MemoryRouter><StoryboardModal open video={video} onClose={vi.fn()} onApproved={vi.fn()} /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText("Role in the story"), { target: { value: "REVEAL" } });
  fireEvent.change(screen.getByLabelText("Photo animation"), { target: { value: "DRAMATIC" } });
  fireEvent.change(screen.getByLabelText("Label 1"), { target: { value: "Look inside" } });
  fireEvent.change(screen.getByLabelText("Show at (%)"), { target: { value: "40" } });
  fireEvent.click(screen.getByRole("button", { name: "Proceed" }));
  await waitFor(() => expect(approveScript).toHaveBeenCalled());
  const shot = approveScript.mock.calls[0][1].scenes[0].sentences[0];
  expect(shot.shot_plan).toEqual({ role: "REVEAL", visual_focus: "The cat peeking out" });
  expect(shot.editing.animation_preset).toBe("DRAMATIC");
  expect(shot.editing.overlays[0]).toEqual({ text: "Look inside", position: "top-center", start_fraction: .4, end_fraction: .75 });
});

it("allows labels to be removed while keeping camera generation in video clips", () => {
  function Review() {
    const [value, setValue] = useState(editing);
    return <VisualEditingFields editing={value} onChange={setValue} photoAnimations={false} />;
  }
  render(<Review />);
  expect(screen.queryByLabelText("Photo animation")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Remove label 1" }));
  expect(screen.queryByLabelText("Label 1")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Add label" }));
  expect(screen.getByLabelText("Hide at (%)").value).toBe("50");
});
