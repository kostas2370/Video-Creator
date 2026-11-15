// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { VoicePreview } from "./VoicePreview";
import { previewVoice } from "../api/apiService";
vi.mock("../api/apiService", () => ({ previewVoice: vi.fn() }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
it("plays a provider sample without generating speech", () => {
  render(<VoicePreview voice={{ id: "roger", name: "Roger", sample: "https://example.com/roger.mp3" }} />);
  fireEvent.click(screen.getByRole("button", { name: "Listen to Roger" }));
  expect(screen.getByLabelText("Preview of Roger").getAttribute("src")).toBe("https://example.com/roger.mp3");
  expect(previewVoice).not.toHaveBeenCalled();
});
it("ignores a stale generated sample after a different voice is selected", async () => {
  let resolve;
  previewVoice.mockReturnValue(new Promise(done => { resolve = done; }));
  const { rerender } = render(<VoicePreview voice={{ id: "one", name: "One" }} />);
  fireEvent.click(screen.getByRole("button", { name: "Listen to One" }));
  rerender(<VoicePreview voice={{ id: "two", name: "Two", sample: "https://example.com/two.mp3" }} />);
  resolve({ ok: true, data: new Blob(["old audio"]) });
  await waitFor(() => expect(screen.getByRole("button", { name: "Listen to Two" })).toBeTruthy());
  expect(screen.queryByLabelText("Preview of One")).toBeNull();
});
it("shows provider errors and allows retrying", async () => {
  previewVoice.mockResolvedValue({ ok: false, message: "Connect your provider first." });
  render(<VoicePreview voice={{ id: "one", name: "One" }} />);
  fireEvent.click(screen.getByRole("button", { name: "Listen to One" }));
  expect((await screen.findByRole("alert")).textContent).toBe("Connect your provider first.");
  expect(screen.getByRole("button", { name: "Listen to One" }).disabled).toBe(false);
});
