const withMT = require("@material-tailwind/react/utils/withMT");
 
module.exports = withMT({
  // "class" because hooks/useTheme puts `.dark` on <html>. It still starts from the
  // OS preference and keeps following it until the user uses the toggle, so the
  // dark: utilities behave as before for anyone who never touches it.
  darkMode: 'class',
  // Resolved from this file's directory. The sources live under src/, so the previous
  // "./pages/**" and "./components/**" matched nothing and no utilities were generated.
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
    "./public/index.html",
  ],
  theme: {
    extend: {
      padding: { '6': '2rem' },
      // The markup uses primary-300/500/600 in about a hundred places — focus rings,
      // borders, buttons — but `primary` was never defined, so none of those classes
      // generated any CSS. Blue matches the blue-* shades used alongside them.
      colors: { primary: require('tailwindcss/colors').blue },
    },
  },
  plugins: [],
});