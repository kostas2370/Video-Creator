// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ClipEditor } from "./ClipEditor";
vi.mock("../api/apiService", () => ({ saveClip: vi.fn() }));
afterEach(cleanup);
it("seeks the existing player when trimming instead of remounting its media", () => {
  const project = { id: "p", duration: 180, words: [], preview: "/media/preview.mp4" };
  const clip = { id: "c", title: "Clip", start: 0, end: 120, words: [], layout: "CROP", captions: false, style: {} };
  const view = render(<ClipEditor project={project} clip={clip} onSaved={vi.fn()} onClose={vi.fn()} />);
  const player = view.container.querySelector("video");
  fireEvent.change(screen.getByLabelText("Start (minutes)"), { target: { value: "0.5" } });
  expect(view.container.querySelector("video")).toBe(player);
  expect(player.currentTime).toBe(30);
});
