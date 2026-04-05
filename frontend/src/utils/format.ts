export function humanizeToken(value: string | null | undefined): string {
  if (!value) return "";
  return value
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (m) => m.toUpperCase());
}

/**
 * Topic labels coming from clustering sometimes include numeric tokens like:
 * "12 Solar Panels Energy ..." or "3 Iran Missile ...".
 * We remove standalone number tokens while keeping meaningful numbers like "3D" or "GPT-4".
 */
export function humanizeTopicLabel(value: string | null | undefined): string {
  if (!value) return "";
  const normalized = value.replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
  const tokens = normalized.split(" ").filter((t) => t && !/^\d+$/.test(t));
  const cleaned = tokens.join(" ").replace(/^\d+\s+/, "").trim();
  return cleaned.replace(/\b\w/g, (m) => m.toUpperCase());
}

/**
 * LLM synthesis stores machine citations like `[raw_post_id=123 url=https://…]` for validation.
 * End users should not see those — sources already appear as chips / links on the card.
 */
export function displayInsightText(raw: string | null | undefined): string {
  if (!raw) return "";
  let s = raw;
  s = s.replace(/\[raw_post_id=\d+\s+url=[^\]]*\]/gi, "");
  s = s.replace(/\[raw_post_id=\d+\]/gi, "");
  return s.replace(/\s{2,}/g, " ").trim();
}

/** Legacy / internal placeholders we should not show as “What it is” copy. */
export function isUnhelpfulInsightText(raw: string | null | undefined): boolean {
  if (!raw?.trim()) return true;
  const t = raw.toLowerCase();
  if (t.includes("not enough source text was collected")) return true;
  if (t.includes("try running an update after more posts")) return true;
  if (t.includes("impact cannot be assessed until there is more evidence")) return true;
  return false;
}

export type HeatLabel = "Just starting" | "Warming up" | "Strong" | "Very hot";
export function heatLabel(score: number | null | undefined): HeatLabel | null {
  if (score == null || Number.isNaN(score)) return null;
  if (score < 0.25) return "Just starting";
  if (score < 0.5) return "Warming up";
  if (score < 0.75) return "Strong";
  return "Very hot";
}

export type PlacesLabel = "One place" | "A few places" | "Many places" | "Everywhere";
export function placesLabel(strength: number | null | undefined): PlacesLabel | null {
  if (strength == null || Number.isNaN(strength)) return null;
  if (strength < 0.2) return "One place";
  if (strength < 0.4) return "A few places";
  if (strength < 0.6) return "Many places";
  return "Everywhere";
}

export type ChatterLabel = "A little chatter" | "Some chatter" | "Lots of chatter";
export function chatterLabel(count: number | null | undefined): ChatterLabel | null {
  if (count == null || Number.isNaN(count)) return null;
  if (count < 10) return "A little chatter";
  if (count < 30) return "Some chatter";
  return "Lots of chatter";
}

