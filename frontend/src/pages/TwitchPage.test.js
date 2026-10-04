import React from "react";
import { MemoryRouter } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import Twitch from "./TwitchPage";
import { generateTwitchVideo } from "../api/apiService";
jest.mock("../api/apiService", () => ({generateTwitchVideo:jest.fn()}));
test("disabled Twitch page does not expose a generation form", () => {
  render(<MemoryRouter><Twitch /></MemoryRouter>);
  expect(screen.getByRole("heading",{name:"Twitch generation is temporarily unavailable"})).toBeInTheDocument();
  expect(screen.getByRole("link",{name:"Create a video"})).toHaveAttribute("href","/");
  expect(generateTwitchVideo).not.toHaveBeenCalled();
});
