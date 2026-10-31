// @vitest-environment happy-dom
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SceneTransition, defaultTransition } from "./SceneTransition";

afterEach(cleanup);
it("shows the series cut default and disables transition duration", () => {
  render(<SceneTransition scene={{ transition_after: "DEFAULT" }} settings={{ creation_mode: "SERIES" }} nextNumber={2} onChange={vi.fn()} />);
  expect(screen.getByRole("option", { name: "Video default (Cut)" })).toBeTruthy();
  expect(screen.getByLabelText("Transition duration").disabled).toBe(true);
});
it("honors explicit transitions and keeps standalone defaults", () => {
  expect(defaultTransition({})).toBe("FADE");
  expect(defaultTransition({ creation_mode: "SERIES", transition_default: "FADE" })).toBe("FADE");
  render(<SceneTransition scene={{ transition_after: "DISSOLVE" }} settings={{ creation_mode: "SERIES" }} nextNumber={2} onChange={vi.fn()} />);
  expect(screen.getByLabelText("Transition duration").disabled).toBe(false);
  expect(screen.getByText("Blend into the next scene")).toBeTruthy();
});
