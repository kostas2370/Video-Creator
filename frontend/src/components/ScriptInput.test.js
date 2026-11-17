// @vitest-environment happy-dom
import React, { useState } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { ScriptInput } from "./ScriptInput";
afterEach(cleanup);
function Harness() {
  const [value, setValue] = useState("My existing script");
  return <ScriptInput value={value} onChange={setValue} />;
}
const upload = (name, text) => fireEvent.change(screen.getByLabelText("Upload a text file to replace the script"), { target: { files: [{ name, size: text.length, arrayBuffer: async () => new TextEncoder().encode(text).buffer }] } });
it("imports Unicode text and preserves line breaks", async () => {
  render(<Harness />);
  upload("script.TXT", "Καλημέρα!\nA fox waits.");
  await waitFor(() => expect(screen.getByLabelText("Your script").value).toBe("Καλημέρα!\nA fox waits."));
});
it("keeps current text when an upload is empty, long, or not plain text", async () => {
  render(<Harness />);
  for (const [name, text] of [["script.txt", "  "], ["script.txt", "x".repeat(2001)], ["script.pdf", "binary"]]) {
    upload(name, text);
    await screen.findByRole("alert");
    expect(screen.getByLabelText("Your script").value).toBe("My existing script");
  }
});
it("keeps typing made while an upload is being read", async () => {
  render(<Harness />);
  let finish;
  fireEvent.change(screen.getByLabelText("Upload a text file to replace the script"), { target: { files: [{ name: "script.txt", size: 5, arrayBuffer: () => new Promise(resolve => { finish = resolve; }) }] } });
  fireEvent.change(screen.getByLabelText("Your script"), { target: { value: "Keep this edit" } });
  finish(new TextEncoder().encode("Old script").buffer);
  await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
  expect(screen.getByLabelText("Your script").value).toBe("Keep this edit");
});
