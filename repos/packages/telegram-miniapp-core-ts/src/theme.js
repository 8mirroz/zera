const THEME_KEYS = [
  "bg_color",
  "text_color",
  "button_color",
  "button_text_color",
  "secondary_bg_color",
  "hint_color",
  "destructive_text_color"
];

export function themeParamsToCssVars(themeParams = {}) {
  const vars = {};
  for (const key of THEME_KEYS) {
    if (themeParams[key]) {
      vars[`--tg-theme-${key.replaceAll("_", "-")}`] = themeParams[key];
    }
  }
  return vars;
}
