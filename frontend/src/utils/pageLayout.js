export const hasEmbeddedFooter = pathname => /^\/(login|register)\/?$/.test(pathname);
export const isVideoEditorPath = pathname => /^\/videos\/[^/]+\/?$/.test(pathname);

export function pageLayout(pathname, authenticated) {
  const publicHelp = /^\/(guide|whats-new)\/?$/.test(pathname);
  const publicShell = (pathname === "/" && !authenticated) || /^\/(privacy|terms|contact|request-access)\/?$/.test(pathname)
    || /^\/share\/[^/]+\/?$/.test(pathname) || (publicHelp && !authenticated);
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
