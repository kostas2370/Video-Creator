// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

vi.mock("../api/apiService", () => ({
  getMediaAssets: vi.fn(), createMediaAsset: vi.fn(), editMediaAsset: vi.fn(),
  deleteMediaAsset: vi.fn(), downloadMediaAsset: vi.fn(),
}));
vi.mock("./ui/ConfirmationDialog", () => ({ ConfirmationDialog: () => null }));
vi.mock("./ui/EditorDialog", () => ({ EditorDialog: () => null, editorInput: "", editorButton: "" }));
import { getMediaAssets } from "../api/apiService";
import { MediaLibrary } from "./MediaLibrary";

beforeEach(() => {
  vi.clearAllMocks();
  getMediaAssets.mockResolvedValue({ ok: true, data: { count: 2, results: [
    { id: "private", title: "My track", kind: "AUDIO", file: "/private.wav", tags: [], is_shared: false },
    { id: "shared", title: "General track", kind: "AUDIO", file: "/shared.wav", tags: ["fun"], is_shared: true,
      attribution: "Music by Artist", license_url: "https://example.com/license" },
  ] } });
});
afterEach(cleanup);

it("offers general music while restricting edit and remove controls to private tracks", async () => {
  const onSelect = vi.fn();
  render(<MediaLibrary kind="AUDIO" onSelect={onSelect} />);
  await screen.findByText("General track");
  expect(screen.getAllByRole("button", { name: "Edit tags" })).toHaveLength(1);
  expect(screen.getAllByRole("button", { name: "Remove" })).toHaveLength(1);
  expect(screen.getByText("Music by Artist")).toBeTruthy();
  expect(screen.getByRole("link", { name: "License" }).getAttribute("href")).toBe("https://example.com/license");
  fireEvent.click(screen.getAllByRole("button", { name: "Use media" })[1]);
  expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "shared" }));
});

it("requests the selected private or general collection", async () => {
  render(<MediaLibrary kind="AUDIO" />);
  await screen.findByText("General track");
  fireEvent.change(screen.getByLabelText("Media collection"), { target: { value: "shared" } });
  await waitFor(() => expect(getMediaAssets).toHaveBeenLastCalledWith("", 1, "AUDIO", "shared"));
  fireEvent.change(screen.getByLabelText("Media collection"), { target: { value: "private" } });
  await waitFor(() => expect(getMediaAssets).toHaveBeenLastCalledWith("", 1, "AUDIO", "private"));
});
