// @vitest-environment happy-dom
import React, { useState } from "react";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PromptTools } from "./PromptTools";
import * as api from "../api/apiService";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
function Editor({ value = "A fox mystery" }) {
  const [text, setText] = useState(value);
  return <><textarea aria-label="Prompt" value={text} onChange={event => setText(event.target.value)} /><PromptTools kind="video" value={text} onUseIdea={idea => setText(idea.prompt)} onUseRewrite={setText} /></>;
}

it("opens one helper at a time and retains inputs when switching", () => {
  render(<Editor />);
  const ideas = screen.getByRole("button", { name: "Find ideas" });
  const rewrite = screen.getByRole("button", { name: "Rewrite with AI" });
  expect(ideas.getAttribute("aria-expanded")).toBe("false");
  fireEvent.click(ideas);
  fireEvent.change(screen.getByLabelText(/Topic or inspiration/), { target: { value: "Space" } });
  fireEvent.click(rewrite);
  expect(ideas.getAttribute("aria-expanded")).toBe("false");
  expect(rewrite.getAttribute("aria-expanded")).toBe("true");
  expect(screen.queryByRole("button", { name: "Suggest video ideas" })).toBeNull();
  fireEvent.click(ideas);
  expect(screen.getByLabelText(/Topic or inspiration/).value).toBe("Space");
});

it("keeps an in-progress idea request when switching and closes after choosing", async () => {
  let finish;
  const request = vi.spyOn(api, "generateIdeas").mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  render(<Editor />);
  fireEvent.click(screen.getByRole("button", { name: "Find ideas" }));
  fireEvent.click(screen.getByRole("button", { name: "Suggest video ideas" }));
  fireEvent.click(screen.getByRole("button", { name: "Rewrite with AI" }));
  await act(async () => finish({ ok: true, data: { ideas: [{ title: "Space fox", prompt: "A fox explores the moon." }] } }));
  fireEvent.click(screen.getByRole("button", { name: "Find ideas" }));
  fireEvent.click(screen.getByRole("button", { name: "Use idea: Space fox" }));
  expect(screen.getByLabelText("Prompt").value).toBe("A fox explores the moon.");
  expect(screen.getByRole("button", { name: "Find ideas" }).getAttribute("aria-expanded")).toBe("false");
  expect(request).toHaveBeenCalledOnce();
});

it("offers ideas on a blank form and enables rewriting after typing", () => {
  render(<Editor value="" />);
  const rewrite = screen.getByRole("button", { name: "Rewrite with AI" });
  expect(rewrite.disabled).toBe(true);
  expect(screen.getByRole("button", { name: "Find ideas" }).disabled).toBe(false);
  fireEvent.change(screen.getByLabelText("Prompt"), { target: { value: "A new idea" } });
  expect(rewrite.disabled).toBe(false);
});
