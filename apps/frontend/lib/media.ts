const FALLBACK_COVER_URL = "https://placehold.co/640x360?text=BiliFocus";

export function getCoverImageUrl(src: string | null) {
  if (!src) {
    return FALLBACK_COVER_URL;
  }

  return `/api/cover?src=${encodeURIComponent(src)}`;
}
