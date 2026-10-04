import React from "react";
import { MemoryRouter } from "react-router-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import Home from "./HomePage";
import { getAvatars, getVoices, getTemplates, generateVideo } from "../api/apiService";
jest.mock("../hooks/useAxiosPrivate", () => ({
  useAxiosPrivate: jest.fn()
}));
jest.mock("react-toastify", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
    info: jest.fn()
  }
}));
jest.mock("../api/apiService", () => ({
  getAvatars: jest.fn(),
  getVoices: jest.fn(),
  getTemplates: jest.fn(),
  generateVideo: jest.fn(),
  deleteTemplate: jest.fn()
}));
jest.mock("../api/pollVideo", () => ({
  pollVideo: () => ({
    promise: Promise.resolve({
      outcome: "SETTLED",
      video: {
        id: 7,
        status: "READY"
      }
    }),
    cancel: jest.fn()
  })
}));
jest.mock("../components/ProceedModal", () => ({
  ProceedModal: () => null
}));
jest.mock("../components/SaveTemplateModal", () => ({
  SaveTemplateModal: () => null
}));
jest.mock("../components/DeleteModal", () => ({
  DeleteModal: () => null
}));
beforeEach(() => {
  jest.resetAllMocks();
  getAvatars.mockResolvedValue(result([{
    id: 2,
    name: "Presenter"
  }]));
  getVoices.mockResolvedValue(result([{
    id: 1,
    name: "onyx",
    provider: "OPENAI"
  }]));
  getTemplates.mockResolvedValue(result([]));
  generateVideo.mockResolvedValue(result({
    video: {
      id: 7
    }
  }));
});
async function openForm() {
  render(<MemoryRouter><Home /></MemoryRouter>);
  await screen.findByRole("option", {
    name: "onyx"
  });
}
test("the form exposes voices and visuals while optional settings are collapsed", async () => {
  await openForm();
  expect(screen.getByRole("button", {
    name: "Generate video"
  })).toBeDisabled();
  expect(screen.getByLabelText("Voice")).toBeVisible();
  expect(screen.getByLabelText("Visuals")).toHaveValue("WEB");
  expect(screen.queryByRole("combobox", {
    name: "Script model"
  })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {
    name: /Advanced settings/
  }));
  expect(screen.getByRole("combobox", {
    name: "Script model"
  })).toBeVisible();
});
test("generation submits the selected voice and matching visual provider", async () => {
  await openForm();
  fireEvent.change(screen.getByLabelText("Your prompt"), {
    target: {
      value: "Explain solar panels"
    }
  });
  fireEvent.change(screen.getByLabelText("Voice"), {
    target: {
      value: "1"
    }
  });
  fireEvent.change(screen.getByLabelText("Visuals"), {
    target: {
      value: "AI"
    }
  });
  expect(screen.getByLabelText("Visual provider")).toHaveValue("DALL-E");
  fireEvent.click(screen.getByRole("button", {
    name: "Generate video"
  }));
  await waitFor(() => expect(generateVideo).toHaveBeenCalledWith(expect.objectContaining({
    message: "Explain solar panels",
    voice_id: "1",
    image_mode: "AI",
    provider: "DALL-E"
  })));
  await waitFor(() => expect(screen.getByRole("button", {
    name: "Generate video"
  })).toBeEnabled());
});
test("turning narration off disables voice controls and updates the summary", async () => {
  await openForm();
  fireEvent.click(screen.getByRole("checkbox", {
    name: /Narration/
  }));
  expect(screen.getByLabelText("Voice")).toBeDisabled();
  expect(screen.getByLabelText("Presenter")).toBeDisabled();
  expect(screen.getByText("Clips only")).toBeInTheDocument();
});
test("an empty voice list points users to provider settings", async () => {
  getVoices.mockResolvedValue(result([]));
  render(<MemoryRouter><Home /></MemoryRouter>);
  expect(await screen.findByRole("link", {
    name: "Check your provider settings"
  })).toHaveAttribute("href", "/api-keys/");
});
test("loading a saved template updates the visible controls and summary", async () => {
  getTemplates.mockResolvedValue(result([{
    id: 3,
    title: "Explainer template",
    message: "A saved story",
    voice_id: 1,
    image_mode: "AI",
    provider: "DALL-E",
    narration: true
  }]));
  await openForm();
  fireEvent.change(screen.getByLabelText("Start from a template"), {
    target: {
      value: "3"
    }
  });
  expect(screen.getByLabelText("Your prompt")).toHaveValue("A saved story");
  expect(screen.getByLabelText("Voice")).toHaveValue("1");
  expect(screen.getByLabelText("Visuals")).toHaveValue("AI");
  expect(screen.getByText("onyx · OpenAI")).toBeInTheDocument();
});
function result(data) {
  return {
    ok: data !== undefined,
    data: data ?? null
  };
}
