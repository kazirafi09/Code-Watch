export function slugify(s) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
export function clamp(n, lo, hi) { return Math.min(Math.max(n, lo), hi); }
