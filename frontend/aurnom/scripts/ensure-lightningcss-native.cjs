"use strict";
/* eslint-disable @typescript-eslint/no-require-imports -- CommonJS bootstrap for postinstall */

if (process.env.AURNOM_IN_NATIVE_HEAL === "1") {
  process.exit(0);
}

/**
 * After npm install, verify lightningcss can load its platform .node binding.
 * If not (common in Docker when optional deps are skipped or volumes are stale),
 * run a second npm install for the Linux gnu packages only.
 */
const { execSync } = require("child_process");
const path = require("path");

const root = path.join(__dirname, "..");

function clearLightningcssCache() {
  for (const k of Object.keys(require.cache)) {
    if (k.includes("lightningcss")) {
      delete require.cache[k];
    }
  }
}

function tryLoad() {
  try {
    clearLightningcssCache();
    require("lightningcss");
    return true;
  } catch {
    return false;
  }
}

if (tryLoad()) {
  process.exit(0);
}

let version = "1.32.0";
try {
  version = require(path.join(root, "node_modules/lightningcss/package.json")).version;
} catch {
  /* lightningcss missing entirely */
}

const healEnv = {
  ...process.env,
  NPM_CONFIG_IGNORE_SCRIPTS: "true",
  AURNOM_IN_NATIVE_HEAL: "1",
};

try {
  execSync(
    `npm install lightningcss-linux-arm64-gnu@${version} lightningcss-linux-x64-gnu@${version} --no-save --no-audit --no-fund`,
    { stdio: "inherit", env: healEnv, cwd: root },
  );
} catch (e) {
  console.error("[aurnom] ensure-lightningcss-native: heal install failed:", e.message);
  process.exit(1);
}

if (!tryLoad()) {
  console.error(
    "[aurnom] lightningcss still cannot load after installing linux-gnu natives. " +
      "Wipe the Docker node_modules volume or run npm ci on Linux arm64.",
  );
  process.exit(1);
}
