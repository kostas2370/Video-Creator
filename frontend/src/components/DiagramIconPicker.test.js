// @vitest-environment happy-dom
import React, { useState } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { getIcons, uploadIcon } from "../api/apiService";
import { DiagramIconPicker } from "./DiagramIconPicker";
import { DiagramLayer } from "./DiagramLayer";

vi.mock("../api/apiService", () => ({ getIcons: vi.fn(), uploadIcon: vi.fn() }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
const droplet = { key: "lucide:droplet", name: "Droplet", collection: "lucide", file: "/media/droplet.svg", description: "Water" };
const reply = (results = [droplet], extra = {}) => ({ ok: true, data: { results, current: 1, count: results.length, next: null, previous: null, ...extra } });

it("searches the catalog, selects an icon, and allows removing it", async () => {
  getIcons.mockResolvedValue(reply());
  function Picker() {
    const [value, setValue] = useState("");
    return <DiagramIconPicker index={0} value={value} onChange={setValue} />;
  }
  render(<Picker />);
  fireEvent.click(screen.getByRole("button", { name: "Icon for item 1: None" }));
  fireEvent.change(screen.getByLabelText("Search icons for item 1"), { target: { value: "water" } });
  await waitFor(() => expect(getIcons).toHaveBeenCalledWith({ search: "water", page: 1 }));
  fireEvent.click(await screen.findByRole("button", { name: "Droplet (lucide)" }));
  fireEvent.click(await screen.findByRole("button", { name: "Icon for item 1: Droplet" }));
  fireEvent.click(screen.getByRole("button", { name: "No icon" }));
  expect(screen.getByRole("button", { name: "Icon for item 1: None" })).toBeTruthy();
});

it("pages through the full catalog and retries failed loads", async () => {
  getIcons.mockResolvedValueOnce({ ok: false, message: "Unavailable" }).mockResolvedValueOnce(reply([droplet], { count: 30, next: 2 })).mockResolvedValue(reply([], { current: 2, previous: 1, count: 30 }));
  render(<DiagramIconPicker index={0} onChange={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Icon for item 1: None" }));
  expect(await screen.findByRole("alert")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByRole("button", { name: "Droplet (lucide)" });
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() => expect(getIcons).toHaveBeenLastCalledWith({ search: "", page: 2 }));
});

it("uploads and selects a reusable icon without submitting the storyboard form", async () => {
  const custom = { ...droplet, key: "custom:one", name: "My engine", collection: "custom" };
  getIcons.mockResolvedValue(reply());
  uploadIcon.mockResolvedValue({ ok: true, data: custom });
  const changed = vi.fn(), submit = vi.fn(event => event.preventDefault());
  render(<form onSubmit={submit}><DiagramIconPicker index={0} onChange={changed} /></form>);
  fireEvent.click(screen.getByRole("button", { name: "Icon for item 1: None" }));
  fireEvent.click(screen.getByText("Upload your own icon"));
  fireEvent.change(screen.getByLabelText("Icon name for item 1"), { target: { value: "My engine" } });
  const file = new File(["image"], "engine.png", { type: "image/png" });
  fireEvent.change(screen.getByLabelText("Icon file for item 1"), { target: { files: [file] } });
  fireEvent.click(screen.getByRole("button", { name: "Upload and use icon" }));
  await waitFor(() => expect(changed).toHaveBeenCalledWith(custom.key));
  expect(uploadIcon.mock.calls[0][0].get("file")).toBe(file);
  expect(uploadIcon.mock.calls[0][0].get("name")).toBe("My engine");
  expect(submit).not.toHaveBeenCalled();
});

it("keeps upload fields after failure and lets the user retry", async () => {
  getIcons.mockResolvedValue(reply());
  uploadIcon.mockResolvedValueOnce({ ok: false, message: "Please retry" }).mockResolvedValue({ ok: true, data: { key: "custom:retry" } });
  const changed = vi.fn();
  render(<DiagramIconPicker index={0} onChange={changed} />);
  fireEvent.click(screen.getByRole("button", { name: "Icon for item 1: None" }));
  fireEvent.click(screen.getByText("Upload your own icon"));
  fireEvent.change(screen.getByLabelText("Icon name for item 1"), { target: { value: "Engine" } });
  fireEvent.change(screen.getByLabelText("Icon file for item 1"), { target: { files: [new File(["image"], "engine.webp", { type: "image/webp" })] } });
  fireEvent.click(screen.getByRole("button", { name: "Upload and use icon" }));
  expect((await screen.findByRole("alert")).textContent).toContain("Please retry");
  expect(screen.getByLabelText("Icon name for item 1").value).toBe("Engine");
  fireEvent.click(screen.getByRole("button", { name: "Upload and use icon" }));
  await waitFor(() => expect(changed).toHaveBeenCalledWith("custom:retry"));
});

it("previews only installed artwork and hides unrevealed icons", async () => {
  getIcons.mockResolvedValue(reply());
  const item = { opacity: 1, diagram: { template: "steps", items: [{ label: "Water", icon: droplet.key }, { label: "Missing", icon: "unknown:x" }] } };
  const { container, rerender } = render(<DiagramLayer item={item} time={3} duration={5} frameSize={[1080, 1920]} />);
  await waitFor(() => expect(container.querySelectorAll("img").length).toBe(1));
  expect(container.querySelector("img").getAttribute("src")).toBe(droplet.file);
  rerender(<DiagramLayer item={item} time={-1} duration={5} frameSize={[1080, 1920]} />);
  expect(container.querySelector("img")).toBeNull();
});
