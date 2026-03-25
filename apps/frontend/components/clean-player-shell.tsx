"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { getVideoPlayback, saveVideoPlaybackProgress } from "@/lib/api";
import { RecommendationReason } from "@/types/api";

export type CleanPlayerPlaylistEntry = {
  bvid: string;
  cid?: string;
  indexLabel: string;
  title: string;
  resumePositionSeconds: number;
  progressPercent: number;
  lastPlayedAt: string;
};

export type CleanPlayerPlaylistGroup = {
  title: string;
  children: CleanPlayerPlaylistEntry[];
};

type CleanPlayerShellProps = {
  title: string;
  bvid: string;
  cid: string | undefined;
  autoResume: boolean;
  sourceUrl: string | null;
  bestQuality: string | undefined;
  acceptQualityCodes: string | undefined;
  allQualities: string | undefined;
  authConfigured: boolean;
  isPreview: boolean;
  summary: string | null;
  reasons: RecommendationReason[];
  rawExtra: Record<string, string>;
  playlist: CleanPlayerPlaylistGroup[];
};

type PanelKey = "summary" | "review" | "stream" | "history";

export function CleanPlayerShell({
  title,
  bvid,
  cid,
  autoResume,
  sourceUrl,
  bestQuality,
  acceptQualityCodes,
  allQualities,
  authConfigured,
  isPreview,
  summary,
  reasons,
  rawExtra,
  playlist,
}: CleanPlayerShellProps) {
  const [theatreMode, setTheatreMode] = useState(true);
  const [activePanel, setActivePanel] = useState<PanelKey>("summary");
  const [selectedVideo, setSelectedVideo] = useState<CleanPlayerPlaylistEntry>({
    bvid,
    cid,
    indexLabel: "当前",
    title,
    resumePositionSeconds: Number(rawExtra.playback_position_seconds || "0"),
    progressPercent: Number(rawExtra.playback_progress_percent || "0"),
    lastPlayedAt: rawExtra.playback_last_played_at || "",
  });
  const [selectedQualityCode, setSelectedQualityCode] = useState("");
  const [appliedQualityCode, setAppliedQualityCode] = useState("");
  const [playbackStreamUrl, setPlaybackStreamUrl] = useState<string | null>(null);
  const [resolvedQualityLabel, setResolvedQualityLabel] = useState(bestQuality ?? "");
  const [resolvedQualityOptions, setResolvedQualityOptions] = useState<{ code: string; label: string }[]>(
    ((acceptQualityCodes ?? "")
      .split(",")
      .map((entry, index) => ({
        code: entry.trim(),
        label: (allQualities ?? "").split(",")[index]?.trim() ?? entry.trim(),
      }))
      .filter((entry) => entry.code)),
  );
  const [playerError, setPlayerError] = useState<string | null>(null);
  const [playerLoading, setPlayerLoading] = useState(false);
  const [progressState, setProgressState] = useState({
    positionSeconds: Number(rawExtra.playback_position_seconds || "0"),
    durationSeconds: Number(rawExtra.playback_duration_seconds || "0"),
    progressPercent: Number(rawExtra.playback_progress_percent || "0"),
    sessionCount: Number(rawExtra.playback_session_count || "0"),
    lastPlayedAt: rawExtra.playback_last_played_at || "",
  });
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const lastSavedPositionRef = useRef(0);
  const shouldAutoplayRef = useRef(false);
  const shouldResumeRef = useRef(autoResume);

  const playlistGroups = useMemo(() => {
    const currentEntry: CleanPlayerPlaylistEntry = {
      bvid,
      cid,
      indexLabel: "当前",
      title,
      resumePositionSeconds: Number(rawExtra.playback_position_seconds || "0"),
      progressPercent: Number(rawExtra.playback_progress_percent || "0"),
      lastPlayedAt: rawExtra.playback_last_played_at || "",
    };
    const flattened = playlist.flatMap((group) => group.children);
    const hasCurrent = flattened.some((entry) => entry.bvid === currentEntry.bvid && (entry.cid ?? "") === (currentEntry.cid ?? ""));
    const groups = [...playlist];
    if (!hasCurrent) {
      groups.unshift({ title: "当前视频", children: [currentEntry] });
    }
    return groups;
  }, [bvid, cid, playlist, rawExtra.playback_last_played_at, rawExtra.playback_position_seconds, rawExtra.playback_progress_percent, title]);

  useEffect(() => {
    setSelectedVideo({
      bvid,
      cid,
      indexLabel: "当前",
      title,
      resumePositionSeconds: Number(rawExtra.playback_position_seconds || "0"),
      progressPercent: Number(rawExtra.playback_progress_percent || "0"),
      lastPlayedAt: rawExtra.playback_last_played_at || "",
    });
    shouldResumeRef.current = autoResume;
  }, [autoResume, bvid, cid, rawExtra.playback_last_played_at, rawExtra.playback_position_seconds, rawExtra.playback_progress_percent, title]);

  useEffect(() => {
    setSelectedQualityCode("");
    setAppliedQualityCode("");
    setPlaybackStreamUrl(null);
    setPlayerError(null);
    setProgressState({
      positionSeconds: selectedVideo.bvid === bvid && (selectedVideo.cid ?? cid ?? "") === (cid ?? "") ? Number(rawExtra.playback_position_seconds || "0") : selectedVideo.resumePositionSeconds,
      durationSeconds: selectedVideo.bvid === bvid && (selectedVideo.cid ?? cid ?? "") === (cid ?? "") ? Number(rawExtra.playback_duration_seconds || "0") : 0,
      progressPercent: selectedVideo.bvid === bvid && (selectedVideo.cid ?? cid ?? "") === (cid ?? "") ? Number(rawExtra.playback_progress_percent || "0") : selectedVideo.progressPercent,
      sessionCount: selectedVideo.bvid === bvid && (selectedVideo.cid ?? cid ?? "") === (cid ?? "") ? Number(rawExtra.playback_session_count || "0") : 0,
      lastPlayedAt: selectedVideo.bvid === bvid && (selectedVideo.cid ?? cid ?? "") === (cid ?? "") ? rawExtra.playback_last_played_at || "" : selectedVideo.lastPlayedAt,
    });
  }, [
    bvid,
    cid,
    rawExtra.playback_duration_seconds,
    rawExtra.playback_last_played_at,
    rawExtra.playback_position_seconds,
    rawExtra.playback_progress_percent,
    rawExtra.playback_session_count,
    selectedVideo.bvid,
    selectedVideo.cid,
    selectedVideo.lastPlayedAt,
    selectedVideo.progressPercent,
    selectedVideo.resumePositionSeconds,
  ]);

  useEffect(() => {
    let cancelled = false;

    async function loadPlayback() {
      setPlayerLoading(true);
      setPlayerError(null);
      try {
        const playback = await getVideoPlayback(
          selectedVideo.bvid,
          selectedQualityCode || undefined,
          selectedVideo.cid || undefined,
        );
        if (cancelled) {
          return;
        }
        setPlaybackStreamUrl(playback.stream_url);
        setResolvedQualityLabel(playback.selected_quality_label);
        setResolvedQualityOptions(playback.qualities);
        setAppliedQualityCode(playback.selected_quality_code);
      } catch (error) {
        if (cancelled) {
          return;
        }
        setPlaybackStreamUrl(null);
        setPlayerError(error instanceof Error ? error.message : "播放信息加载失败");
      } finally {
        if (!cancelled) {
          setPlayerLoading(false);
        }
      }
    }

    void loadPlayback();
    return () => {
      cancelled = true;
    };
  }, [selectedQualityCode, selectedVideo.bvid, selectedVideo.cid]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      const element = videoRef.current;
      if (!element || element.paused || Number.isNaN(element.currentTime)) {
        return;
      }
      const delta = Math.abs(element.currentTime - lastSavedPositionRef.current);
      if (delta < 10) {
        return;
      }
      void persistProgress(false);
    }, 15000);
    return () => window.clearInterval(timer);
  }, [selectedVideo.bvid, selectedVideo.cid]);

  async function persistProgress(completed: boolean) {
    const element = videoRef.current;
    if (!element) {
      return;
    }
    const payload = {
      bvid: selectedVideo.bvid,
      position_seconds: completed ? element.duration || element.currentTime : element.currentTime,
      duration_seconds: Number.isFinite(element.duration) ? element.duration : undefined,
      completed,
    };
    lastSavedPositionRef.current = payload.position_seconds;
    try {
      const response = await saveVideoPlaybackProgress(payload);
      setProgressState((current) => ({
        positionSeconds: response.position_seconds,
        durationSeconds: response.duration_seconds ?? 0,
        progressPercent: response.progress_percent,
        sessionCount: completed ? current.sessionCount + 1 : current.sessionCount,
        lastPlayedAt: response.last_played_at,
      }));
    } catch {
      // Keep playback uninterrupted if local progress persistence fails.
    }
  }

  const playerHeightClass = useMemo(
    () => (theatreMode ? "aspect-[16/9] min-h-[72vh]" : "aspect-video min-h-[52vh]"),
    [theatreMode],
  );

  const panelButtonClass = (panel: PanelKey) =>
    `rounded-full border px-3 py-1.5 text-xs uppercase tracking-[0.24em] transition ${
      activePanel === panel
        ? "border-blue-200 bg-blue-50 text-blue-700"
        : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
    }`;

  return (
    <section
      className={`overflow-hidden rounded-[28px] border ${
        theatreMode
          ? "border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.04)]"
          : "border-slate-200 bg-white shadow-[0_16px_40px_rgba(15,23,42,0.04)]"
      } p-3`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-[20px] border border-slate-200 bg-slate-50 px-4 py-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-600/75">Clean Player</p>
          <p className="mt-1 text-sm text-slate-700">优先按 B 站原生选集顺序播放，支持清晰度切换和本地进度记录。</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            className="rounded-full border border-slate-200 bg-white px-3 py-2 text-xs uppercase tracking-[0.2em] text-slate-700 hover:border-slate-300"
            onClick={() => setTheatreMode((value) => !value)}
            type="button"
          >
            {theatreMode ? "退出影院模式" : "影院模式"}
          </button>
          <button
            className="rounded-full border border-slate-200 bg-white px-3 py-2 text-xs uppercase tracking-[0.2em] text-slate-700 hover:border-slate-300"
            onClick={() => {
              videoRef.current?.load();
            }}
            type="button"
          >
            重载播放器
          </button>
          <a
            className="rounded-full bg-blue-600 px-3 py-2 text-xs uppercase tracking-[0.2em] text-white hover:bg-blue-500"
            href={selectedVideo.bvid === bvid ? (sourceUrl ?? "#") : `https://www.bilibili.com/video/${selectedVideo.bvid}`}
            rel="noreferrer"
            target="_blank"
          >
            打开原视频
          </a>
        </div>
      </div>

      <div className={`mt-3 grid gap-4 ${theatreMode ? "xl:grid-cols-[minmax(0,4fr)_minmax(280px,1fr)]" : "lg:grid-cols-[minmax(0,3fr)_300px]"}`}>
        <div className="grid gap-4">
          <div className="overflow-hidden rounded-[24px] border border-slate-200 bg-black shadow-[0_16px_40px_rgba(15,23,42,0.08)]">
            {playbackStreamUrl ? (
              <video
                ref={videoRef}
                className={`w-full bg-black ${playerHeightClass}`}
                controls
                onEnded={() => {
                  void persistProgress(true);
                }}
                onLoadedMetadata={() => {
                  const element = videoRef.current;
                  if (!element) {
                    return;
                  }
                  if (shouldResumeRef.current && selectedVideo.resumePositionSeconds > 5 && Number.isFinite(element.duration)) {
                    element.currentTime = Math.min(selectedVideo.resumePositionSeconds, Math.max(element.duration - 1, 0));
                    shouldResumeRef.current = false;
                  }
                  if (shouldAutoplayRef.current) {
                    void element.play().catch(() => undefined);
                    shouldAutoplayRef.current = false;
                  }
                  setProgressState((current) => ({
                    ...current,
                    durationSeconds: Number.isFinite(element.duration) ? element.duration : current.durationSeconds,
                  }));
                }}
                onPause={() => {
                  void persistProgress(false);
                }}
                onTimeUpdate={() => {
                  const element = videoRef.current;
                  if (!element || Number.isNaN(element.currentTime)) {
                    return;
                  }
                  const duration = Number.isFinite(element.duration) ? element.duration : progressState.durationSeconds;
                  const progressPercent = duration > 0 ? Number(((element.currentTime / duration) * 100).toFixed(2)) : 0;
                  setProgressState((current) => ({
                    ...current,
                    positionSeconds: Number(element.currentTime.toFixed(2)),
                    durationSeconds: duration,
                    progressPercent,
                  }));
                }}
                playsInline
                preload="metadata"
                src={playbackStreamUrl}
              />
            ) : playerLoading ? (
              <div className={`flex items-center justify-center bg-slate-950 px-6 text-center text-sm text-slate-400 ${playerHeightClass}`}>
                正在为当前选集准备可播放流...
              </div>
            ) : (
              <div className={`flex items-center justify-center bg-slate-950 px-6 text-center text-sm text-slate-400 ${playerHeightClass}`}>
                {playerError ?? "当前视频没有可用的代理播放流。"}
              </div>
            )}
          </div>

          <div className="rounded-[24px] border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] uppercase tracking-[0.24em] text-slate-700">
                {isPreview ? "Preview" : "Synced"}
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] uppercase tracking-[0.24em] text-slate-700">
                {selectedVideo.indexLabel}
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] uppercase tracking-[0.24em] text-slate-700">
                {resolvedQualityLabel || bestQuality || "未知画质"}
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] uppercase tracking-[0.24em] text-slate-700">
                Cookie {authConfigured ? "已配置" : "未配置"}
              </span>
            </div>
            <h3 className="mt-3 text-xl font-semibold text-slate-900">{selectedVideo.title}</h3>
            {resolvedQualityOptions.length > 0 ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {resolvedQualityOptions.map((option) => (
                  <button
                    key={option.code}
                    className={`rounded-full border px-3 py-1.5 text-xs ${
                      (selectedQualityCode || appliedQualityCode) === option.code
                        ? "border-blue-200 bg-blue-50 text-blue-700"
                        : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                    }`}
                    onClick={() => {
                      if (option.code !== selectedQualityCode) {
                        setSelectedQualityCode(option.code);
                      }
                    }}
                    type="button"
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-sm text-slate-600">
                {allQualities ? `可用清晰度：${allQualities}` : "当前还没有解析到完整清晰度列表。"}
              </p>
            )}
          </div>
        </div>

        <aside className="grid gap-4">
          <div className="rounded-[24px] border border-slate-200 bg-white p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-600/75">视频选集</p>
            <div className="mt-3 grid max-h-[72vh] gap-2 overflow-y-auto pr-1">
              {playlistGroups.map((group, groupIndex) => (
                <div key={`${group.title}-${groupIndex}`} className="grid gap-2">
                  <div className="rounded-xl bg-slate-100 px-3 py-2 text-xs font-medium tracking-[0.18em] text-slate-500">
                    {group.title}
                  </div>
                  {group.children.map((entry, index) => {
                    const active = entry.bvid === selectedVideo.bvid && (entry.cid ?? "") === (selectedVideo.cid ?? "");
                    return (
                      <button
                        key={`${group.title}-${entry.bvid}:${entry.cid ?? index}`}
                        className={`rounded-[18px] border px-3 py-3 text-left ${active ? "border-blue-200 bg-blue-50" : "border-slate-200 bg-white hover:border-slate-300"}`}
                        onClick={() => {
                          shouldAutoplayRef.current = true;
                          shouldResumeRef.current = true;
                          setSelectedVideo(entry);
                        }}
                        type="button"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{entry.indexLabel || `EP ${index + 1}`}</p>
                          {entry.progressPercent > 0 ? <span className="text-[11px] text-slate-500">{entry.progressPercent.toFixed(0)}%</span> : null}
                        </div>
                        <p className="mt-1 line-clamp-2 text-sm font-medium text-slate-900">{entry.title}</p>
                        {entry.progressPercent > 0 ? (
                          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-200">
                            <div className="h-full rounded-full bg-blue-500" style={{ width: `${Math.min(entry.progressPercent, 100)}%` }} />
                          </div>
                        ) : null}
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[24px] border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap gap-2">
              <button className={panelButtonClass("summary")} onClick={() => setActivePanel("summary")} type="button">
                摘要
              </button>
              <button className={panelButtonClass("review")} onClick={() => setActivePanel("review")} type="button">
                审核
              </button>
              <button className={panelButtonClass("stream")} onClick={() => setActivePanel("stream")} type="button">
                播放
              </button>
              <button className={panelButtonClass("history")} onClick={() => setActivePanel("history")} type="button">
                记录
              </button>
            </div>

            {activePanel === "summary" ? <div className="mt-4 text-sm leading-7 text-slate-700">{summary ?? "暂无摘要。"} </div> : null}

            {activePanel === "review" ? (
              <ul className="mt-4 space-y-2 text-sm text-slate-700">
                {reasons.length > 0 ? (
                  reasons.map((reason) => (
                    <li key={`${reason.code}-${reason.message}`} className="rounded-[18px] border border-slate-200 bg-slate-50 px-3 py-2">
                      <span className="text-slate-500">{reason.code}</span> {reason.message}
                    </li>
                  ))
                ) : (
                  <li className="rounded-[18px] border border-slate-200 bg-slate-50 px-3 py-2 text-slate-500">暂无审核轨迹。</li>
                )}
              </ul>
            ) : null}

            {activePanel === "stream" ? (
              <div className="mt-4 grid gap-2 text-sm text-slate-700">
                <p>BVID：{selectedVideo.bvid}</p>
                <p>CID：{selectedVideo.cid ?? cid ?? "未知"}</p>
                <p>当前画质：{resolvedQualityLabel || bestQuality || "未知"}</p>
                <p>
                  可用清晰度：
                  {resolvedQualityOptions.length > 0
                    ? resolvedQualityOptions.map((option) => option.label).join(" / ")
                    : allQualities || "未获取"}
                </p>
              </div>
            ) : null}

            {activePanel === "history" ? (
              <div className="mt-4 grid gap-2 text-sm text-slate-700">
                <p>播放进度：{progressState.progressPercent.toFixed(2)}%</p>
                <p>当前位置：{progressState.positionSeconds.toFixed(2)} 秒</p>
                <p>总时长：{progressState.durationSeconds > 0 ? `${progressState.durationSeconds.toFixed(2)} 秒` : "未知"}</p>
                <p>播放记录：{progressState.sessionCount} 次</p>
                <p>最近播放：{progressState.lastPlayedAt ? new Date(progressState.lastPlayedAt).toLocaleString() : "暂无"}</p>
              </div>
            ) : null}
          </div>
        </aside>
      </div>
    </section>
  );
}
