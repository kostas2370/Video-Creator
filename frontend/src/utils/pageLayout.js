export const hasEmbeddedFooter = pathname => /^\/(login|register)\/?$/.test(pathname);
export const isVideoEditorPath = pathname => /^\/videos\/[^/]+\/?$/.test(pathname);

export function pageLayout(pathname, authenticated) {
  const publicShell = (pathname === "/" && !authenticated) || /^\/(privacy|terms|contact)\/?$/.test(pathname)
    || /^\/share\/[^/]+\/?$/.test(pathname);
  const publicHelp = /^\/(guide|whats-new)\/?$/.test(pathname);
  const passwordRecovery = pathname.startsWith("/forgot-password")
    || pathname.startsWith("/reset-password");

  return {
    publicShell,
    showNavbar: (authenticated || !publicHelp)
      && !publicShell
      && !hasEmbeddedFooter(pathname)
      && !passwordRecovery,
  };
}
