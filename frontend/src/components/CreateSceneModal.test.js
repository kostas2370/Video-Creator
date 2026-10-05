import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { SceneCreationModal } from "./CreateSceneModal";
import { createScene, draftScene } from "../api/apiService";

jest.mock("../api/apiService", () => ({ createScene: jest.fn(), draftScene: jest.fn() }));
jest.mock("react-toastify", () => ({ toast: { success: jest.fn() } }));
beforeAll(() => { global.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }; });
beforeEach(() => jest.clearAllMocks());
const setup = () => {
  const props = { id: 12, showModal: true, setShowModal: jest.fn(), setItems: jest.fn() };
  render(<SceneCreationModal {...props} />);
  return props;
};

test.each([true, false])("drafts with context=%s and saves only after review", async useContext => {
  draftScene.mockResolvedValue({ data: { text: "AI dialogue", image_description: "A sunrise" } });
  createScene.mockResolvedValue({ data: { message: "saved" } });
  const props = setup();
  fireEvent.click(screen.getByRole("button", { name: "Create with AI" }));
  fireEvent.change(screen.getByLabelText("What should happen in this scene?"), { target: { value: "Introduce the journey" } });
  if (!useContext) fireEvent.click(screen.getByRole("radio", { name: /No context/ }));
  fireEvent.click(screen.getByRole("button", { name: "Generate draft" }));
  await waitFor(() => expect(screen.getByLabelText("Dialogue")).toHaveValue("AI dialogue"));
  expect(draftScene).toHaveBeenCalledWith(12, { prompt: "Introduce the journey", use_context: useContext });
  expect(createScene).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Dialogue"), { target: { value: "Reviewed dialogue" } });
  fireEvent.click(screen.getByRole("button", { name: "Add scene" }));
  await waitFor(() => expect(props.setShowModal).toHaveBeenCalledWith(false));
  expect(createScene.mock.calls[0][1].get("text")).toBe("Reviewed dialogue");
  expect(createScene.mock.calls[0][1].get("image_description")).toBe("A sunrise");
});

test("failed draft preserves the manual text and permits retry", async () => {
  draftScene.mockResolvedValue({ data: null, message: "Provider unavailable" });
  setup();
  fireEvent.change(screen.getByLabelText("Dialogue"), { target: { value: "My draft" } });
  fireEvent.click(screen.getByRole("button", { name: "Create with AI" }));
  fireEvent.change(screen.getByLabelText("What should happen in this scene?"), { target: { value: "A discovery" } });
  fireEvent.click(screen.getByRole("button", { name: "Generate draft" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Provider unavailable");
  expect(screen.getByLabelText("Dialogue")).toHaveValue("My draft");
  expect(screen.getByRole("button", { name: "Generate draft" })).toBeEnabled();
});

test("manual creation omits a blank optional visual and recovers from failure", async () => {
  createScene.mockResolvedValue({ data: null, message: "Try again" });
  const props = setup();
  fireEvent.change(screen.getByLabelText("Dialogue"), { target: { value: "Manual scene" } });
  fireEvent.click(screen.getByRole("button", { name: "Add scene" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Try again");
  expect(createScene.mock.calls[0][1].has("image_description")).toBe(false);
  expect(props.setShowModal).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Add scene" })).toBeEnabled();
});
