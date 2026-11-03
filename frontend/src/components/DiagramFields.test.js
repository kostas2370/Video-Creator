// @vitest-environment happy-dom
import React, { useState } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, expect, it, vi } from "vitest";
import { SceneOverlays } from "./SceneOverlays";
import { updateSceneOverlays } from "../api/apiService";
import { DiagramFields } from "./DiagramFields";
import { OverlayLayer } from "./OverlayLayer";
import { VisualEditingFields } from "./VisualEditingFields";

vi.mock("../api/apiService", () => ({ updateSceneOverlays: vi.fn() }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it("creates, edits, bounds and removes an optional diagram", () => {
  function Editor() {
    const [value, setValue] = useState(null);
    return <DiagramFields value={value} onChange={setValue} optional />;
  }
  render(<Editor />);
  fireEvent.change(screen.getByLabelText("Educational animation"), { target: { value: "steps" } });
  fireEvent.change(screen.getByLabelText("Item 1"), { target: { value: "Start here" } });
  fireEvent.click(screen.getByRole("button", { name: "Add item" }));
  fireEvent.click(screen.getByRole("button", { name: "Add item" }));
  expect(screen.queryByRole("button", { name: "Add item" })).toBeNull();
  fireEvent.change(screen.getByLabelText("Educational animation"), { target: { value: "comparison" } });
  expect(screen.getByLabelText("Item 1").value).toBe("Start here");
  expect(screen.queryByLabelText("Item 3")).toBeNull();
  fireEvent.change(screen.getByLabelText("Educational animation"), { target: { value: "" } });
  expect(screen.queryByLabelText("Item 1")).toBeNull();
});

it("keeps diagrams and extra AI labels mutually exclusive", () => {
  function Review() {
    const [editing, setEditing] = useState({ overlays: [{ text: "Extra", start_fraction: 0, end_fraction: 1 }] });
    return <VisualEditingFields editing={editing} onChange={setEditing} />;
  }
  render(<Review />);
  fireEvent.change(screen.getByLabelText("Educational animation"), { target: { value: "timeline" } });
  expect(screen.queryByLabelText("Label 1")).toBeNull();
  expect(screen.getByRole("button", { name: "Add label" }).disabled).toBe(true);
});

it("reveals diagram items over time and clips them to the scene boundary", () => {
  const item = { kind: "diagram", start: 1, end: null, opacity: 1, diagram: { template: "steps", title: "Process", items: [{ label: "First", detail: "" }, { label: "Last", detail: "" }] } };
  const preview = time => renderToStaticMarkup(<OverlayLayer overlays={[item]} time={time} duration={5} frameSize={[1080, 1920]} />);
  expect(preview(.9)).not.toContain("Process");
  expect(preview(1.5)).toContain("First");
  expect(preview(1.5)).not.toContain("Last");
  expect(preview(4)).toContain("Last");
  expect(preview(5)).not.toContain("Process");
});

it("saves a manually added diagram through the existing scene controls", async () => {
  updateSceneOverlays.mockResolvedValue({ ok: true });
  const saved = vi.fn();
  render(<SceneOverlays scene={{ id: "scene-1", overlays: [], timing: { duration: 6 } }} index={0} onSaved={saved} videoFormat="PORTRAIT" />);
  fireEvent.click(screen.getByRole("button", { name: "Add text and logo overlays for scene 1" }));
  fireEvent.click(screen.getByRole("button", { name: "+ Educational animation" }));
  fireEvent.change(screen.getByLabelText("Educational animation"), { target: { value: "flow" } });
  fireEvent.change(screen.getByLabelText("Item 1"), { target: { value: "Before" } });
  fireEvent.change(screen.getByLabelText("Item 2"), { target: { value: "After" } });
  fireEvent.click(screen.getByRole("button", { name: "Save overlays" }));
  await waitFor(() => expect(saved).toHaveBeenCalledWith(true));
  const [id, payload] = updateSceneOverlays.mock.calls[0];
  expect(id).toBe("scene-1");
  expect(payload.overlays[0].kind).toBe("diagram");
  expect(payload.overlays[0].diagram.template).toBe("flow");
  expect(payload.overlays[0].diagram.items.map(item => item.label)).toEqual(["Before", "After"]);
});
