// @vitest-environment happy-dom
import React from "react";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { DeveloperPrompts } from "./DeveloperPrompts";
import { getVideoLLMTraces } from "../api/apiService";

vi.mock("../api/apiService", () => ({ getVideoLLMTraces: vi.fn() }));
beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);
const trace = { id: 1, model: "gpt-test", attempt: 1, created_at: "2026-11-16T10:00:00Z", prompt: "A fox explores", response: '{"title":"Fox"}', validation_errors: [], has_reference_image: true };
const page = (results, changes = {}) => ({ ok: true, data: { results, count: results.length, current: 1, next: null, previous: null, ...changes } });
const open = async () => act(async () => {
  const details = screen.getByText("Advanced · Developer prompts").closest("details");
  details.open = true;
  fireEvent(details, new Event("toggle"));
});

it("loads only when opened and shows prompts, formatted JSON, and image metadata", async () => {
  getVideoLLMTraces.mockResolvedValue(page([trace]));
  render(<DeveloperPrompts videoId="video" />);
  expect(getVideoLLMTraces).not.toHaveBeenCalled();
  await open();
  expect(getVideoLLMTraces).toHaveBeenCalledWith("video", 1);
  expect(screen.getByText("A fox explores")).toBeTruthy();
  expect(screen.getByText(/"title": "Fox"/)).toBeTruthy();
  expect(screen.getByText("A reference image was included with this prompt.")).toBeTruthy();
});

it("preserves invalid raw replies and displays correction feedback", async () => {
  getVideoLLMTraces.mockResolvedValue(page([{ ...trace, response: "invalid JSON", validation_errors: ["Return valid JSON."] }]));
  render(<DeveloperPrompts videoId="video" />);
  await open();
  expect(screen.getByText("invalid JSON")).toBeTruthy();
  expect(screen.getByText("Return valid JSON.")).toBeTruthy();
});

it("handles failed loading and refreshes without polling", async () => {
  getVideoLLMTraces.mockResolvedValueOnce({ ok: false }).mockResolvedValueOnce(page([]));
  render(<DeveloperPrompts videoId="video" />);
  await open();
  expect(screen.getByRole("alert")).toBeTruthy();
  await act(async () => fireEvent.click(screen.getByText("Refresh requests")));
  expect(screen.getByText("No captured requests for this project yet.")).toBeTruthy();
  expect(getVideoLLMTraces).toHaveBeenCalledTimes(2);
});

it("loads older pages on demand", async () => {
  getVideoLLMTraces.mockResolvedValueOnce(page([trace], { next: 2, count: 13 })).mockResolvedValueOnce(page([], { current: 2, previous: 1, count: 13 }));
  render(<DeveloperPrompts videoId="video" />);
  await open();
  await act(async () => fireEvent.click(screen.getByText("Older")));
  expect(getVideoLLMTraces).toHaveBeenLastCalledWith("video", 2);
});
