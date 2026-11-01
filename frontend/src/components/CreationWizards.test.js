// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
vi.mock("../hooks/useAxiosPrivate", () => ({ useAxiosPrivate: () => ({}) }));
vi.mock("../api/apiService", async importOriginal => ({ ...await importOriginal(), getGenerationModels: vi.fn(), getAvatars: vi.fn(), getTemplates: vi.fn(), getVoices: vi.fn(), getIntro: vi.fn(), getOutro: vi.fn(), getCustomVisualProviders: vi.fn(), generateVideo: vi.fn(), draftCharacterDescription: vi.fn() }));
import * as api from "../api/apiService";
import Home from "../pages/HomePage";
import { SeriesProfileForm } from "./SeriesProfileForm";
import { CharacterDescriptionDraft } from "./CharacterDescriptionDraft";

beforeEach(() => {
  vi.clearAllMocks();
  [api.getAvatars, api.getTemplates, api.getVoices, api.getIntro, api.getOutro].forEach(fn => fn.mockResolvedValue({ ok: true, data: { results: [], next: null } }));
  api.getGenerationModels.mockResolvedValue({ ok: true, data: { script_models: { OPENAI: ["server-script-model"] }, default_script_model: "server-script-model" } });
  api.getCustomVisualProviders.mockResolvedValue({ ok: true, data: [] });
  api.generateVideo.mockResolvedValue({ ok: false });
});
afterEach(cleanup);

it("offers Economy only as an explicit generation choice", async () => {
  render(<MemoryRouter><Home /></MemoryRouter>);
  fireEvent.change(screen.getByLabelText("Your prompt"), { target: { value: "A fox solves a mystery" } });
  fireEvent.click(screen.getByRole("button", { name: "Continue to look & sound" }));
  fireEvent.click(screen.getByRole("button", { name: "Review video" }));
  expect(screen.getByRole("combobox", { name: "Generation mode" }).value).toBe("STANDARD");
  fireEvent.change(screen.getByRole("combobox", { name: "Generation mode" }), { target: { value: "ECONOMY" } });
  await waitFor(() => expect(screen.getByRole("button", { name: "Draft storyboard" }).disabled).toBe(false));
  fireEvent.click(screen.getByRole("button", { name: "Draft storyboard" }));
  await waitFor(() => expect(api.generateVideo).toHaveBeenCalledOnce());
  expect(api.generateVideo.mock.calls[0][0]).toMatchObject({ generation_mode: "ECONOMY" });
});

it("walks through video steps without generating until final review and preserves earlier choices", async () => {
  render(<MemoryRouter><Home /></MemoryRouter>);
  expect(screen.queryByRole("heading", { name: "Choose the look & sound" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Continue to look & sound" }));
  expect(screen.getByRole("alert").textContent).toContain("Describe your video idea");
  fireEvent.change(screen.getByLabelText("Your prompt"), { target: { value: "A fox solves a mystery" } });
  fireEvent.click(screen.getByRole("button", { name: "Continue to look & sound" }));
  expect(screen.getByRole("heading", { name: "Choose the look & sound" })).toBeTruthy();
  fireEvent.click(screen.getByRole("radio", { name: /Portrait/ }));
  fireEvent.click(screen.getByRole("button", { name: "Review video" }));
  expect(screen.getByRole("heading", { name: "Review your video" })).toBeTruthy();
  expect(api.generateVideo).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Back" }));
  expect(screen.getByRole("radio", { name: /Portrait/ }).checked).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Review video" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Draft storyboard" }).disabled).toBe(false));
  fireEvent.click(screen.getByRole("button", { name: "Draft storyboard" }));
  await waitFor(() => expect(api.generateVideo).toHaveBeenCalledOnce());
  expect(api.generateVideo.mock.calls[0][0]).toMatchObject({ message: "A fox solves a mystery", video_format: "PORTRAIT", review_script: true });
});

