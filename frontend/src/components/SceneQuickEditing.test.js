// @vitest-environment happy-dom
import React, { useState } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ReorderableScenes } from "./ReorderableScenes";
const scenes = ["first", "second"].map((id, index) => ({ id, video: "video-1", text: `Script ${index + 1}`, narration_status: "disabled", audio_settings: {}, timing: { duration: 5 } }));
function Editor({ textBusy = false }) {
  const [selected, select] = useState("first");
  return <ReorderableScenes videoId="video-1" scenes={scenes} manual selectedSceneId={selected} onSelectScene={select} textBusy={textBusy} disabled={textBusy} onTextSave={vi.fn()} onTiming={vi.fn()} />;
}
beforeEach(() => sessionStorage.clear());
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
it("keeps drafts when switching scenes and reopening the editor", () => {
  const view = render(<Editor />);
  fireEvent.change(screen.getByLabelText("Text for scene 1"), { target: { value: "My first draft" } });
  fireEvent.click(screen.getByRole("button", { name: "Edit scene 2" }));
  expect(screen.getByLabelText("Text for scene 2").value).toBe("Script 2");
  fireEvent.click(screen.getByRole("button", { name: "Edit scene 1" }));
  expect(screen.getByLabelText("Text for scene 1").value).toBe("My first draft");
  view.unmount(); render(<Editor />);
  expect(screen.getByLabelText("Text for scene 1").value).toBe("My first draft");
});
it("offers timing outside the advanced section", () => {
  render(<Editor />);
  expect(screen.getByRole("region", { name: "Quick scene timing" }).closest("details")).toBeNull();
  expect(screen.getByLabelText("Duration of scene 1")).toBeTruthy();
  expect(screen.getByLabelText("Pause after scene 1")).toBeTruthy();
});
it("locks scene switching during a text operation", () => {
  render(<Editor textBusy />);
  expect(screen.getByRole("button", { name: "Edit scene 2" }).disabled).toBe(true);
  expect(screen.getByRole("button", { name: "Next scene" }).disabled).toBe(true);
});
it("keeps drafts in memory when browser storage is unavailable", () => {
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("storage unavailable"); });
  render(<Editor />);
  fireEvent.change(screen.getByLabelText("Text for scene 1"), { target: { value: "Keep in memory" } });
  fireEvent.click(screen.getByRole("button", { name: "Edit scene 2" }));
  fireEvent.click(screen.getByRole("button", { name: "Edit scene 1" }));
  expect(screen.getByLabelText("Text for scene 1").value).toBe("Keep in memory");
});
