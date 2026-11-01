// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { GenerationModeSelect } from "./GenerationModeSelect";

afterEach(cleanup);

it("keeps Standard selected until Economy is explicitly chosen", () => {
  const change = vi.fn();
  render(<GenerationModeSelect onChange={change} />);
  expect(screen.getByRole("combobox", { name: "Generation mode" }).value).toBe("STANDARD");
  expect(change).not.toHaveBeenCalled();
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "ECONOMY" } });
  expect(change).toHaveBeenCalledWith("ECONOMY");
});

it("explains the quality tradeoff and separate animation and narration costs", () => {
  render(<GenerationModeSelect value="ECONOMY" onChange={vi.fn()} />);
  expect(screen.getByText(/Less detail, lower image cost/).textContent).toContain("Animation and narration prices are unchanged");
  expect(screen.getByText(/Existing media is kept/)).toBeTruthy();
});

it("can be locked during generation or saving", () => {
  render(<GenerationModeSelect disabled onChange={vi.fn()} />);
  expect(screen.getByRole("combobox").disabled).toBe(true);
});
