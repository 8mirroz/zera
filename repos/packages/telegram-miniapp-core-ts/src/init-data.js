export function parseInitData(raw = "") {
  const params = new URLSearchParams(raw);
  return {
    query_id: params.get("query_id"),
    user: params.get("user"),
    auth_date: params.get("auth_date"),
    hash: params.get("hash")
  };
}

export function hasRequiredInitData(raw = "") {
  const parsed = parseInitData(raw);
  return Boolean(parsed.auth_date && parsed.hash);
}
