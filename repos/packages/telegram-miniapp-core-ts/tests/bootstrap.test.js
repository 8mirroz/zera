import test from "node:test";
import assert from "node:assert/strict";

import { bindNativeButton, bootstrapTelegramWebApp, getTelegramWebApp } from "../src/bootstrap.js";
import { hasRequiredInitData } from "../src/init-data.js";
import { themeParamsToCssVars } from "../src/theme.js";

test("bootstrap falls back in browser preview", () => {
  const result = bootstrapTelegramWebApp({});
  assert.equal(result.source, "browser-preview");
  assert.equal(result.ready, false);
});

test("getTelegramWebApp resolves nested runtime", () => {
  const tg = {};
  assert.equal(getTelegramWebApp({ window: { Telegram: { WebApp: tg } } }), tg);
});

test("bindNativeButton returns cleanup", () => {
  let count = 0;
  let removed = false;
  let saved;
  const button = {
    onClick(cb) {
      saved = cb;
    },
    offClick(cb) {
      removed = cb === saved;
    }
  };
  const cleanup = bindNativeButton(button, () => {
    count += 1;
  });
  saved();
  cleanup();
  assert.equal(count, 1);
  assert.equal(removed, true);
});

test("theme params become Telegram css variables", () => {
  const vars = themeParamsToCssVars({ bg_color: "#000000" });
  assert.equal(vars["--tg-theme-bg-color"], "#000000");
});

test("required init-data keys are enforced", () => {
  assert.equal(hasRequiredInitData("auth_date=1&hash=abc"), true);
  assert.equal(hasRequiredInitData("query_id=1"), false);
});
