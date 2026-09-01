import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";

import { chromium } from "playwright-core";
import { createServer } from "vite";

const host = "127.0.0.1";
const port = 5174;
const resultsDirectory = resolve("test-results");
const server = await createServer({
  server: { host, port, strictPort: true },
});

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

await mkdir(resultsDirectory, { recursive: true });
await server.listen();

const launchOptions = { headless: true };
if (process.env.PLAYWRIGHT_CHROME_PATH) {
  launchOptions.executablePath = process.env.PLAYWRIGHT_CHROME_PATH;
} else {
  launchOptions.channel = "chrome";
}

const browser = await chromium.launch(launchOptions);
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const consoleErrors = [];
page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});

try {
  await page.goto(`http://${host}:${port}/`, { waitUntil: "networkidle" });
  assert((await page.locator(".validation-state strong").innerText()) === "Registry valid", "Default registry should be valid");
  assert(!(await page.locator("#download-file").isDisabled()), "Download should be enabled for a valid registry");
  assert((await page.locator(".comparison-item").count()) === 1, "Default registry should contain one comparison");

  const overflowAt = async (width, height) => {
    await page.setViewportSize({ width, height });
    await page.waitForTimeout(80);
    return page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  };

  assert(!(await overflowAt(1440, 1000)), "Desktop layout should not overflow horizontally");
  await page.screenshot({ path: resolve(resultsDirectory, "editor-desktop.png"), fullPage: true });

  const leftConnection = page.locator('[data-field="left.connection"]');
  await leftConnection.fill("");
  assert((await page.locator(".validation-state strong").innerText()).includes("issue"), "Blank required field should produce an issue");
  assert(await page.locator("#download-file").isDisabled(), "Invalid registry should disable download");
  assert(await page.locator('[data-field="left.connection"]').getAttribute("aria-invalid") === "true", "Invalid field should be announced");

  await leftConnection.fill("oracle_prod");
  assert((await page.locator(".validation-state strong").innerText()) === "Registry valid", "Corrected field should restore valid state");

  await page.locator("#add-comparison").click();
  assert((await page.locator(".comparison-item").count()) === 2, "Add comparison should create a second registry entry");
  assert(await page.locator("#download-file").isDisabled(), "Incomplete new comparison should block download");

  await page.reload({ waitUntil: "networkidle" });
  assert(!(await overflowAt(768, 900)), "Tablet layout should not overflow horizontally");
  await page.screenshot({ path: resolve(resultsDirectory, "editor-tablet.png"), fullPage: true });
  assert(!(await overflowAt(390, 844)), "Mobile layout should not overflow horizontally");
  assert(await page.locator("#open-file").isVisible(), "Open action should remain visible on mobile");
  assert(await page.locator("#download-file").isVisible(), "Download action should remain visible on mobile");
  await page.screenshot({ path: resolve(resultsDirectory, "editor-mobile.png"), fullPage: true });

  assert(consoleErrors.length === 0, `Console errors: ${consoleErrors.join("; ")}`);
  console.log("Browser smoke test passed at 1440px, 768px, and 390px.");
} finally {
  await browser.close();
  await server.close();
}
