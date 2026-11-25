import { expect, it } from "vitest";
import { hasEmbeddedFooter, isVideoEditorPath, pageLayout } from "./pageLayout";

it.each(["/login", "/login/", "/register", "/register/"])("keeps %s focused on its form", pathname => {
  expect(hasEmbeddedFooter(pathname)).toBe(true);
  expect(pageLayout(pathname, true).showNavbar).toBe(false);
});
it.each(["/privacy/", "/terms/", "/contact/", "/share/token/"])("uses the public palette on %s", pathname => {
  expect(pageLayout(pathname, false)).toEqual({ publicShell: true, showNavbar: false });
  expect(hasEmbeddedFooter(pathname)).toBe(false);
  expect(pageLayout(pathname, true).showNavbar).toBe(false);
});
it.each(["/guide/", "/whats-new/"])("shows app navigation on %s only when signed in", pathname => {
  expect(pageLayout(pathname, false).showNavbar).toBe(false);
  expect(pageLayout(pathname, true).showNavbar).toBe(true);
});
it("distinguishes the library, editor and password-recovery pages", () => {
  expect(isVideoEditorPath("/videos/")).toBe(false);
  expect(isVideoEditorPath("/videos/fox/")).toBe(true);
  expect(isVideoEditorPath("/videos/fox/extra")).toBe(false);
  expect(pageLayout("/videos/fox/", true).showNavbar).toBe(true);
  expect(pageLayout("/forgot-password/", false).showNavbar).toBe(false);
  expect(pageLayout("/reset-password/", true).showNavbar).toBe(false);
});

it("uses a public homepage shell only for signed-out visitors", () => {
  expect(pageLayout("/", false)).toEqual({publicShell: true, showNavbar: false});
  expect(pageLayout("/", true)).toEqual({publicShell: false, showNavbar: true});
});
