// @vitest-environment happy-dom
import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Visual } from "./VideoPreview";

vi.mock("./PhotoAnimationLayer", () => ({ PhotoAnimationLayer: () => <span>Particles</span> }));
vi.mock("./OverlayLayer", () => ({ OverlayLayer: ({ time, duration }) => <span>{time < duration ? "Diagram" : "Expired diagram"}</span> }));
afterEach(cleanup);

it("fades the complete scene including particles and diagrams without a photo", () => {
  const { container } = render(<Visual segment={{ duration: 2 }} size={[160, 90]} time={1} opacity={0.5} />);
  expect(container.firstChild.style.opacity).toBe("0.5");
  expect(container.firstChild.contains(screen.getByText("Diagram"))).toBe(true);
  expect(container.firstChild.contains(screen.getByText("Particles"))).toBe(true);
});

it("holds outgoing overlays on the last frame during a dissolve", () => {
  render(<Visual segment={{ duration: 2 }} size={[160, 90]} time={2} opacity={0.5} />);
  expect(screen.getByText("Diagram")).toBeTruthy();
  expect(screen.queryByText("Expired diagram")).toBeNull();
});
