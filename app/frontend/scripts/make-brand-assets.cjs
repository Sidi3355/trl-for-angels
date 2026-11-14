// Renders every Halomark brand asset from the one geometry in src/lib/mark.ts:
//
//   public/icons/icon.svg               favicon (vector; lighter blue in dark browser chrome)
//   public/icons/favicon-64.png         favicon (bitmap): the punch itself, transparent around it
//   public/icons/icon-192.png, -512.png installed-app icons: rounded tile
//   public/icons/icon-maskable-512.png  Android maskable: full bleed, mark inside the 80% safe circle
//   public/icons/apple-touch-icon.png   iOS Home Screen: full-bleed square (iOS rounds the corners)
//   src/app/opengraph-image.png         link preview (1200 x 630)
//
// Run:  node scripts/make-brand-assets.cjs
// Needs Node 22.18+ (it loads the .ts geometry directly) and Playwright's Chromium.
// The link preview is set in Archivo, which it takes from the last `next build` (.next/static/media);
// without a build it is skipped and the icons are still written.
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");
const { MARK_PUNCH, MARK_HALO, MARK_PATH, HALO_VIEWBOX, BRAND_BLUE, BRAND_PAPER, BRAND_INK } = require("../src/lib/mark.ts");

const root = path.join(__dirname, "..");
const icons = path.join(root, "public", "icons");

/** The punch in one colour with the halo in another (so the halo is never see-through). */
const punch = (field, halo) => `<path d="${MARK_PUNCH}" fill="${field}"/><path d="${MARK_HALO}" fill="${halo}" fill-rule="evenodd"/>`;

/** The app icon: a blue ground, the punch in paper, the halo showing the ground through it. */
function tile({ scale, radius = 0 }) {
  const inner = `<g transform="translate(32 32) scale(${scale}) translate(-32 -32)"><path d="${MARK_PATH}" fill="${BRAND_PAPER}" fill-rule="evenodd"/></g>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="${radius}" fill="${BRAND_BLUE}"/>${inner}</svg>`;
}

const faviconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><style>.f{fill:${BRAND_BLUE}}@media (prefers-color-scheme:dark){.f{fill:#4d68f0}}</style><path class="f" d="${MARK_PUNCH}"/><path d="${MARK_HALO}" fill="${BRAND_PAPER}" fill-rule="evenodd"/></svg>
`;

const bitmaps = [
  { file: "favicon-64.png", size: 64, svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">${punch(BRAND_BLUE, BRAND_PAPER)}</svg>`, transparent: true },
  { file: "icon-192.png", size: 192, svg: tile({ scale: 0.6, radius: 14.4 }), transparent: true },
  { file: "icon-512.png", size: 512, svg: tile({ scale: 0.6, radius: 14.4 }), transparent: true },
  // The punch's farthest point is 37.7 units from the centre; at 0.54 that is 20.4 of the 25.6-unit safe radius.
  { file: "icon-maskable-512.png", size: 512, svg: tile({ scale: 0.54 }) },
  { file: "apple-touch-icon.png", size: 180, svg: tile({ scale: 0.6 }) },
];

function archivo() {
  const dir = path.join(root, ".next", "static", "media");
  if (!fs.existsSync(dir)) return null;
  // next/font names the preloaded (latin) subset "<hash>-s.p.<hash>.woff2".
  const file = fs.readdirSync(dir).find((f) => /-s\.p\..*\.woff2$/.test(f));
  return file ? fs.readFileSync(path.join(dir, file)).toString("base64") : null;
}

function openGraph(font) {
  const stamp = (bg) => `<span style="width:76px;height:76px;background:${bg};clip-path:polygon(18.75% 0,81.25% 0,100% 18.75%,100% 81.25%,81.25% 100%,18.75% 100%,0 81.25%,0 18.75%)"></span>`;
  return `<!doctype html><style>
    @font-face{font-family:Archivo;src:url(data:font/woff2;base64,${font});font-weight:100 900;font-stretch:62% 125%}
    body{margin:0;width:1200px;height:630px;background:${BRAND_PAPER};color:${BRAND_INK};font-family:Archivo;display:flex;flex-direction:column;justify-content:space-between;box-sizing:border-box;padding:76px 84px 72px}
    .w{font-size:132px;font-weight:800;font-stretch:125%;letter-spacing:.012em;line-height:1;white-space:nowrap}
    .w svg{height:.725em;width:calc(.725em * 1.355);margin:0 .04em 0 .045em;position:relative;top:.014em}
    .t{font-size:46px;font-weight:650;letter-spacing:-.025em;line-height:1.12;max-width:17em}
    .r{display:flex;align-items:flex-end;justify-content:space-between}
    .s{display:flex;gap:14px}
    .e{font-size:19px;font-weight:650;font-stretch:116%;letter-spacing:.09em;text-transform:uppercase;color:#5b5e5a}
  </style>
  <div><div class="w">HAL<svg viewBox="${HALO_VIEWBOX}"><path d="${MARK_HALO}" fill="${BRAND_INK}" fill-rule="evenodd"/></svg>MARK</div></div>
  <div class="r"><div><div class="e">Founder screening for angel investors</div><div class="t" style="margin-top:18px">Test a founder against your bar. Get a verdict: meet, look closer or pass.</div></div>
  <div class="s">${stamp("#35d685")}${stamp("#ffb930")}${stamp("#17181a")}</div></div>`;
}

(async () => {
  fs.mkdirSync(icons, { recursive: true });
  fs.writeFileSync(path.join(icons, "icon.svg"), faviconSvg);
  const browser = await chromium.launch();
  for (const { file, size, svg, transparent } of bitmaps) {
    const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
    await page.setContent(`<!doctype html><style>html,body{margin:0;background:transparent}svg{display:block;width:${size}px;height:${size}px}</style>${svg}`);
    await page.screenshot({ path: path.join(icons, file), omitBackground: Boolean(transparent), clip: { x: 0, y: 0, width: size, height: size } });
    await page.close();
    console.log("wrote public/icons/" + file);
  }
  const font = archivo();
  if (font) {
    const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
    await page.setContent(openGraph(font));
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(root, "src", "app", "opengraph-image.png") });
    console.log("wrote src/app/opengraph-image.png");
  } else {
    console.log("skipped src/app/opengraph-image.png: run `next build` first so Archivo is available");
  }
  await browser.close();
})();
