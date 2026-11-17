// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { NarrationInput } from "./NarrationInput";
afterEach(cleanup);
it("rejects unsupported and oversized files while keeping an existing MP3", () => {
  const onFileChange = vi.fn();
  render(<NarrationInput mode="audio" value="" file={{ name: "original.mp3" }} onFileChange={onFileChange} />);
  for (const file of [{ name: "wrong.wav", size: 20 }, { name: "large.mp3", size: 26 * 1024 * 1024 }, { name: "empty.mp3", size: 0 }]) {
    fireEvent.change(screen.getByLabelText("Your MP3"), { target: { files: [file] } });
    expect(screen.getByRole("alert").textContent).toContain("Choose a spoken MP3");
    expect(screen.getByText("original.mp3")).toBeTruthy();
    expect(onFileChange).not.toHaveBeenCalled();
  }
});