it("keeps series production choices until the final step and preserves them across navigation", async () => {
  const onSave = vi.fn();
  render(<SeriesProfileForm onSave={onSave} />);
  expect(screen.queryByRole("spinbutton", { name: "Shots per episode" })).toBeNull();
  fireEvent.change(screen.getByLabelText("Series name"), { target: { value: "Fox mysteries" } });
  fireEvent.change(screen.getByLabelText("What is this series about?"), { target: { value: "A fox solves a mystery each week" } });
  fireEvent.click(screen.getByRole("button", { name: "Continue to cast" }));
  expect(screen.getByRole("heading", { name: "Meet your characters" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Continue to finish" }));
  fireEvent.change(screen.getByRole("spinbutton", { name: "Shots per episode" }), { target: { value: "9" } });
  fireEvent.click(screen.getByRole("button", { name: "Back" }));
  fireEvent.click(screen.getByRole("button", { name: "Continue to finish" }));
  expect(screen.getByRole("spinbutton", { name: "Shots per episode" }).value).toBe("9");
  expect(onSave).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Create series" }));
  expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ title: "Fox mysteries", scene_count: 9, narration: false }));
});

it("reviews an AI character description before applying it and sends the existing identity as context", async () => {
  const onUse = vi.fn();
  const character = { name: "Milo", appearance: "Orange fox", wardrobe: "Scarf", personality: "", relationships: "" };
  const draft = { ...character, personality: "Curious detective", wardrobe: "Teal scarf" };
  api.draftCharacterDescription.mockResolvedValue({ ok: true, data: { character: draft } });
  render(<CharacterDescriptionDraft character={character} premise="Fox mysteries" visualStyle="Watercolor" storyFormat="ANIMATED_STORY" castNames={["Milo", "Rin"]} onUse={onUse} />);
  fireEvent.change(screen.getByLabelText(/Character idea/), { target: { value: "A shy detective" } });
  fireEvent.click(screen.getByRole("button", { name: "Write description with AI" }));
  await screen.findByText("Description draft");
  expect(onUse).not.toHaveBeenCalled();
  expect(api.draftCharacterDescription).toHaveBeenCalledWith(expect.objectContaining({ name: "Milo", appearance: "Orange fox", idea: "A shy detective", cast_names: ["Milo", "Rin"] }));
  fireEvent.click(screen.getByRole("button", { name: "Use description" }));
  expect(onUse).toHaveBeenCalledWith(draft);
});

it("keeps the existing description when AI drafting fails", async () => {
  api.draftCharacterDescription.mockResolvedValue({ ok: false, message: "Text provider unavailable" });
  const onUse = vi.fn();
  render(<CharacterDescriptionDraft character={{ name: "Milo", appearance: "Orange fox" }} premise="Fox mysteries" visualStyle="Watercolor" storyFormat="GENERAL" castNames={["Milo"]} onUse={onUse} />);
  fireEvent.click(screen.getByRole("button", { name: "Write description with AI" }));
  expect((await screen.findByRole("alert")).textContent).toContain("Text provider unavailable");
  expect(onUse).not.toHaveBeenCalled();
});

it("loads script choices and the default from the backend", async () => {
  render(<MemoryRouter><Home /></MemoryRouter>);
  await waitFor(() => expect(api.getGenerationModels).toHaveBeenCalledOnce());
  fireEvent.change(screen.getByLabelText("Your prompt"), { target: { value: "A fox" } });
  fireEvent.click(screen.getByRole("button", { name: "Continue to look & sound" }));
  fireEvent.click(screen.getByRole("button", { name: "Review video" }));
  await waitFor(() => expect(screen.getByLabelText("Script model").value).toBe("server-script-model"));
  expect(screen.getByRole("option", { name: "server-script-model", hidden: true })).toBeTruthy();
  expect(screen.queryByRole("option", { name: "gpt-5.4-mini", hidden: true })).toBeNull();
});

it("creates a topic-based series by skipping optional characters", async () => {
  const onSave = vi.fn();
  render(<SeriesProfileForm onSave={onSave} />);
  fireEvent.change(screen.getByLabelText("Series name"), { target: { value: "Everyday science" } });
  fireEvent.change(screen.getByLabelText("What is this series about?"), { target: { value: "A different science topic each week" } });
  fireEvent.click(screen.getByRole("button", { name: "Continue to cast" }));
  fireEvent.click(screen.getByRole("button", { name: "Continue without characters" }));
  expect(screen.getByRole("heading", { name: "Ready for your first episode?" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Create series" }));
  await waitFor(() => expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ cast: [], characters: "", story_format: "GENERAL" })));
  expect(api.draftCharacterDescription).not.toHaveBeenCalled();
});
