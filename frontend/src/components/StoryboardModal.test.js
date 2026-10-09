import React from "react";
import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { StoryboardModal } from "./StoryboardModal";
import { approveScript } from "../api/apiService";

jest.mock("../api/apiService", () => ({ approveScript: jest.fn() }));
jest.mock("@material-tailwind/react", () => ({
  Dialog: ({ children }) => <div role="dialog">{children}</div>,
  DialogHeader: ({ children }) => <h2>{children}</h2>,
  DialogBody: ({ children }) => <div>{children}</div>,
  DialogFooter: ({ children }) => <div>{children}</div>,
}));
const video = { id: "draft-id", settings: { narration: true }, gpt_answer: {
  title: "A cat", scenes: [{ scene: "Opening", sentences: [{ sentence: "Hello", image_description: "A sleeping cat" }] }],
} };
const show = (props = {}) => render(<MemoryRouter><StoryboardModal open video={video} onClose={jest.fn()} {...props} /></MemoryRouter>);
beforeEach(() => jest.clearAllMocks());

test("shows generated prompts and sends edited script only after Proceed", async () => {
  const approved = jest.fn();
  approveScript.mockResolvedValue({ ok: true, data: { video: { id: video.id, status: "GENERATION" } } });
  show({ onApproved: approved });
  expect(screen.getByLabelText("Narration")).toHaveValue("Hello");
  expect(screen.getByLabelText("Visual prompt")).toHaveValue("A sleeping cat");
  expect(approveScript).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Visual prompt"), { target: { value: "A cat on a beach" } });
  fireEvent.click(screen.getByRole("button", { name: "Proceed" }));
  await waitFor(() => expect(approved).toHaveBeenCalled());
  expect(approveScript.mock.calls[0][1].scenes[0].sentences[0].image_description).toBe("A cat on a beach");
  expect(video.gpt_answer.scenes[0].sentences[0].image_description).toBe("A sleeping cat");
});

test("close does not start media generation", () => {
  const close = jest.fn();
  show({ onClose: close });
  fireEvent.click(screen.getByRole("button", { name: "Close" }));
  expect(close).toHaveBeenCalled();
  expect(approveScript).not.toHaveBeenCalled();
});

test("queue failure preserves edits and permits retry", async () => {
  approveScript.mockResolvedValue({ ok: false, message: "Worker unavailable" });
  show();
  fireEvent.change(screen.getByLabelText("Narration"), { target: { value: "Edited narration" } });
  fireEvent.click(screen.getByRole("button", { name: "Proceed" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Worker unavailable");
  expect(screen.getByLabelText("Narration")).toHaveValue("Edited narration");
  expect(screen.getByRole("button", { name: "Proceed" })).toBeEnabled();
});

test("visual-only drafts do not ask for narration", () => {
  show({ video: { ...video, settings: { narration: false } } });
  expect(screen.queryByLabelText("Narration")).not.toBeInTheDocument();
  expect(screen.getByLabelText("Visual prompt")).toHaveValue("A sleeping cat");
});


test("background updates preserve edits in an open draft", () => {
  const close = jest.fn();
  const { rerender } = render(<MemoryRouter><StoryboardModal open video={video} onClose={close} /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText("Narration"), { target: { value: "My new narration" } });
  rerender(<MemoryRouter><StoryboardModal open video={JSON.parse(JSON.stringify(video))} onClose={close} /></MemoryRouter>);
  expect(screen.getByLabelText("Narration")).toHaveValue("My new narration");
  const next = { ...video, id: "another-draft", gpt_answer: { ...video.gpt_answer, title: "Another video" } };
  rerender(<MemoryRouter><StoryboardModal open video={next} onClose={close} /></MemoryRouter>);
  expect(screen.getByLabelText("Video title")).toHaveValue("Another video");
  expect(screen.getByLabelText("Narration")).toHaveValue("Hello");
});
