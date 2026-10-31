// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Scene } from "./Scene";
import * as api from "../api/apiService";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
it("shows a saved starting image after video failure and retries the saved description", async () => {
  const retry = vi.spyOn(api, "generateSceneImage").mockResolvedValue({ ok: true });
  const updated = vi.fn();
  render(<Scene scene={{ id: "scene-1", video: "video-1", text: "Milo finds a lantern", narration_status: "disabled", starting_image: "/media/library/start.png", starting_image_description: "Milo at the forest gate", scene_image: { file: null } }} manual setUpdated={updated} />);
  expect(screen.getByAltText("Scene 1 saved starting image").getAttribute("src")).toContain("/media/library/start.png");
  fireEvent.click(screen.getByRole("button", { name: "Retry video with saved image" }));
  await waitFor(() => expect(updated).toHaveBeenCalledWith(true));
  expect(retry.mock.calls[0][0]).toBe("scene-1");
  expect(retry.mock.calls[0][1].get("image_description")).toBe("Milo at the forest gate");
});
