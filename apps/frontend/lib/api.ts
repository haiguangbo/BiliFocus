import {
  BilibiliQRCodeCreateResponse,
  BilibiliQRCodePollResponse,
  CurationJobCreateResponse,
  CurationJobStatusResponse,
  CurationRunResponse,
  PreferenceConfig,
  PreferenceUpdateResponse,
  SearchResponse,
  SearchSyncResponse,
  VideoCacheResponse,
  VideoDeleteResponse,
  VideoDetail,
  VideoListResponse,
  VideoPlaybackProgressResponse,
  VideoMetadataRewriteResponse,
  VideoPlaybackResponse,
} from "@/types/api";

const browserBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/backend-api";
const serverBaseUrl = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

function getBaseUrl() {
  return typeof window === "undefined" ? serverBaseUrl : browserBaseUrl;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const payload = await response.json();
      const apiMessage = payload?.error?.message;
      if (typeof apiMessage === "string" && apiMessage.trim()) {
        message = apiMessage;
      }
    } catch {
      // Ignore body parsing errors and keep the status-based message.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function searchVideos(payload: {
  query: string;
  filter_text?: string;
  limit?: number;
  offset?: number;
  source?: string;
}) {
  return request<SearchResponse>("/api/search", {
    method: "POST",
    body: JSON.stringify({
      query: payload.query,
      filter_text: payload.filter_text ?? "",
      limit: payload.limit ?? 20,
      offset: payload.offset ?? 0,
      source: payload.source ?? "default",
    }),
  });
}

export async function listVideos() {
  return listVideosWithParams({});
}

export async function listVideosWithParams(params: {
  q?: string;
  tag?: string;
  sort?: "recent" | "views" | "published_at";
  limit?: number;
  offset?: number;
}) {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.tag) search.set("tag", params.tag);
  if (params.sort) search.set("sort", params.sort);
  if (typeof params.limit === "number") search.set("limit", String(params.limit));
  if (typeof params.offset === "number") search.set("offset", String(params.offset));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<VideoListResponse>(`/api/videos${suffix}`);
}

export async function getPreferences() {
  return request<PreferenceConfig>("/api/preferences");
}

export async function createBilibiliQRCode() {
  return request<BilibiliQRCodeCreateResponse>("/api/auth/bilibili/qrcode");
}

export async function pollBilibiliQRCode(qrcodeKey: string) {
  return request<BilibiliQRCodePollResponse>(`/api/auth/bilibili/qrcode/poll?qrcode_key=${encodeURIComponent(qrcodeKey)}`);
}

export async function getVideoDetail(bvid: string) {
  return request<VideoDetail>(`/api/videos/${bvid}`);
}

export async function getVideoPlayback(bvid: string, quality?: string, cid?: string) {
  const search = new URLSearchParams();
  if (quality) search.set("quality", quality);
  if (cid) search.set("cid", cid);
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<VideoPlaybackResponse>(`/api/videos/${bvid}/playback${suffix}`);
}

export async function saveVideoPlaybackProgress(payload: {
  bvid: string;
  position_seconds: number;
  duration_seconds?: number | null;
  completed?: boolean;
}) {
  return request<VideoPlaybackProgressResponse>(`/api/videos/${payload.bvid}/playback-progress`, {
    method: "POST",
    body: JSON.stringify({
      position_seconds: payload.position_seconds,
      duration_seconds: payload.duration_seconds ?? null,
      completed: payload.completed ?? false,
    }),
  });
}

export async function syncVideoByBvid(bvid: string) {
  return request<SearchSyncResponse>(`/api/videos/${bvid}/sync`, {
    method: "POST",
  });
}

export async function syncVideoSeriesByBvid(bvid: string, limit = 20) {
  return request<SearchSyncResponse>(`/api/videos/${bvid}/sync-series?limit=${encodeURIComponent(String(limit))}`, {
    method: "POST",
  });
}

export async function deleteVideoByBvid(bvid: string) {
  return request<VideoDeleteResponse>(`/api/videos/${bvid}`, {
    method: "DELETE",
  });
}

export async function cacheVideoToLocal(bvid: string, quality?: string) {
  const suffix = quality ? `?quality=${encodeURIComponent(quality)}` : "";
  return request<VideoCacheResponse>(`/api/videos/${bvid}/cache${suffix}`, {
    method: "POST",
  });
}

export async function rewriteLibraryMetadata(payload: { limit?: number; tag?: string }) {
  return request<VideoMetadataRewriteResponse>("/api/videos/rewrite-metadata", {
    method: "POST",
    body: JSON.stringify({
      limit: payload.limit ?? 20,
      tag: payload.tag ?? null,
    }),
  });
}

export async function syncSearchResults(payload: {
  query: string;
  filter_text?: string;
  limit?: number;
  source?: string;
}) {
  return request<SearchSyncResponse>("/api/sync/search", {
    method: "POST",
    body: JSON.stringify({
      query: payload.query,
      filter_text: payload.filter_text ?? "",
      limit: payload.limit ?? 20,
      source: payload.source ?? "default",
    }),
  });
}

export async function savePreferences(payload: PreferenceConfig) {
  return request<PreferenceUpdateResponse>("/api/preferences", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function runCuration(payload: {
  objective: string;
  extra_requirements?: string;
  max_keywords?: number;
  limit_per_keyword?: number;
  sync_accepted?: boolean;
}) {
  return request<CurationRunResponse>("/api/curation/run", {
    method: "POST",
    body: JSON.stringify({
      objective: payload.objective,
      extra_requirements: payload.extra_requirements ?? "",
      max_keywords: payload.max_keywords ?? 5,
      limit_per_keyword: payload.limit_per_keyword ?? 8,
      sync_accepted: payload.sync_accepted ?? true,
    }),
  });
}

export async function createCurationJob(payload: {
  objective: string;
  extra_requirements?: string;
  max_keywords?: number;
  limit_per_keyword?: number;
  sync_accepted?: boolean;
}) {
  return request<CurationJobCreateResponse>("/api/curation/jobs", {
    method: "POST",
    body: JSON.stringify({
      objective: payload.objective,
      extra_requirements: payload.extra_requirements ?? "",
      max_keywords: payload.max_keywords ?? 5,
      limit_per_keyword: payload.limit_per_keyword ?? 8,
      sync_accepted: payload.sync_accepted ?? true,
    }),
  });
}

export async function getCurationJobStatus(jobId: string) {
  return request<CurationJobStatusResponse>(`/api/curation/jobs/${encodeURIComponent(jobId)}`);
}
