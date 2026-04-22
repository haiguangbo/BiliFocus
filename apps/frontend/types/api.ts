export type RecommendationReason = {
  code: string;
  message: string;
};

export type VideoItem = {
  bvid: string;
  title: string;
  author_name: string;
  cover_url: string | null;
  duration_seconds: number | null;
  published_at: string | null;
  view_count: number | null;
  like_count: number | null;
  summary: string | null;
  tags: string[];
  primary_category?: string | null;
  secondary_category?: string | null;
  series_key?: string | null;
  series_title?: string | null;
  playback_position_seconds?: number | null;
  playback_progress_percent?: number | null;
  playback_last_played_at?: string | null;
  playback_completed?: boolean;
  match_reasons: RecommendationReason[];
  cached: boolean;
};

export type VideoDetail = VideoItem & {
  description: string | null;
  source_url: string | null;
  sync_status: string;
  last_synced_at: string | null;
  raw_extra: Record<string, string>;
};

export type PlaybackQualityOption = {
  code: string;
  label: string;
};

export type VideoPlaybackResponse = {
  bvid: string;
  cid: string;
  selected_quality_code: string;
  selected_quality_label: string;
  stream_url: string;
  qualities: PlaybackQualityOption[];
};

export type VideoPlaybackProgressResponse = {
  bvid: string;
  status: string;
  position_seconds: number;
  duration_seconds: number | null;
  progress_percent: number;
  completed: boolean;
  last_played_at: string;
};

export type VideoListResponse = {
  items: VideoItem[];
  total: number;
  limit: number;
  offset: number;
};

export type SearchResponse = {
  query: string;
  filter_text: string | null;
  items: VideoItem[];
  total: number;
  limit: number;
  offset: number;
};

export type SearchSyncResponse = {
  job_id: string;
  status: string;
  query: string;
  saved_count: number;
  skipped_count: number;
  failed_count: number;
  started_at: string;
  finished_at: string;
};

export type VideoCacheResponse = {
  bvid: string;
  status: string;
  output_path: string;
  quality_code: string;
  quality_label: string;
  bytes_written: number;
};

export type VideoMetadataRewriteResponse = {
  job_id: string;
  status: string;
  rewritten_count: number;
  skipped_count: number;
  updated_bvids: string[];
  started_at: string;
  finished_at: string;
};

export type VideoDeleteResponse = {
  bvid: string;
  status: string;
};

export type CurationRunResponse = {
  job_id: string;
  status: string;
  objective: string;
  recommended_keywords: string[];
  pipeline_trace: {
    planner: PipelineStageTrace;
    reviewer: PipelineStageTrace;
    classifier: PipelineStageTrace;
  };
  reviewed_count: number;
  accepted_count: number;
  rejected_count: number;
  saved_count: number;
  skipped_count: number;
  accepted_items: VideoItem[];
  started_at: string;
  finished_at: string;
};

export type CurationJobStage = "planner" | "collector" | "reviewer" | "classifier" | "sync" | "completed";
export type CurationJobStatus = "queued" | "running" | "completed" | "failed";

export type CurationJobCreateResponse = {
  job_id: string;
  status: CurationJobStatus;
  stage: CurationJobStage;
  progress_message: string;
};

export type CurationJobStatusResponse = {
  job_id: string;
  status: CurationJobStatus;
  stage: CurationJobStage;
  progress_message: string;
  result?: CurationRunResponse | null;
  error_message?: string | null;
};

export type PreferenceConfig = {
  default_search_limit: number;
  default_source: string;
  default_filter_text: string;
  bilibili_cookie: string;
  download_output_dir: string;
  theme: string;
  language: string;
  library_sort: string;
  hide_watched_placeholder: boolean;
};

export type PreferenceUpdateResponse = PreferenceConfig & {
  updated_at?: string | null;
};

export type PipelineStageTrace = {
  agent: string;
  status: string;
  summary: string;
  outputs: string[];
};

export type BilibiliQRCodeCreateResponse = {
  status: string;
  qrcode_key: string;
  login_url: string;
  expires_in_seconds: number;
};

export type BilibiliQRCodePollResponse = {
  status: string;
  state: string;
  message: string;
  cookie_configured: boolean;
};
