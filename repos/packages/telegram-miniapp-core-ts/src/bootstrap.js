export function getTelegramWebApp(runtime = globalThis) {
  return runtime?.window?.Telegram?.WebApp ?? runtime?.Telegram?.WebApp ?? null;
}

export function bootstrapTelegramWebApp(runtime = globalThis) {
  const tg = getTelegramWebApp(runtime);
  if (!tg) {
    return {
      source: "browser-preview",
      expanded: false,
      ready: false
    };
  }

  tg.ready?.();
  tg.expand?.();

  return {
    source: "telegram",
    expanded: true,
    ready: true
  };
}

export function bindNativeButton(button, onClick) {
  if (!button || typeof onClick !== "function") {
    return () => {};
  }
  button.onClick?.(onClick);
  return () => button.offClick?.(onClick);
}
