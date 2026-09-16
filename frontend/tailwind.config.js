const withMT = require("@material-tailwind/react/utils/withMT");
 
module.exports = withMT({
  // withMT defaults this to "class", which emits `.dark\:x:is(.dark *)` — rules that
  // only apply under an ancestor carrying `.dark`. Nothing in this app ever sets that
  // class, and every dark: utility in the components was written against the OS
  // preference (the CSS previously committed to src/index.css was built with "media").
  // Keep "media" so those utilities keep working; switch to "class" only alongside a
  // real theme toggle that puts `.dark` on <html>.
  darkMode: 'media',
  // These globs are resolved from this file's directory, and every source file lives
  // under src/ — so "./pages/**" and "./components/**" matched nothing and Tailwind
  // generated no utilities at all. The app was running purely off the pre-compiled
  // CSS checked into src/index.css, which meant any class missing from that stale
  // dump (dark:bg-gray-600, dark:border-gray-500, ...) silently had no styles.
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
    "./public/index.html",
  ],
  theme: {
    extend: {padding:{'6':'2rem'}},
  },
  plugins: [],
});