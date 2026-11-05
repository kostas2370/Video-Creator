// @vitest-environment happy-dom
import React from "react";
import { act, cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Track } from "./VideoPreview";
let ready, ended, paused, play;
beforeEach(() => {
  ready = 2; ended = false; paused = true;
  vi.spyOn(HTMLMediaElement.prototype, "readyState", "get").mockImplementation(() => ready);
  vi.spyOn(HTMLMediaElement.prototype, "duration", "get").mockReturnValue(4);
  vi.spyOn(HTMLMediaElement.prototype, "ended", "get").mockImplementation(() => ended);
  vi.spyOn(HTMLMediaElement.prototype, "paused", "get").mockImplementation(() => paused);
  play = vi.spyOn(HTMLMediaElement.prototype, "play").mockImplementation(() => { paused = false; return Promise.resolve(); });
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => { paused = true; });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const props = () => ({ source: "/voice.mp3", time: 0, duration: 5, playing: true, muted: false, seekVersion: 0, onBuffering: vi.fn(), onFailure: vi.fn(), onBlocked: vi.fn() });
it("waits for buffered media before starting instead of repeatedly playing and pausing", () => {
  const settings = props();
  const view = render(<Track {...settings} />);
  expect(play).not.toHaveBeenCalled();
  expect(settings.onBuffering.mock.calls.at(-1)[1]).toBe(true);
  ready = 4;
  fireEvent.canPlay(view.container.querySelector("audio"));
  expect(settings.onBuffering.mock.calls.at(-1)[1]).toBe(false);
  expect(play).toHaveBeenCalledTimes(1);
  fireEvent.canPlay(view.container.querySelector("audio"));
  expect(play).toHaveBeenCalledTimes(1);
});
it("holds completed narration instead of restarting it when the timeline lasts longer", () => {
  ready = 4; ended = true;
  render(<Track {...props()} time={4.2} />);
  expect(play).not.toHaveBeenCalled();
});
it("keeps a ready track paused until the other tracks finish buffering", () => {
  ready = 4;
  const settings = props();
  const view = render(<Track {...settings} stalled />);
  expect(play).not.toHaveBeenCalled();
  view.rerender(<Track {...settings} stalled={false} />);
  expect(play).toHaveBeenCalledTimes(1);
});

it("pauses and resumes in place without seeking or rebuffering", async () => {
  ready = 4;
  const settings = props();
  const view = render(<Track {...settings} time={1} />);
  await act(async () => {});
  const audio = view.container.querySelector("audio");
  audio.currentTime = 1.12;
  const seek = vi.spyOn(audio, "currentTime", "set");
  view.rerender(<Track {...settings} time={1} playing={false} />);
  expect(paused).toBe(true);
  expect(seek).not.toHaveBeenCalled();
  view.rerender(<Track {...settings} time={1} playing />);
  await act(async () => {});
  expect(paused).toBe(false);
  expect(seek).not.toHaveBeenCalled();
  expect(play).toHaveBeenCalledTimes(2);
});
it("resumes immediately after an interrupted play request settles", async () => {
  ready = 4;
  let rejectPlay;
  play.mockImplementationOnce(() => new Promise((_, reject) => { rejectPlay = reject; }));
  const settings = props();
  const view = render(<Track {...settings} />);
  view.rerender(<Track {...settings} playing={false} />);
  view.rerender(<Track {...settings} playing />);
  expect(play).toHaveBeenCalledTimes(1);
  await act(async () => { rejectPlay(new DOMException("Playback interrupted", "AbortError")); });
  expect(play).toHaveBeenCalledTimes(2);
  expect(paused).toBe(false);
});
