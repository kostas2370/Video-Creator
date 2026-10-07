import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Home from "./HomePage";
import { generateVideo, getAvatars, getTemplates, getVoices, getCustomVisualProviders } from "../api/apiService";

jest.mock("../api/apiService", () => ({
  generateVideo: jest.fn(), getAvatars: jest.fn(), getTemplates: jest.fn(),
  getVoices: jest.fn(), getCustomVisualProviders: jest.fn(),
}));
jest.mock("../hooks/useAxiosPrivate", () => ({ useAxiosPrivate: () => {} }));
jest.mock("../components/ProceedModal", () => ({ ProceedModal: () => null }));
jest.mock("../components/SaveTemplateModal", () => ({ SaveTemplateModal: () => null }));
jest.mock("../components/DeleteModal", () => ({ DeleteModal: () => null }));

beforeEach(() => {
  jest.clearAllMocks();
  [getAvatars, getTemplates, getVoices, getCustomVisualProviders].forEach(fn => fn.mockResolvedValue({ ok: true, data: [] }));
  generateVideo.mockResolvedValue({ ok: false });
  URL.createObjectURL = jest.fn(() => "blob:reference");
  URL.revokeObjectURL = jest.fn();
});

async function prepare() {
  render(<MemoryRouter><Home /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText("Your prompt"), { target: { value: "A cat exploring" } });
  fireEvent.change(screen.getByLabelText("Visuals"), { target: { value: "AI" } });
  await waitFor(() => expect(screen.getByRole("button", { name: "Generate video" }).disabled).toBe(false));
  const file = new File(["image"], "cat.png", { type: "image/png" });
  fireEvent.change(screen.getByLabelText(/Reference image/), { target: { files: [file] } });
  return file;
}

test("uploads reference and form settings together with a preview", async () => {
  const file = await prepare();
  expect(screen.getByAltText("Reference preview").src).toBe("blob:reference");
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Generate video" })); });
  await waitFor(() => expect(generateVideo).toHaveBeenCalledTimes(1));
  const payload = generateVideo.mock.calls[0][0];
  expect(payload).toBeInstanceOf(FormData);
  expect(payload.get("reference_image")).toBe(file);
  expect(payload.get("message")).toBe("A cat exploring");
  expect(payload.get("narration")).toBe("true");
});

test("removing the reference restores ordinary generation", async () => {
  await prepare();
  fireEvent.click(screen.getByRole("button", { name: "Remove reference" }));
  expect(screen.queryByAltText("Reference preview")).toBeNull();
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Generate video" })); });
  await waitFor(() => expect(generateVideo).toHaveBeenCalledTimes(1));
  expect(generateVideo.mock.calls[0][0]).not.toBeInstanceOf(FormData);
  expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:reference");
});

test("switching to an unsupported provider clears the reference", async () => {
  await prepare();
  fireEvent.change(screen.getByLabelText("Visual provider"), { target: { value: "midjourney" } });
  expect(screen.queryByLabelText(/Reference image/)).toBeNull();
  fireEvent.change(screen.getByLabelText("Visual provider"), { target: { value: "sora" } });
  expect(screen.queryByAltText("Reference preview")).toBeNull();
  expect(screen.getByLabelText(/Reference image/)).toBeTruthy();
});
