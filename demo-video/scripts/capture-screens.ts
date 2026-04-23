/**
 * capture-screens.ts
 *
 * Playwright script that records two videos of the live Kvitly app:
 *   1. form-capture.webm  — upload form interaction
 *   2. dashboard-capture.webm — dashboard browsing
 *
 * Saves both to ../public/ so Remotion can reference them via staticFile().
 *
 * Run with:
 *   npm run capture
 *   (which runs: ts-node --project tsconfig.json scripts/capture-screens.ts)
 *
 * Prerequisites:
 *   - Flask app running on http://localhost:5000
 *   - npx playwright install chromium (first time only)
 */

import { chromium } from "playwright";
import * as path from "path";
import * as fs from "fs";

const BASE_URL = "http://localhost:5000";
const PUBLIC_DIR = path.resolve(__dirname, "../public");

// Dashboard password — must match DASHBOARD_PASSWORD env var in Flask
const DASHBOARD_PASSWORD = "Tsv89vzc";

async function ensurePublicDir(): Promise<void> {
  if (!fs.existsSync(PUBLIC_DIR)) {
    fs.mkdirSync(PUBLIC_DIR, { recursive: true });
    console.log(`Created directory: ${PUBLIC_DIR}`);
  }
}

async function captureFormVideo(): Promise<void> {
  console.log("\n[1/2] Capturing form interaction...");

  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    recordVideo: {
      dir: PUBLIC_DIR,
      size: { width: 1920, height: 1080 },
    },
  });

  const page = await context.newPage();

  try {
    // Navigate to the form
    console.log(`  Navigating to ${BASE_URL}/`);
    await page.goto(`${BASE_URL}/`, { waitUntil: "networkidle" });
    await page.waitForTimeout(800);

    // Fill in the name field
    console.log("  Filling in name: Anders");
    const nameField = page.locator(
      'input[name="name"], input[placeholder*="navn"], input[placeholder*="Navn"], #name'
    );
    await nameField.first().click();
    await page.waitForTimeout(300);
    // Type slowly for visual effect
    await nameField.first().type("Anders", { delay: 120 });
    await page.waitForTimeout(600);

    // Select payment type "Eget udlæg"
    console.log("  Selecting payment type: Eget udlæg");
    // Try radio button first, then select element
    const egetUdlaegRadio = page.locator(
      'input[type="radio"][value*="udl"], input[type="radio"][value*="Udl"], label:has-text("Eget udlæg") input'
    );
    const radioCount = await egetUdlaegRadio.count();
    if (radioCount > 0) {
      await egetUdlaegRadio.first().click();
    } else {
      // Try clicking the label text
      const label = page.locator('label:has-text("Eget udlæg")');
      if ((await label.count()) > 0) {
        await label.first().click();
      }
    }
    await page.waitForTimeout(500);

    // Choose udvalg from dropdown — use "Aktivitetsudvalg"
    console.log("  Choosing udvalg: Aktivitetsudvalg");
    const udvalgSelect = page.locator(
      'select[name="udvalg"], select#udvalg, select:has(option:text("udvalg"))'
    );
    const selectCount = await udvalgSelect.count();
    if (selectCount > 0) {
      await udvalgSelect.first().selectOption({ label: "Aktivitetsudvalg" });
    } else {
      // Might be a custom dropdown
      const udvalgButton = page.locator('button:has-text("udvalg"), [data-udvalg]');
      if ((await udvalgButton.count()) > 0) {
        await udvalgButton.first().click();
        await page.waitForTimeout(300);
        const option = page.locator(
          'li:has-text("Aktivitetsudvalg"), option:has-text("Aktivitetsudvalg")'
        );
        if ((await option.count()) > 0) {
          await option.first().click();
        }
      }
    }
    await page.waitForTimeout(1000);

    // Scroll down slightly to show the submit area
    await page.evaluate(() => window.scrollBy(0, 200));
    await page.waitForTimeout(800);

    // Scroll back up
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(600);

    console.log("  Form capture complete.");
  } catch (err) {
    console.error("  Error during form capture:", err);
  } finally {
    // Close context to flush the video to disk
    await context.close();
    await browser.close();
  }

  // Rename the auto-generated video file to form-capture.webm
  const videoFiles = fs
    .readdirSync(PUBLIC_DIR)
    .filter((f) => f.endsWith(".webm") && f !== "form-capture.webm" && f !== "dashboard-capture.webm")
    .map((f) => ({
      name: f,
      mtime: fs.statSync(path.join(PUBLIC_DIR, f)).mtimeMs,
    }))
    .sort((a, b) => b.mtime - a.mtime);

  if (videoFiles.length > 0 && videoFiles[0]) {
    const src = path.join(PUBLIC_DIR, videoFiles[0].name);
    const dest = path.join(PUBLIC_DIR, "form-capture.webm");
    if (fs.existsSync(dest)) fs.unlinkSync(dest);
    fs.renameSync(src, dest);
    console.log(`  Saved: ${dest}`);
  } else {
    console.warn(
      "  Warning: no .webm file found in public/ after form capture."
    );
  }
}

