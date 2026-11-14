import { beforeEach, expect, it, vi } from "vitest";

let publicClient;
let privateClient;
let calls;
let sequence;

beforeEach(async () => {
  vi.resetModules();
  const clients = await import("./axiosPrivate");
  publicClient = clients.axiosInstance;
  privateClient = clients.axiosPrivateInstance;
  calls = [];
  sequence = 0;
  const adapter = async config => {
    calls.push(config);
    return {
      status: 200, statusText: "OK", config, data: {},
      headers: config.url === "csrf/" ? { "x-csrftoken": `token-${++sequence}` }
        : config.url === "login/" ? { "x-csrftoken": "rotated-token" } : {},
    };
  };
  publicClient.defaults.adapter = adapter;
  privateClient.defaults.adapter = adapter;
});

it("bootstraps CSRF before login and uses the rotated token for private writes", async () => {
  await publicClient.post("login/", {});
  expect(calls.map(call => call.url)).toEqual(["csrf/", "login/"]);
  expect(calls[1].headers["X-CSRFToken"]).toBe("token-1");
  await privateClient.patch("videos/1/", {});
  expect(calls[2].headers["X-CSRFToken"]).toBe("rotated-token");
});

it("bootstraps refresh after reload and deduplicates simultaneous writes", async () => {
  await Promise.all([publicClient.post("token/refresh/"), privateClient.delete("videos/1/")]);
  expect(calls.filter(call => call.url === "csrf/")).toHaveLength(1);
  for (const call of calls.filter(call => call.url !== "csrf/")) {
    expect(call.headers["X-CSRFToken"]).toBe("token-1");
  }
});

it("safe reads need no CSRF bootstrap", async () => {
  await privateClient.get("videos/");
  expect(calls.map(call => call.url)).toEqual(["videos/"]);
});
