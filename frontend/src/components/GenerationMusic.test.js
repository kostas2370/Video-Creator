// @vitest-environment happy-dom
import React, { useState } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { GenerationMusic } from "./GenerationMusic";

afterEach(cleanup);

it("switches between automatic music, a YouTube link, and no soundtrack", () => {
  function Form() {
    const [music, setMusic] = useState("");
    return <><GenerationMusic value={music} onChange={setMusic} /><output aria-label="Music choice">{music}</output></>;
  }
  render(<Form />);
  fireEvent.change(screen.getByLabelText("Background music YouTube link"), { target: { value: "https://youtu.be/abcdefghijk" } });
  expect(screen.getByLabelText("Music choice").textContent).toBe("https://youtu.be/abcdefghijk");
  fireEvent.click(screen.getByRole("checkbox", { name: /Auto-select music/ }));
  expect(screen.getByLabelText("Music choice").textContent).toBe("auto");
  expect(screen.queryByLabelText("Background music YouTube link")).toBeNull();
  fireEvent.click(screen.getByRole("checkbox", { name: /Auto-select music/ }));
  expect(screen.getByLabelText("Music choice").textContent).toBe("");
});

it("restores the automatic selection saved in a template or draft", () => {
  render(<GenerationMusic value="auto" onChange={() => {}} />);
  expect(screen.getByRole("checkbox", { name: /Auto-select music/ }).checked).toBe(true);
});
