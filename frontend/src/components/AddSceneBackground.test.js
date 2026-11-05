// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SceneCreationModal } from "./CreateSceneModal";
import { draftScene } from "../api/apiService";
vi.mock("../api/apiService", () => ({ createScene: vi.fn(), draftScene: vi.fn() }));
vi.mock("./LibraryPicker", () => ({ LibraryPicker: () => null }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
it("allows a background draft to close and retains the reviewed result on reopening", async () => {
  let finish;
  draftScene.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  const props = { id: "project", setShowModal: vi.fn(), setItems: vi.fn() };
  const view = render(<SceneCreationModal {...props} showModal />);
  fireEvent.click(screen.getByRole("button", { name: /Create with AI/ }));
  fireEvent.change(screen.getByLabelText("What should happen in this scene?"), { target: { value: "Find the lighthouse" } });
  fireEvent.click(screen.getByRole("button", { name: "Generate draft" }));
  expect(screen.getByRole("button", { name: "Close editor" }).disabled).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "Close editor" }));
  expect(props.setShowModal).toHaveBeenCalledWith(false);
  view.rerender(<SceneCreationModal {...props} showModal={false} />);
  finish({ ok: true, data: { text: "A light in the distance.", image_description: "A lighthouse by the sea" } });
  await waitFor(() => expect(draftScene).toHaveBeenCalledTimes(1));
  view.rerender(<SceneCreationModal {...props} showModal />);
  await waitFor(() => expect(screen.getByLabelText("Dialogue").value).toBe("A light in the distance."));
  expect(draftScene).toHaveBeenCalledTimes(1);
});
