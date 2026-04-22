import { CleanPlayerPlaylistEntry, CleanPlayerPlaylistGroup, CleanPlayerShell } from "@/components/clean-player-shell";
import { getVideoDetail } from "@/lib/api";
import { getCoverImageUrl } from "@/lib/media";

type VideoDetailPageProps = {
  params: {
    bvid: string;
  };
  searchParams?: {
    resume?: string;
  };
};

function buildNativeEpisodePlaylist(rawExtra: Record<string, string>): CleanPlayerPlaylistEntry[] {
  const payload = rawExtra.episode_playlist_json;
  if (!payload) {
    return [];
  }
  try {
    const items = JSON.parse(payload) as Array<Record<string, string>>;
    return items
      .filter((entry) => Boolean(entry?.bvid))
      .map((entry, index) => ({
        bvid: entry.bvid,
        cid: entry.cid || undefined,
        indexLabel: entry.label || entry.index || `EP ${index + 1}`,
        title: entry.title || entry.label || `第${index + 1}集`,
        resumePositionSeconds: 0,
        progressPercent: 0,
        lastPlayedAt: "",
      }));
  } catch {
    return [];
  }
}

function buildNativeEpisodeTree(rawExtra: Record<string, string>): CleanPlayerPlaylistGroup[] {
  const payload = rawExtra.episode_tree_json;
  if (!payload) {
    return [];
  }
  try {
    const groups = JSON.parse(payload) as Array<{ title?: string; children?: Array<Record<string, string>> }>;
    return groups
      .filter((group) => Array.isArray(group?.children) && group.children.length > 0)
      .map((group) => ({
        title: group.title || "默认分组",
        children: (group.children ?? [])
          .filter((entry) => Boolean(entry?.bvid))
          .map((entry, index) => ({
            bvid: entry.bvid,
            cid: entry.cid || undefined,
            indexLabel: entry.label || entry.index || `EP ${index + 1}`,
            title: entry.title || entry.label || `第${index + 1}集`,
            resumePositionSeconds: 0,
            progressPercent: 0,
            lastPlayedAt: "",
          })),
      }));
  } catch {
    return [];
  }
}

function formatDuration(seconds: number | null): string {
  if (!seconds || seconds <= 0) {
    return "未知";
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return `${hours} 小时 ${minutes} 分`;
  }
  return `${minutes} 分钟`;
}

