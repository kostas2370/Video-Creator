// @vitest-environment happy-dom
import React from "react";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { IdeaGenerator } from "./IdeaGenerator";
import { SeriesProfileForm } from "./SeriesProfileForm";
import Home from "../pages/HomePage";
import AuthContext from "../store/AuthContext";
import * as api from "../api/apiService";

vi.mock("../hooks/useAxiosPrivate", () => ({ useAxiosPrivate: () => ({}) }));
vi.mock("../api/apiService", async importOriginal => ({ ...await importOriginal(), generateIdeas: vi.fn(), getGenerationModels: vi.fn(), getAvatars: vi.fn(), getTemplates: vi.fn(), getVoices: vi.fn(), getIntro: vi.fn(), getOutro: vi.fn(), getCustomVisualProviders: vi.fn(), generateVideo: vi.fn() }));

const ideas = [
  { title: "The Borrowed Moon", prompt: "A fox borrows the moon and must return it before dawn." },
  { title: "The Last Lighthouse", prompt: "A tiny lighthouse guides lost clouds home." },
  { title: "The Midnight Market", prompt: "Two unlikely friends solve a fresh market mystery each week." },
];
const wrap = element => <MemoryRouter><AuthContext.Provider value={{ user: { id: "alice" } }}>{element}</AuthContext.Provider></MemoryRouter>;
const openHelper = () => fireEvent.click(screen.queryByRole("button", { name: "Find ideas" }) || screen.getByText("Need an idea? Let AI suggest a few"));
beforeEach(() => {
  vi.clearAllMocks(); localStorage.clear();
  api.generateIdeas.mockResolvedValue({ ok: true, data: { ideas } });
  [api.getAvatars, api.getTemplates, api.getVoices, api.getIntro, api.getOutro].forEach(fn => fn.mockResolvedValue({ ok: true, data: { results: [], next: null } }));
  api.getGenerationModels.mockResolvedValue({ ok: true, data: { script_models: { OPENAI: ["gpt-5.4-mini"] }, default_script_model: "gpt-5.4-mini" } });
  api.getCustomVisualProviders.mockResolvedValue({ ok: true, data: [] });
});
afterEach(() => { cleanup(); localStorage.clear(); vi.restoreAllMocks(); });

it("suggests from a blank topic and applies only the chosen proposal", async () => {
  const useIdea = vi.fn();
  render(<IdeaGenerator kind="video" onUse={useIdea} />);
  openHelper();
  fireEvent.click(screen.getByRole("button", { name: "Suggest video ideas" }));
  await screen.findByRole("heading", { name: ideas[0].title });
  expect(api.generateIdeas).toHaveBeenCalledWith({ kind: "video", seed: "" });
  expect(useIdea).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: `Use idea: ${ideas[1].title}` }));
  expect(useIdea).toHaveBeenCalledWith(ideas[1]);
  expect(screen.getByText("Need an idea? Let AI suggest a few").closest("details").open).toBe(false);
});

it("uses current input as inspiration and lets an explicit topic take priority", async () => {
  render(<IdeaGenerator kind="series" seed="Fox mysteries" preferences={{ story_format: "ANIMATED_STORY" }} onUse={vi.fn()} />);
  openHelper();
  fireEvent.change(screen.getByLabelText(/Topic or inspiration/), { target: { value: "Space detectives" } });
  fireEvent.click(screen.getByRole("button", { name: "Suggest series ideas" }));
  await screen.findByRole("heading", { name: ideas[0].title });
  expect(api.generateIdeas).toHaveBeenCalledWith({ kind: "series", seed: "Space detectives", story_format: "ANIMATED_STORY" });
});

it("preserves the existing video prompt until selection and restores proposals after reopening", async () => {
  const first = render(wrap(<Home />));
  fireEvent.change(screen.getByLabelText("Your prompt"), { target: { value: "My original idea" } });
  openHelper();
  fireEvent.click(screen.getByRole("button", { name: "Suggest video ideas" }));
  await screen.findByRole("heading", { name: ideas[0].title });
  expect(screen.getByLabelText("Your prompt").value).toBe("My original idea");
  expect(api.generateIdeas.mock.calls[0][0].seed).toBe("My original idea");
  first.unmount();
  render(wrap(<Home />));
  expect(screen.getByRole("heading", { name: ideas[0].title })).toBeTruthy();
  expect(api.generateIdeas).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole("button", { name: `Use idea: ${ideas[0].title}` }));
  expect(screen.getByLabelText("Your prompt").value).toBe(ideas[0].prompt);
  expect(api.generateVideo).not.toHaveBeenCalled();
});

it("fills the series name and premise without saving or changing the cast", async () => {
  const onSave = vi.fn();
  const first = render(wrap(<SeriesProfileForm onSave={onSave} />));
  openHelper();
  fireEvent.click(screen.getByRole("button", { name: "Suggest series ideas" }));
  await screen.findByRole("heading", { name: ideas[0].title });
  first.unmount();
  render(wrap(<SeriesProfileForm onSave={onSave} />));
  expect(screen.getByRole("heading", { name: ideas[0].title })).toBeTruthy();
  expect(api.generateIdeas).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole("button", { name: `Use idea: ${ideas[2].title}` }));
  expect(screen.getByLabelText("Series name").value).toBe(ideas[2].title);
  expect(screen.getByLabelText("What is this series about?").value).toBe(ideas[2].prompt);
  expect(onSave).not.toHaveBeenCalled();
});

it("prevents duplicate requests and recovers from failures without discarding proposals", async () => {
  let finish;
  api.generateIdeas.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  render(<IdeaGenerator kind="video" onUse={vi.fn()} />);
  openHelper();
  fireEvent.click(screen.getByRole("button", { name: "Suggest video ideas" }));
  expect(screen.getByRole("button", { name: "Finding ideas…" }).disabled).toBe(true);
  await act(async () => finish({ ok: true, data: { ideas } }));
  api.generateIdeas.mockResolvedValueOnce({ ok: false, message: "Provider unavailable" });
  fireEvent.click(screen.getByRole("button", { name: "Suggest more ideas" }));
  await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("Provider unavailable"));
  expect(screen.getByRole("heading", { name: ideas[0].title })).toBeTruthy();
});
