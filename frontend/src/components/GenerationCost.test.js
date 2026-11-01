// @vitest-environment happy-dom
import React from "react";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
vi.mock("../api/apiService", () => ({ getCostEstimate: vi.fn(), getScenarioCostEstimate: vi.fn(), getProjectCosts: vi.fn() }));
import { getCostEstimate, getScenarioCostEstimate, getProjectCosts } from "../api/apiService";
import { GenerationCost, ProjectCosts, RecordedCost, formatCost } from "./GenerationCost";

const estimate = { low_usd: "0.15", high_usd: "0.21", partial: false, currency: "USD", checked_at: "2026-11-01", lines: [{ label: "Images", provider: "OPENAI", model: "gpt-image-2", low_usd: "0.15", high_usd: "0.21", units: { images: 1 }, note: "Output only; inputs cost extra.", source: "https://developers.openai.com/api/docs/pricing" }] };
const tick = () => act(() => vi.advanceTimersByTimeAsync(300));
beforeEach(() => { vi.useFakeTimers(); vi.clearAllMocks(); });
afterEach(() => { cleanup(); vi.useRealTimers(); });

it("shows a priced estimate before generation and sends edited narration", async () => {
  getCostEstimate.mockResolvedValue({ ok: true, data: estimate });
  render(<GenerationCost videoId="video" sceneId="scene" operation="narration" text="Changed dialogue" />);
  expect(screen.getByRole("status").textContent).toContain("Estimating");
  await tick();
  expect(getCostEstimate).toHaveBeenCalledWith({ video_id: "video", scene_id: "scene", operation: "narration", text: "Changed dialogue" });
  expect(screen.getByText(/Estimated media cost:/).textContent).toContain("$0.15–$0.21 USD");
  fireEvent.click(screen.getByText("Cost breakdown and assumptions"));
  expect(screen.getByRole("link", { name: "Pricing source" }).href).toContain("developers.openai.com");
});

it("hides the old estimate immediately after inputs change and ignores late responses", async () => {
  let oldResponse;
  getCostEstimate.mockReturnValueOnce(new Promise(resolve => { oldResponse = resolve; }));
  getCostEstimate.mockResolvedValueOnce({ ok: true, data: { ...estimate, low_usd: "2", high_usd: "2" } });
  const view = render(<GenerationCost videoId="first" />);
  await tick();
  view.rerender(<GenerationCost videoId="second" />);
  await tick();
  expect(screen.getByText(/Estimated media cost:/).textContent).toContain("$2.00");
  await act(async () => oldResponse({ ok: true, data: estimate }));
  expect(screen.getByText(/Estimated media cost:/).textContent).toContain("$2.00");
  view.rerender(<GenerationCost videoId="second" text="New text" />);
  expect(screen.getByRole("status").textContent).toContain("Estimating");
});

it("shows unknown prices as unavailable and partial estimates as subtotals", async () => {
  getCostEstimate.mockResolvedValue({ ok: true, data: { ...estimate, partial: true, lines: [{ ...estimate.lines[0], low_usd: null, high_usd: null }] } });
  render(<GenerationCost videoId="video" />);
  await tick();
  expect(screen.getByText(/Known subtotal:/)).toBeTruthy();
  expect(screen.getByText("Images: Price unavailable")).toBeTruthy();
});

it("allows retry after estimate failure without hiding the paid-request notice", async () => {
  getCostEstimate.mockResolvedValueOnce({ ok: false }).mockResolvedValueOnce({ ok: true, data: estimate });
  render(<GenerationCost videoId="video" />);
  await tick();
  expect(screen.getByText(/Generation may still incur provider charges/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Retry estimate" }));
  await tick();
  expect(screen.getByText(/Estimated media cost:/)).toBeTruthy();
});

it("does not request estimates for upload controls or inactive forms", async () => {
  render(<GenerationCost videoId="video" active={false} />);
  await tick();
  expect(getCostEstimate).not.toHaveBeenCalled();
  expect(screen.queryByRole("complementary")).toBeNull();
});

it("shows scenario cost before a project exists and refreshes when the chosen model changes", async () => {
  getScenarioCostEstimate.mockResolvedValue({ ok: true, data: { ...estimate, scope: "scenario" } });
  const view = render(<GenerationCost scenario={{ message: "fox", gpt_model: "gpt-5.4-mini" }} />);
  await tick();
  expect(getScenarioCostEstimate).toHaveBeenCalledWith({ message: "fox", gpt_model: "gpt-5.4-mini" });
  expect(screen.getByText(/Estimated scenario cost:/)).toBeTruthy();
  view.rerender(<GenerationCost scenario={{ message: "fox", gpt_model: "gpt-5.4" }} />);
  await tick();
  expect(getScenarioCostEstimate.mock.calls[1][0].gpt_model).toBe("gpt-5.4");
  expect(getCostEstimate).not.toHaveBeenCalled();
});

it("refreshes costs when the saved scene duration or project settings change", async () => {
  getCostEstimate.mockResolvedValue({ ok: true, data: estimate });
  const view = render(<GenerationCost videoId="video" refresh={{ duration: 4 }} />);
  await tick();
  view.rerender(<GenerationCost videoId="video" refresh={{ duration: 8 }} />);
  expect(screen.getByRole("status").textContent).toContain("Estimating");
  await tick();
  expect(getCostEstimate).toHaveBeenCalledTimes(2);
  expect(getCostEstimate.mock.calls[1][0]).toEqual({ video_id: "video", operation: "all" });
});

it("compares the original estimate with recorded project costs and partial coverage", async () => {
  getProjectCosts.mockResolvedValue({ ok: true, data: { estimate, recorded: { totals: { requests: 3, requests_with_cost: 2, cost_usd: "0.32" } } } });
  render(<ProjectCosts videoId="video" refresh={1} />);
  await act(async () => {});
  expect(screen.getByText("$0.15–$0.21 USD")).toBeTruthy();
  expect(screen.getByText("$0.32")).toBeTruthy();
  expect(screen.getByText(/2 of 3 requests priced/)).toBeTruthy();
});

it("never turns missing cost into zero and preserves small charges", () => {
  expect(formatCost(null)).toBe("Price unavailable");
  expect(formatCost("0")).toBe("$0.00");
  expect(formatCost("0.000015")).toBe("<$0.0001");
  render(<RecordedCost metrics={{ requests: 2, requests_with_cost: 0, cost_usd: null }} />);
  expect(screen.getByText("Price unavailable")).toBeTruthy();
  expect(screen.getByText(/0 of 2 requests priced/)).toBeTruthy();
});
