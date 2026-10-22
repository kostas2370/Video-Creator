import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PublishingAccounts } from "./PublishingAccounts";

describe("publishing account management", () => {
  it("shows account status and reconnect/disconnect actions", () => {
    const html = renderToStaticMarkup(<PublishingAccounts connections={{
      platforms: [{ id: "youtube", name: "YouTube", configured: true }],
      accounts: [
        { id: "one", platform: "youtube", display_name: "Channel one", needs_reconnect: false },
        { id: "two", platform: "youtube", display_name: "Channel two", needs_reconnect: true },
      ],
    }} />);
    expect(html).toContain("Connected");
    expect(html).toContain("Reconnect required");
    expect(html).toContain('aria-label="Reconnect Channel two"');
    expect(html).toContain('aria-label="Disconnect Channel one"');
    expect(html).toContain("Connect another account");
  });
  it("disables connecting when the platform is not configured", () => {
    const html = renderToStaticMarkup(<PublishingAccounts connections={{
      platforms: [{ id: "youtube", name: "YouTube", configured: false, setup_message: "Setup needed" }],
      accounts: [],
    }} />);
    expect(html).toContain("Setup needed");
    expect(html).toMatch(/<button[^>]*disabled=""/);
    expect(html).toContain("Connect YouTube");
  });
  it("keeps every account action disabled while a connection is changing", () => {
    const html = renderToStaticMarkup(<PublishingAccounts busy="youtube" connections={{
      platforms: [{ id: "youtube", name: "YouTube", configured: true }],
      accounts: [{ id: "one", platform: "youtube", display_name: "Channel one", needs_reconnect: true }],
    }} />);
    expect(html).toContain("Needs attention");
    expect(html).toContain("Opening connection…");
    const buttons = html.match(/<button[^>]*>/g);
    expect(buttons).toHaveLength(3);
    expect(buttons.every(button => button.includes('disabled=""'))).toBe(true);
  });

});
