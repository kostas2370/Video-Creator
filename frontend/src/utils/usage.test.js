import { describe, expect, it } from "vitest";
import { tokenMetric } from "./usage";

describe("token reporting", () => {
  it("shows known input even when output and total are unavailable", () => {
    const row = { requests: 1, input_tokens: 12, output_tokens: null, total_tokens: null,
      requests_with_input_tokens: 1, requests_with_output_tokens: 0, requests_with_tokens: 0 };
    expect(tokenMetric(row, "input_tokens")).toEqual({ label: "12", note: null });
    expect(tokenMetric(row, "output_tokens").label).toBe("Unavailable");
    expect(tokenMetric(row, "total_tokens").label).toBe("Unavailable");
  });
  it("shows a reported total without inventing its components", () => {
    const row = { requests: 1, input_tokens: null, output_tokens: null, total_tokens: 20,
      requests_with_input_tokens: 0, requests_with_output_tokens: 0, requests_with_tokens: 1 };
    expect(tokenMetric(row, "input_tokens").label).toBe("Unavailable");
    expect(tokenMetric(row, "total_tokens").label).toBe("20");
  });
  it("shows zero as measured and marks partial coverage for each metric", () => {
    expect(tokenMetric({ requests: 2, input_tokens: 0, requests_with_input_tokens: 1 }, "input_tokens"))
      .toEqual({ label: "0", note: "1 of 2 requests reported" });
    expect(tokenMetric({ requests: 0, total_tokens: 0, requests_with_tokens: 0 }, "total_tokens"))
      .toEqual({ label: "0", note: null });
  });
});