export default async function VideoDetailPage({ params, searchParams }: VideoDetailPageProps) {
  try {
    const video = await getVideoDetail(params.bvid);
    const cid = video.raw_extra.cid;
    const bestQuality = video.raw_extra.stream_best_quality_label;
    const acceptQualityCodes = video.raw_extra.stream_accept_quality_codes;
    const allQualities = video.raw_extra.stream_accept_quality_labels;
    const authConfigured = video.raw_extra.auth_cookie_configured === "true";
    const isPreview = video.sync_status === "preview";
    const nativeTree = buildNativeEpisodeTree(video.raw_extra);
    const nativePlaylist = buildNativeEpisodePlaylist(video.raw_extra);
    const playlist: CleanPlayerPlaylistGroup[] =
      nativeTree.length > 0
        ? nativeTree
        : nativePlaylist.length > 0
          ? [{ title: "原生选集", children: nativePlaylist }]
          : [];
    const autoResume = searchParams?.resume === "1";
    const episodeCount = nativeTree.length > 0 ? nativeTree.reduce((acc, group) => acc + group.children.length, 0) : nativePlaylist.length;
    const statusLabel = isPreview ? "实时预览" : "已同步";
    const compactTags = video.tags.slice(0, 8);
    return (
      <main className="grid gap-6" data-testid="video-detail-page">
        <section className="grid gap-4">
          <div className="grid gap-4">
            <CleanPlayerShell
              allQualities={allQualities}
              acceptQualityCodes={acceptQualityCodes}
              authConfigured={authConfigured}
              bestQuality={bestQuality}
              bvid={video.bvid}
              cid={cid}
              autoResume={autoResume}
              isPreview={isPreview}
              playlist={playlist}
              rawExtra={video.raw_extra}
              reasons={video.match_reasons}
              sourceUrl={video.source_url}
              summary={video.description ?? video.summary}
              title={video.title}
            />
            <section className="overflow-hidden rounded-[24px] border border-slate-200 bg-white p-4 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
              <div className="grid gap-4 md:grid-cols-[180px_1fr]">
                <img
                  alt={video.title}
                  className="aspect-video w-full rounded-[18px] object-cover"
                  src={getCoverImageUrl(video.cover_url)}
                />
                <div className="grid gap-4">
                  <div className="flex flex-wrap gap-2">
                    <span className={`rounded-full border px-3 py-1 text-xs font-medium ${isPreview ? "border-amber-200 bg-amber-50 text-amber-700" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>
                      {statusLabel}
                    </span>
                    {video.primary_category ? (
                      <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-700">{video.primary_category}</span>
                    ) : null}
                    {video.secondary_category ? (
                      <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-700">{video.secondary_category}</span>
                    ) : null}
                    {episodeCount > 0 ? (
                      <span className="rounded-full border border-blue-100 bg-blue-50 px-3 py-1 text-xs text-blue-700">选集 {episodeCount} 项</span>
                    ) : null}
                    {bestQuality ? (
                      <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-700">{bestQuality}</span>
                    ) : null}
                  </div>

                  <div className="grid gap-3 md:grid-cols-4">
                    <div className="rounded-[18px] border border-slate-200 bg-slate-50 p-3">
                      <p className="text-[11px] uppercase tracking-[0.2em] text-slate-500">发布时间</p>
                      <p className="mt-2 text-sm font-medium text-slate-900">{video.published_at ? new Date(video.published_at).toLocaleDateString() : "未知"}</p>
                    </div>
                    <div className="rounded-[18px] border border-slate-200 bg-slate-50 p-3">
                      <p className="text-[11px] uppercase tracking-[0.2em] text-slate-500">时长</p>
                      <p className="mt-2 text-sm font-medium text-slate-900">{formatDuration(video.duration_seconds)}</p>
                    </div>
                    <div className="rounded-[18px] border border-slate-200 bg-slate-50 p-3">
                      <p className="text-[11px] uppercase tracking-[0.2em] text-slate-500">播放</p>
                      <p className="mt-2 text-sm font-medium text-slate-900">{video.view_count ?? 0}</p>
                    </div>
                    <div className="rounded-[18px] border border-slate-200 bg-slate-50 p-3">
                      <p className="text-[11px] uppercase tracking-[0.2em] text-slate-500">点赞</p>
                      <p className="mt-2 text-sm font-medium text-slate-900">{video.like_count ?? 0}</p>
                    </div>
                  </div>

                  <div className="grid gap-2 text-sm text-slate-600">
                    <p className="leading-7 text-slate-700">{video.description ?? video.summary ?? "暂无描述"}</p>
                    {video.series_title ? <p>所属系列：<span className="text-slate-900">{video.series_title}</span></p> : null}
                    <p>最近更新：<span className="text-slate-900">{video.last_synced_at ? new Date(video.last_synced_at).toLocaleString() : "未知"}</span></p>
                    <p>登录态：<span className="text-slate-900">{authConfigured ? "已配置 Cookie" : "未配置 Cookie"}</span></p>
                    {video.source_url ? (
                      <p>
                        原始链接：
                        <a className="ml-1 text-blue-700 hover:text-blue-600" href={video.source_url} rel="noreferrer" target="_blank">
                          查看原视频
                        </a>
                      </p>
                    ) : null}
                  </div>

                  {compactTags.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {compactTags.map((tag) => (
                        <span key={tag} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-700">
                          {tag}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            </section>
          </div>
        </section>
      </main>
    );
  } catch {
    return (
      <main className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
        视频详情加载失败，可能该视频尚未同步到本地库。
      </main>
    );
  }
}
