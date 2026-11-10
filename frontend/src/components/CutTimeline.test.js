// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { CutTimeline, cutClock } from "./CutTimeline";
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
it("scrubs a zoomed timeline using its full width and selects the touched section", () => {
  const onSeek = vi.fn(), onSelect = vi.fn();
  const { container } = render(<CutTimeline scene={{}} sections={[{ start: 0, end: 2 }, { start: 6, end: 10 }]} sourceDuration={10} selected={0} position={0} onSeek={onSeek} onSelect={onSelect} />);
  fireEvent.click(screen.getByRole("button", { name: "Zoom in timeline" }));
  const track = container.querySelector(".cut-track");
  expect(track.style.width).toBe("200%");
  vi.spyOn(track, "getBoundingClientRect").mockReturnValue({ left: 100, width: 1200 });
  fireEvent.pointerDown(screen.getByRole("button", { name: /Section 2,/ }), { pointerId: 1, button: 0, clientX: 700 });
  expect(onSelect).toHaveBeenCalledWith(1);
  expect(onSeek).toHaveBeenLastCalledWith(3);
  fireEvent.pointerMove(track, { pointerId: 1, clientX: 1000 });
  expect(onSeek).toHaveBeenLastCalledWith(4.5);
  fireEvent.pointerUp(track, { pointerId: 1 });
  fireEvent.pointerMove(track, { pointerId: 1, clientX: 500 });
  expect(onSeek).toHaveBeenLastCalledWith(4.5);
});
it("formats precision timestamps without rolling seconds past sixty", () => {
  expect(cutClock(59.999)).toBe("01:00.00");
  expect(cutClock(1.416)).toBe("00:01.42");
});
