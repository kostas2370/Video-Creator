const withMT = require("@material-tailwind/react/utils/withMT");
 
module.exports = withMT({
  // withMT defaults this to "class", which needs a `.dark` ancestor that nothing here
  // sets. Every dark: utility in the components targets the OS preference instead.
  // Switch to "class" only alongside a real toggle that puts `.dark` on <html>.
  darkMode: 'media',
  // Resolved from this file's directory. The sources live under src/, so the previous
  // "./pages/**" and "./components/**" matched nothing and no utilities were generated.
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
    "./public/index.html",
  ],
  theme: {
    extend: {padding:{'6':'2rem'}},
  },
  plugins: [],
});