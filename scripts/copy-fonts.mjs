import { copyFileSync, mkdirSync } from "node:fs";
import { basename, join } from "node:path";

const destination = "sitehealth/static/fonts";

const fontFiles = [
  "@fontsource-variable/schibsted-grotesk/files/schibsted-grotesk-latin-wght-normal.woff2",
  "@fontsource-variable/schibsted-grotesk/files/schibsted-grotesk-latin-wght-italic.woff2",
  "@fontsource-variable/jetbrains-mono/files/jetbrains-mono-latin-wght-normal.woff2",
];

mkdirSync(destination, { recursive: true });
for (const file of fontFiles) {
  copyFileSync(join("node_modules", file), join(destination, basename(file)));
}
