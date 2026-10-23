import React from "react";
import { Link } from "react-router-dom";

export function LegalFooter() {
  return (
    <footer className="border-t border-gray-200 px-6 py-6 text-sm text-gray-500 dark:border-gray-800 dark:text-gray-400">
      <nav aria-label="Legal" className="mx-auto flex max-w-4xl flex-wrap items-center justify-center gap-x-6 gap-y-3">
        <Link className="underline underline-offset-4" to="/terms/">Terms of Service</Link>
        <Link className="underline underline-offset-4" to="/privacy/">Privacy Policy</Link>
        <Link className="underline underline-offset-4" to="/contact/">Contact us</Link>
      </nav>
    </footer>
  );
}
