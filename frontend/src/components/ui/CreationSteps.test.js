// @vitest-environment happy-dom
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { CreationSteps } from "./CreationSteps";
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
it("moves keyboard focus between steps without forcing a scroll", () => {
  const scroll = vi.spyOn(Element.prototype, "scrollIntoView").mockImplementation(() => {});
  const steps = ["Idea", "Look & sound", "Review"];
  const view = render(<CreationSteps steps={steps} current={0} onSelect={vi.fn()} />);
  const next = screen.getByRole("button", { name: /Look & sound/ });
  const focus = vi.spyOn(next, "focus");
  view.rerender(<CreationSteps steps={steps} current={1} onSelect={vi.fn()} />);
  expect(focus).toHaveBeenCalledWith({ preventScroll: true });
  expect(scroll).not.toHaveBeenCalled();
});
