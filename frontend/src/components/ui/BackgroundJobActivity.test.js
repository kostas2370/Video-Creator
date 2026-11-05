// @vitest-environment happy-dom
import React from "react";
import { MemoryRouter } from "react-router-dom";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { BackgroundJobActivity } from "./BackgroundJobActivity";
import { configureBackgroundJobs } from "../../api/backgroundJobs";

afterEach(() => { cleanup(); configureBackgroundJobs(""); localStorage.clear(); });
it("recovers a completed draft for review without applying it to the original form", async () => {
  localStorage.setItem("viddie:jobs:v1:reviewer", JSON.stringify([{ id: "done", label: "Story draft", pollUrl: "draft-jobs/", status: "SUCCEEDED", createdAt: Date.now(), path: "/story/", result: { title: "The lighthouse", story: "A light appeared in the distance." } }]));
  configureBackgroundJobs("reviewer");
  render(<MemoryRouter><label>Existing story<input defaultValue="My own writing" /></label><BackgroundJobActivity /></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", { name: /Generation activity/ }));
  fireEvent.click(screen.getByRole("button", { name: "View result" }));
  expect(screen.getByRole("textbox", { name: "Generated result" }).value).toContain("A light appeared in the distance.");
  expect(screen.getByRole("textbox", { name: "Generated result" }).readOnly).toBe(true);
  expect(screen.getByLabelText("Existing story").value).toBe("My own writing");
  expect(screen.getByRole("link", { name: /Open original page/ }).getAttribute("href")).toBe("/story/");
});
