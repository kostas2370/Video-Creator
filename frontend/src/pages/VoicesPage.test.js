// @vitest-environment happy-dom
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Voices } from "./VoicesPage";
import { getVoices } from "../api/apiService";
vi.mock("../api/apiService", () => ({ getVoices: vi.fn(), cloneVoice: vi.fn(), deleteVoice: vi.fn(), refreshVoice: vi.fn(), previewVoice: vi.fn() }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
it("shows imported voices, loads further pages, and keeps cloning available", async () => {
  getVoices.mockImplementation((search, page, options) => Promise.resolve({ ok: true, data: options?.is_cloned ? { results: [], next: null } : { results: [{ id: String(page), name: page === 1 ? "Roger" : "Sarah", provider: "ELEVENLABS", sample: "https://example.com/sample.mp3" }], next: page === 1 ? 2 : null } }));
  render(<MemoryRouter><Voices /></MemoryRouter>);
  await screen.findByRole("heading", { name: "Roger" });
  expect(screen.getByRole("button", { name: "Listen to Roger" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Delete" })).toBeNull();
  expect(screen.getByRole("button", { name: "Create my voice" }).disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Load more voices" }));
  await screen.findByRole("heading", { name: "Sarah" });
  fireEvent.change(screen.getByLabelText("Show"), { target: { value: "custom" } });
  await waitFor(() => expect(screen.queryByRole("heading", { name: "Roger" })).toBeNull());
  expect(screen.getByText("Your custom voices will appear here after you create one.")).toBeTruthy();
});
