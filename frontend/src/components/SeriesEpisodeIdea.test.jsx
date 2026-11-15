// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { EpisodeComposer } from "./SeriesWorkspacePanels";

afterEach(cleanup);

it("lets the user request and review an idea before replacing their text", () => {
  const generate = vi.fn(), use = vi.fn(), change = vi.fn(), submit = vi.fn();
  render(<EpisodeComposer profile={{ episode_count: 2 }} idea="My own idea" onGenerateIdea={generate} suggestedIdea="Milo finds a telescope" onUseIdea={use} onIdeaChange={change} onSubmit={submit} />);
  fireEvent.click(screen.getByRole("button", { name: "Generate episode idea" }));
  expect(generate).toHaveBeenCalledOnce();
  expect(screen.getByRole("textbox").value).toBe("My own idea");
  expect(change).not.toHaveBeenCalled();
  expect(submit).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Use this idea" }));
  expect(use).toHaveBeenCalledOnce();
});

it("disables idea actions while generation is running", () => {
  const { unmount } = render(<EpisodeComposer profile={{}} idea="Keep this" busy ideaGenerating suggestedIdea="Previous suggestion" />);
  expect(screen.getByRole("button", { name: "Suggesting an idea…" }).disabled).toBe(true);
  expect(screen.getByRole("button", { name: "Use this idea" }).disabled).toBe(true);
  expect(screen.getByRole("button", { name: "Draft next episode" }).disabled).toBe(true);
  expect(screen.getByRole("status").textContent).toContain("Finding a new story");
  unmount();
});
