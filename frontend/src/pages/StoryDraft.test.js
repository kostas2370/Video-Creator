// @vitest-environment happy-dom
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { StoryVideo } from "./StoryVideoPage";
import { draftStory } from "../api/apiService";
vi.mock("../api/apiService", () => ({ draftStory: vi.fn(), createStoryVideo: vi.fn(), getVoices: vi.fn() }));
vi.mock("../hooks/useAxiosPrivate", () => ({ useAxiosPrivate: () => {} }));
vi.mock("../hooks/useAssetOptions", () => ({ useAssetOptions: () => ({ items: [], loading: false }) }));
vi.mock("../components/ui/MoreAssetOptions", () => ({ MoreAssetOptions: () => null }));
vi.mock("../components/CaptionLayer", () => ({ CaptionLayer: () => null }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
it("keeps the form editable while writing and requires review before replacing text", async () => {
  let finish;
  draftStory.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  render(<MemoryRouter><StoryVideo /></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", { name: "Generate story" }));
  expect(screen.getByLabelText("Video title").closest("fieldset").disabled).toBe(false);
  fireEvent.change(screen.getByLabelText("Your story"), { target: { value: "My own writing" } });
  finish({ ok: true, data: { title: "AI title", story: "AI story" } });
  await screen.findByRole("region", { name: "Generated story draft" });
  expect(screen.getByLabelText("Your story").value).toBe("My own writing");
  fireEvent.click(screen.getByRole("button", { name: "Use this story" }));
  await waitFor(() => expect(screen.getByLabelText("Your story").value).toBe("AI story"));
});
