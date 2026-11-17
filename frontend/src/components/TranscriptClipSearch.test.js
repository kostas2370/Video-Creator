// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
vi.mock("../api/apiService", () => ({ searchClipTranscript: vi.fn() }));
import { searchClipTranscript } from "../api/apiService";
import { TranscriptClipSearch } from "./TranscriptClipSearch";
afterEach(() => { cleanup(); vi.clearAllMocks(); });

async function search(props = {}) {
  searchClipTranscript.mockResolvedValue({ ok: true, data: { clips: [
    { title: "First", start: 0, end: 10 }, { title: "Second", start: 10, end: 20 },
  ] } });
  render(<TranscriptClipSearch projectId="p" {...props} />);
  fireEvent.change(screen.getByLabelText("Describe the moment you want"), { target: { value: "Funny" } });
  await userEvent.click(screen.getByRole("button", { name: "Find matching clips" }));
  await screen.findByLabelText("Select First");
}

it("keeps successful additions when a batch partially fails, and retries only remaining results", async () => {
  const add = vi.fn().mockResolvedValueOnce(true).mockResolvedValueOnce(false).mockResolvedValueOnce(true);
  await search({ onCreateClip: add });
  await userEvent.click(screen.getByLabelText("Select First"));
  await userEvent.click(screen.getByLabelText("Select Second"));
  await userEvent.click(screen.getByRole("button", { name: "Add selected (2)" }));
  await screen.findByRole("alert");
  expect(screen.getAllByText("Added")).toHaveLength(1);
  await userEvent.click(screen.getByRole("button", { name: "Add selected (1)" }));
  await waitFor(() => expect(screen.getAllByText("Added")).toHaveLength(2));
  expect(add.mock.calls.map(call => call[0].title)).toEqual(["First", "Second", "Second"]);
});

it("keeps individual additions in search and blocks duplicates", async () => {
  const add = vi.fn().mockResolvedValue(true);
  await search({ onCreateClip: add });
  await userEvent.click(screen.getAllByRole("button", { name: "Add clip", exact: true })[0]);
  await screen.findByText("Added", { exact: true });
  expect(add).toHaveBeenCalledWith({ title: "First", start: 0, end: 10 }, { edit: false });
  expect(screen.getByLabelText("Select First").disabled).toBe(true);
  expect(screen.getAllByRole("button", { name: "Add clip", exact: true })).toHaveLength(1);
});

it("blocks a batch that exceeds project capacity", async () => {
  const add = vi.fn();
  await search({ onCreateClip: add, remainingSlots: 1 });
  await userEvent.click(screen.getByLabelText("Select First"));
  await userEvent.click(screen.getByLabelText("Select Second"));
  expect(screen.getByRole("button", { name: "Add selected (2)" }).disabled).toBe(true);
  expect(add).not.toHaveBeenCalled();
});