async function captureDashboardVideo(): Promise<void> {
  console.log("\n[2/2] Capturing dashboard interaction...");

  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    recordVideo: {
      dir: PUBLIC_DIR,
      size: { width: 1920, height: 1080 },
    },
  });

  const page = await context.newPage();

  try {
    // Navigate to dashboard login
    console.log(`  Navigating to ${BASE_URL}/dashboard/login`);
    await page.goto(`${BASE_URL}/dashboard/login`, {
      waitUntil: "networkidle",
    });
    await page.waitForTimeout(600);

    // Fill in password and submit
    console.log("  Submitting dashboard password...");
    const passwordField = page.locator(
      'input[type="password"], input[name="password"]'
    );
    await passwordField.first().fill(DASHBOARD_PASSWORD);
    await page.waitForTimeout(300);

    // Submit the form
    const submitButton = page.locator(
      'button[type="submit"], input[type="submit"], button:has-text("Log ind"), button:has-text("Adgang")'
    );
    const submitCount = await submitButton.count();
    if (submitCount > 0) {
      await submitButton.first().click();
    } else {
      await passwordField.first().press("Enter");
    }

    // Wait for dashboard to load
    console.log("  Waiting for dashboard to load...");
    await page.waitForURL(`${BASE_URL}/dashboard`, { timeout: 10000 });
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1200);

    // Click on "Udgifter" tab if present
    console.log("  Looking for Udgifter tab...");
    const udgifterTab = page.locator(
      'button:has-text("Udgifter"), a:has-text("Udgifter"), [data-tab="udgifter"]'
    );
    const tabCount = await udgifterTab.count();
    if (tabCount > 0) {
      await udgifterTab.first().click();
      await page.waitForTimeout(800);
    } else {
      console.log("  No Udgifter tab found, continuing...");
    }

    // Slow scroll through the table
    console.log("  Scrolling through table...");
    for (let i = 0; i < 5; i++) {
      await page.evaluate(() => window.scrollBy({ top: 180, behavior: "smooth" }));
      await page.waitForTimeout(500);
    }
    await page.waitForTimeout(600);

    // Try to click a table row to expand receipt detail
    console.log("  Clicking a table row...");
    const tableRow = page.locator(
      "table tbody tr, .expense-row, [data-expense], .receipt-row"
    );
    const rowCount = await tableRow.count();
    if (rowCount > 0) {
      await tableRow.first().click();
      await page.waitForTimeout(1000);
    } else {
      console.log("  No table rows found, scrolling back to top...");
    }

    // Scroll back to top
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
    await page.waitForTimeout(800);

    console.log("  Dashboard capture complete.");
  } catch (err) {
    console.error("  Error during dashboard capture:", err);
  } finally {
    await context.close();
    await browser.close();
  }

  // Rename to dashboard-capture.webm
  const videoFiles = fs
    .readdirSync(PUBLIC_DIR)
    .filter(
      (f) =>
        f.endsWith(".webm") &&
        f !== "form-capture.webm" &&
        f !== "dashboard-capture.webm"
    )
    .map((f) => ({
      name: f,
      mtime: fs.statSync(path.join(PUBLIC_DIR, f)).mtimeMs,
    }))
    .sort((a, b) => b.mtime - a.mtime);

  if (videoFiles.length > 0 && videoFiles[0]) {
    const src = path.join(PUBLIC_DIR, videoFiles[0].name);
    const dest = path.join(PUBLIC_DIR, "dashboard-capture.webm");
    if (fs.existsSync(dest)) fs.unlinkSync(dest);
    fs.renameSync(src, dest);
    console.log(`  Saved: ${dest}`);
  } else {
    console.warn(
      "  Warning: no .webm file found in public/ after dashboard capture."
    );
  }
}

async function main(): Promise<void> {
  console.log("Kvitly screen capture — Playwright");
  console.log("===================================");
  console.log(`Target: ${BASE_URL}`);
  console.log(`Output: ${PUBLIC_DIR}`);

  await ensurePublicDir();

  // Check Flask is reachable
  console.log("\nChecking Flask app is running...");
  const { default: http } = await import("http");
  await new Promise<void>((resolve, reject) => {
    const req = http.get(BASE_URL, (res) => {
      console.log(`  Flask responded: HTTP ${res.statusCode}`);
      res.resume();
      resolve();
    });
    req.on("error", (err) => {
      reject(
        new Error(
          `Flask app not reachable at ${BASE_URL}.\n` +
            `Make sure it's running: python app.py\n` +
            `Original error: ${err.message}`
        )
      );
    });
    req.setTimeout(5000, () => {
      req.destroy();
      reject(new Error(`Flask app timed out at ${BASE_URL}`));
    });
  });

  await captureFormVideo();
  await captureDashboardVideo();

  console.log("\nAll captures complete.");
  console.log("Files in public/:");
  fs.readdirSync(PUBLIC_DIR).forEach((f) => {
    const size = fs.statSync(path.join(PUBLIC_DIR, f)).size;
    console.log(`  ${f} (${(size / 1024 / 1024).toFixed(1)} MB)`);
  });
}

main().catch((err) => {
  console.error("\nCapture failed:", err.message || err);
  process.exit(1);
});
