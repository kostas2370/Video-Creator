// @vitest-environment happy-dom
import React, { useState } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { SeriesCastEditor } from "./SeriesCastEditor";

afterEach(cleanup);

function CastForm() {
  const [cast, setCast] = useState([]);
  return <><SeriesCastEditor cast={cast} onChange={setCast} /><output>{JSON.stringify(cast)}</output></>;
}

it("adds and edits distinct characters without changing another character's identity", () => {
  const { container } = render(<CastForm />);
  fireEvent.click(screen.getByRole("button", { name: "Add character" }));
  fireEvent.change(screen.getByLabelText("Character 1 name"), { target: { value: "Milo" } });
  fireEvent.change(screen.getByLabelText("Fixed appearance"), { target: { value: "Orange fox" } });
  fireEvent.change(screen.getByLabelText("Default wardrobe"), { target: { value: "Teal scarf" } });
  const original = JSON.parse(container.querySelector("output").textContent)[0];
  fireEvent.click(screen.getByRole("button", { name: "Add character" }));
  fireEvent.change(screen.getByLabelText("Character 2 name"), { target: { value: "Rin" } });
  let cast = JSON.parse(container.querySelector("output").textContent);
  expect(cast[0]).toEqual(original);
  expect(cast[1].id).not.toBe(original.id);
  fireEvent.click(screen.getByRole("button", { name: "Edit character Milo" }));
  fireEvent.click(screen.getByRole("button", { name: "Remove character 1" }));
  cast = JSON.parse(container.querySelector("output").textContent);
  expect(cast).toHaveLength(1);
  expect(cast[0].name).toBe("Rin");
});

it("limits the cast to six characters and makes room after removal", () => {
  render(<CastForm />);
  const add = screen.getByRole("button", { name: "Add character" });
  for (let index = 0; index < 6; index += 1) fireEvent.click(add);
  expect(add.disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Edit character 3", exact: true }));
  fireEvent.click(screen.getByRole("button", { name: "Remove character 3" }));
  expect(add.disabled).toBe(false);
});
