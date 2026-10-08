import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { SceneCreationModal } from "./CreateSceneModal";
import { createScene, draftScene } from "../api/apiService";

jest.mock("../api/apiService", () => ({ createScene: jest.fn(), draftScene: jest.fn() }));
jest.mock("./ui/EditorDialog", () => ({
  EditorDialog: ({ open, children }) => open ? <div>{children}</div> : null,
  editorInput: "", editorButton: "",
}));

beforeEach(() => {
  jest.clearAllMocks();
  createScene.mockResolvedValue({ data: { status: "GENERATION" } });
});

function openEditor() {
  render(<SceneCreationModal id={42} showModal setShowModal={jest.fn()} setItems={jest.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Create with AI" }));
  fireEvent.change(screen.getByLabelText("What should happen in this scene?"), { target: { value: "Continue the journey" } });
}

test("defaults to one sentence and keeps the draft unsaved until review", async () => {
  draftScene.mockResolvedValue({ data: { text: "We follow the path.", image_description: "A winding path" } });
  openEditor();
  expect(screen.getByLabelText("Sentences / scenes").value).toBe("1");
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Generate draft" })); });
  expect(draftScene).toHaveBeenCalledWith(42, expect.objectContaining({ draft_type: "sentence", sentence_count: 1 }));
  expect(screen.getByLabelText("Dialogue").value).toBe("We follow the path.");
  expect(createScene).not.toHaveBeenCalled();
});

test("reviews, edits, and removes section sentences before queueing them together", async () => {
  draftScene.mockResolvedValue({ data: { scenes: [
    { text: "The journey begins.", image_description: "A sunrise" },
    { text: "We cross the river.", image_description: "A river" },
    { text: "We arrive home.", image_description: "A home" },
  ] } });
  openEditor();
  fireEvent.change(screen.getByLabelText("Draft length"), { target: { value: "section" } });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Generate draft" })); });
  expect(draftScene).toHaveBeenCalledWith(42, expect.objectContaining({ draft_type: "section", sentence_count: 3 }));
  expect(createScene).not.toHaveBeenCalled();
  fireEvent.change(screen.getAllByLabelText("Sentence")[0], { target: { value: "A new journey begins." } });
  fireEvent.click(screen.getAllByRole("button", { name: "Remove" })[1]);
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Add 2 scenes" })); });
  await waitFor(() => expect(createScene).toHaveBeenCalledWith(42, { scenes: [
    { text: "A new journey begins.", image_description: "A sunrise", is_last: false, with_audio: false },
    { text: "We arrive home.", image_description: "A home", is_last: true, with_audio: false },
  ] }));
});

test("a short story starts with six scenes and allows a smaller count", async () => {
  draftScene.mockResolvedValue({ data: { scenes: [
    { text: "We leave.", image_description: "A door" },
    { text: "We return.", image_description: "A home" },
  ] } });
  openEditor();
  fireEvent.change(screen.getByLabelText("Draft length"), { target: { value: "story" } });
  expect(screen.getByLabelText("Sentences / scenes").value).toBe("6");
  fireEvent.change(screen.getByLabelText("Sentences / scenes"), { target: { value: "2" } });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Generate draft" })); });
  expect(draftScene).toHaveBeenCalledWith(42, expect.objectContaining({ draft_type: "story", sentence_count: 2 }));
});
