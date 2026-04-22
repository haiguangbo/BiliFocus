"use client";

import Link from "next/link";
import { useState } from "react";

import { cacheVideoToLocal, deleteVideoByBvid, syncVideoByBvid, syncVideoSeriesByBvid } from "@/lib/api";
import { getCoverImageUrl } from "@/lib/media";
import { VideoItem } from "@/types/api";

type VideoCardProps = {
  video: VideoItem;
  showDetailLink?: boolean;
  actionMode?: "search" | "library";
  onDeleted?: (bvid: string) => void;
};

export function VideoCard({ video, showDetailLink = false, actionMode, onDeleted }: VideoCardProps) {
  const providerLabel = video.tags.includes("real") ? "Bilibili Web" : "External";
  const [localCached, setLocalCached] = useState(video.cached);
  const [busy, setBusy] = useState(false);
  const [actionMessage, setActionMessage] = useState("");
  const playbackProgress = Math.max(0, Math.min(video.playback_progress_percent ?? 0, 100));
  const showProgress = actionMode === "library" && (playbackProgress > 0 || video.playback_completed);
  const isLibraryCard = actionMode === "library";

  async function handleSync() {
    setBusy(true);
    setActionMessage("");
    try {
      const response = await syncVideoByBvid(video.bvid);
      setLocalCached(true);
      setActionMessage(`已同步：新增 ${response.saved_count}，跳过 ${response.skipped_count}`);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "同步失败");
    } finally {
      setBusy(false);
    }
  }

  async function handleCacheToLocal() {
    setBusy(true);
    setActionMessage("");
    try {
      const response = await cacheVideoToLocal(video.bvid);
      setActionMessage(`已缓存到本地：${response.output_path}`);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "本地缓存失败");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    setBusy(true);
    setActionMessage("");
    try {
      await deleteVideoByBvid(video.bvid);
      onDeleted?.(video.bvid);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "删除失败");
    } finally {
      setBusy(false);
    }
  }

  async function handleSyncSeries() {
    setBusy(true);
    setActionMessage("");
    try {
      const response = await syncVideoSeriesByBvid(video.bvid, 20);
      setActionMessage(`已同步系列：新增 ${response.saved_count}，跳过 ${response.skipped_count}`);
    } catch (error) {
      setActionMessage(error instanceof Error ? error.message : "系列同步失败");
    } finally {
      setBusy(false);
    }
  }

  if (isLibraryCard) {
    return (
      <article className="group overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-[0_12px_38px_rgba(15,23,42,0.06)] transition hover:-translate-y-1 hover:shadow-[0_20px_50px_rgba(15,23,42,0.12)]" data-testid="video-card">
        <div className="relative aspect-[16/10] overflow-hidden bg-slate-100">
          <img alt={video.title} className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.03]" src={getCoverImageUrl(video.cover_url)} />
          <div className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-[linear-gradient(180deg,transparent,rgba(15,23,42,0.75))] px-3 pb-3 pt-8 text-[11px] text-white">
            <span>{video.duration_seconds ? `${Math.floor(video.duration_seconds / 60)} 分钟` : "时长未知"}</span>
            <span>{video.view_count ?? 0} 播放</span>
          </div>
        </div>
        <div className="grid gap-3 p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="line-clamp-2 text-sm font-semibold leading-6 text-slate-900">{video.title}</h3>
              <p className="mt-1 text-xs text-slate-500">{video.author_name}</p>
            </div>
            <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] text-slate-600">{providerLabel}</span>
          </div>
          {showProgress ? (
            <div className="rounded-[18px] border border-blue-100 bg-blue-50 p-3">
              <div className="flex items-center justify-between gap-3 text-xs text-slate-600">
                <span>{video.playback_completed ? "已看完" : "播放进度"}</span>
                <span>{playbackProgress.toFixed(2)}%</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-white">
                <div className="h-full rounded-full bg-blue-500" style={{ width: `${playbackProgress}%` }} />
              </div>
              <p className="mt-2 text-[11px] text-slate-500">
                最近播放：{video.playback_last_played_at ? new Date(video.playback_last_played_at).toLocaleString() : "暂无记录"}
              </p>
            </div>
          ) : null}
          <div className="flex flex-wrap gap-2">
            {video.primary_category ? (
              <span className="rounded-full bg-blue-50 px-2.5 py-1 text-[11px] text-blue-700">
                {video.primary_category}
              </span>
            ) : null}
            {video.series_title ? (
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] text-slate-700">
                {video.series_title}
              </span>
            ) : null}
            {video.tags.slice(0, 4).map((tag) => (
              <span key={`${video.bvid}-${tag}`} className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] text-slate-600">
                {tag}
              </span>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {showDetailLink ? (
              <Link className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 hover:border-slate-400" href={`/videos/${video.bvid}`}>
                查看详情
              </Link>
            ) : null}
            {showProgress ? (
              <Link className="rounded-[18px] bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-500" href={`/videos/${video.bvid}?resume=1`}>
                继续播放
              </Link>
            ) : null}
            <button
              className="rounded-[18px] bg-blue-600 px-3 py-2 text-sm text-white disabled:bg-slate-300 disabled:text-slate-500"
              disabled={busy}
              onClick={handleCacheToLocal}
              type="button"
            >
              {busy ? "处理中..." : "缓存文件"}
            </button>
            <button
              className="rounded-[18px] border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={busy}
              onClick={handleSyncSeries}
              type="button"
            >
              同步系列
            </button>
            <button
              className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 hover:border-rose-400 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={busy}
              onClick={handleDelete}
              type="button"
            >
              删除
            </button>
          </div>
          {actionMessage ? <p className="text-xs text-slate-500">{actionMessage}</p> : null}
        </div>
      </article>
    );
  }

  return (
    <article className="grid gap-4 rounded-[24px] border border-slate-200 bg-white p-4 shadow-[0_16px_40px_rgba(15,23,42,0.04)] md:grid-cols-[220px_1fr]" data-testid="video-card">
      <div className="overflow-hidden rounded-[20px] border border-slate-200 bg-slate-50">
        <img alt={video.title} className="h-full w-full object-cover" src={getCoverImageUrl(video.cover_url)} />
      </div>
      <div className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold tracking-tight text-slate-950">{video.title}</h3>
            <p className="mt-1 text-sm text-slate-500">{video.author_name}</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-700">
              {localCached ? "已同步" : "实时结果"}
            </span>
            <span className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs text-blue-700">
              {providerLabel}
            </span>
          </div>
        </div>
        <p className="text-sm leading-6 text-slate-700">{video.summary ?? "暂无摘要"}</p>
        <div className="flex flex-wrap gap-2 text-xs text-slate-500">
          <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1">
            发布时间 {video.published_at ? new Date(video.published_at).toLocaleDateString() : "未知"}
          </span>
          <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1">播放 {video.view_count ?? 0}</span>
          <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1">点赞 {video.like_count ?? 0}</span>
        </div>
        <div className="rounded-[20px] border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">推荐理由</p>
          <ul className="space-y-1">
            {video.match_reasons.length > 0 ? (
              video.match_reasons.map((reason) => <li key={`${video.bvid}-${reason.code}`}>{reason.message}</li>)
            ) : (
              <li>暂无推荐理由</li>
            )}
          </ul>
        </div>
        <div className="flex flex-wrap gap-2">
          {video.tags.slice(0, 5).map((tag) => (
            <span key={`${video.bvid}-${tag}`} className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-700">
              {tag}
            </span>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2 pt-1">
          {showDetailLink ? (
            <Link
              className="inline-flex rounded-[18px] border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 hover:border-slate-300"
              data-testid="video-detail-link"
              href={`/videos/${video.bvid}`}
            >
              {localCached ? "查看本地详情" : "查看实时详情"}
            </Link>
          ) : null}
          {actionMode === "search" && !localCached ? (
            <button
              className="rounded-[18px] bg-blue-600 px-3 py-2 text-sm text-white disabled:bg-slate-300 disabled:text-slate-500"
              disabled={busy}
              onClick={handleSync}
              type="button"
            >
              {busy ? "同步中..." : "同步到本地"}
            </button>
          ) : null}
          {actionMessage ? <span className="text-xs text-slate-500">{actionMessage}</span> : null}
        </div>
      </div>
    </article>
  );
}
