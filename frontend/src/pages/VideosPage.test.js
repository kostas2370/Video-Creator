import React from "react";
import { MemoryRouter } from "react-router-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Videos } from "./VideosPage";
import { getVideos } from "../api/apiService";
jest.mock("../api/apiService", () => ({
  getVideos: jest.fn()
}));
jest.mock("../hooks/useDebounce", () => ({
  useDebounce: value => value
}));
jest.mock("../components/Table", () => ({
  DefaultTable: ({
    data
  }) => <div>{data.map(item => <p key={item.id}>{item.title}</p>)}</div>
}));
beforeEach(() => jest.resetAllMocks());
test("search resets pagination and ignores stale library responses", async () => {
  let resolveOld;
  getVideos.mockImplementation(term => term ? Promise.resolve(result({
    results: [{
      id: 3,
      title: "Solar story"
    }],
    count: 1
  })) : new Promise(resolve => {
    resolveOld = resolve;
  }));
  render(<MemoryRouter initialEntries={["/videos?page=4"]}><Videos /></MemoryRouter>);
  fireEvent.change(screen.getByRole("searchbox", {
    name: "Search videos"
  }), {
    target: {
      value: "solar"
    }
  });
  expect(await screen.findByText("Solar story")).toBeInTheDocument();
  expect(getVideos).toHaveBeenLastCalledWith("solar", 1);
  resolveOld(result({
    results: [{
      id: 9,
      title: "Old results"
    }],
    count: 1
  }));
  await waitFor(() => expect(screen.queryByText("Old results")).not.toBeInTheDocument());
  expect(screen.getByText("Page 1")).toBeInTheDocument();
});
test("empty search can be cleared and the library can be retried after a failure", async () => {
  getVideos.mockResolvedValueOnce(result(undefined)).mockResolvedValue(result({
    results: [],
    count: 0
  }));
  render(<MemoryRouter initialEntries={["/videos?search=nothing"]}><Videos /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", {
    name: "Try again"
  }));
  expect(await screen.findByText("No matching videos")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {
    name: "Clear search"
  }));
  expect(await screen.findByText("Your first video starts with an idea")).toBeInTheDocument();
});
function result(data) {
  return {
    ok: data !== undefined,
    data: data ?? null
  };
}
