// The Halomark mark, as plain geometry on a 64-unit grid. One source for the app (components/ui.tsx)
// and for the icon generator (scripts/make-brand-assets.cjs), so the logo and the icons can't drift apart.
//
// What it is: a hallmark punch (the cut-corner field an assay office strikes into gold) with a halo
// struck into it. Construction:
//   punch  64 x 64 square, corners cut at 45 degrees 12 units in, each vertex eased by 1.6 units
//   halo   outer ellipse 22.5 x 15 turned -20 degrees about the centre (32, 32);
//          inner ellipse 14.6 x 6.6 turned -31 degrees, centred 3 right and 3.2 up, so the band is
//          heavy at the lower left and fine at the upper right, like a stamp struck slightly off square.

export const MARK_SIZE = 64;

export const MARK_PUNCH =
  "M10.87 1.13Q12 0 13.6 0L50.4 0Q52 0 53.13 1.13L62.87 10.87Q64 12 64 13.6L64 50.4Q64 52 62.87 53.13L53.13 62.87Q52 64 50.4 64L13.6 64Q12 64 10.87 62.87L1.13 53.13Q0 52 0 50.4L0 13.6Q0 12 1.13 10.87Z";

export const MARK_HALO_OUTER =
  "M10.86 39.7C8.02 31.91 15.19 22.15 26.87 17.9C38.55 13.65 50.31 16.52 53.14 24.3C55.98 32.09 48.81 41.85 37.13 46.1C25.45 50.35 13.69 47.48 10.86 39.7Z";

export const MARK_HALO_INNER =
  "M22.49 36.32C20.61 33.2 24.69 27.3 31.6 23.14C38.51 18.99 45.64 18.16 47.51 21.28C49.39 24.4 45.31 30.3 38.4 34.46C31.49 38.61 24.36 39.44 22.49 36.32Z";

/** The halo alone: fill with fill-rule="evenodd". */
export const MARK_HALO = MARK_HALO_OUTER + MARK_HALO_INNER;

/** The whole mark in one colour (the halo is cut out of the punch): fill with fill-rule="evenodd". */
export const MARK_PATH = MARK_PUNCH + MARK_HALO;

/** Brand colours: stamp-pad blue on paper. Kept here for the icons; the app reads them from globals.css. */
export const BRAND_BLUE = "#1f3bd0";
export const BRAND_BLUE_ON_DARK = "#8fa0ff";
export const BRAND_PAPER = "#eeeeea";
export const BRAND_INK = "#0e0f0e";
