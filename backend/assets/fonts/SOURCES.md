# Bundled video fonts

Downloaded from the official Google Fonts repository on 2026-10-19:

- Poppins regular and bold: https://github.com/google/fonts/tree/main/ofl/poppins
- Lato regular and bold: https://github.com/google/fonts/tree/main/ofl/lato
- Bebas Neue regular: https://github.com/google/fonts/tree/main/ofl/bebasneue

Each family's SIL Open Font License is included next to the font files.
These files are also bundled in frontend/public/fonts for local browser previews.
DejaVu preview fonts in that directory mirror the renderer's fonts-dejavu-core
package and retain its accompanying license.

The renderer stages this directory next to each temporary ASS file and passes it
to libass through fontsdir. It does not depend on a system font-cache refresh.
