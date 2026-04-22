"use client";

import { useEffect, useState } from "react";

import { SearchBar } from "@/components/search-bar";
import { SmartFetchOrchestrationFlow } from "@/components/smart-fetch-orchestration-flow";
import { StatusPanel } from "@/components/status-panel";
import { VideoList } from "@/components/video-list";
import { createCurationJob, getCurationJobStatus, searchVideos, syncSearchResults } from "@/lib/api";
import { CurationJobStage, CurationJobStatus, PipelineStageTrace, PreferenceConfig, VideoItem } from "@/types/api";

type ExploreViewProps = {
  preferences: PreferenceConfig;
};

type ActiveTab = "fetch" | "curation";

type FetchState = {
  query: string;
  filterText: string;
  items: VideoItem[];
  searching: boolean;
  syncing: boolean;
  error: string;
  message: string;
  lastTotal: number | null;
  lastUpdatedAt: string;
};

type CurationState = {
  objective: string;
  requirements: string;
  jobId: string;
  jobStatus: CurationJobStatus | "";
  currentStage: CurationJobStage | null;
  stageHistory: CurationJobStage[];
  progressMessage: string;
  items: VideoItem[];
  running: boolean;
  error: string;
  message: string;
  lastTotal: number | null;
  lastUpdatedAt: string;
  keywords: string[];
  pipelineTrace: {
    planner: PipelineStageTrace;
    reviewer: PipelineStageTrace;
    classifier: PipelineStageTrace;
  } | null;
};

const STORAGE_KEY = "bilifocus:explore-state:v2";

function buildDefaultFetchState(preferences: PreferenceConfig): FetchState {
  return {
    query: "AI Agent 系统设计",
    filterText: preferences.default_filter_text || "只看教程，排除直播切片，不要标题党",
    items: [],
    searching: false,
    syncing: false,
    error: "",
    message: "",
    lastTotal: null,
    lastUpdatedAt: "",
  };
}

function buildDefaultCurationState(): CurationState {
  return {
    objective: "围绕 AI、大模型、Agent、系统设计与工程化实践，自动筛选适合长期学习的视频",
    requirements: "不要短视频，不要标题党，不要直播切片",
    jobId: "",
    jobStatus: "",
    currentStage: null,
    stageHistory: [],
    progressMessage: "",
    items: [],
    running: false,
    error: "",
    message: "",
    lastTotal: null,
    lastUpdatedAt: "",
    keywords: [],
    pipelineTrace: null,
  };
}

export function ExploreView({ preferences }: ExploreViewProps) {
  const [activeTab, setActiveTab] = useState<ActiveTab>("fetch");
  const [fetchState, setFetchState] = useState<FetchState>(() => buildDefaultFetchState(preferences));
  const [curationState, setCurationState] = useState<CurationState>(() => buildDefaultCurationState());
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        setHydrated(true);
        return;
      }
      const parsed = JSON.parse(raw) as {
        activeTab?: ActiveTab;
        fetchState?: Partial<FetchState>;
        curationState?: Partial<CurationState>;
      };
      if (parsed.activeTab === "fetch" || parsed.activeTab === "curation") {
        setActiveTab(parsed.activeTab);
      }
      if (parsed.fetchState) {
        setFetchState({
          ...buildDefaultFetchState(preferences),
          ...parsed.fetchState,
          searching: false,
          syncing: false,
        });
      }
      if (parsed.curationState) {
        setCurationState({
          ...buildDefaultCurationState(),
          ...parsed.curationState,
          running: false,
        });
      }
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
    } finally {
      setHydrated(true);
    }
  }, [preferences]);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        activeTab,
        fetchState: {
          ...fetchState,
          searching: false,
          syncing: false,
        },
        curationState: {
          ...curationState,
          running: false,
        },
      }),
    );
  }, [activeTab, curationState, fetchState, hydrated]);

  function mergeStageHistory(history: CurationJobStage[], stage: CurationJobStage | null | undefined) {
    if (!stage || history.includes(stage)) {
      return history;
    }
    return [...history, stage];
  }

  useEffect(() => {
    if (!curationState.running || !curationState.jobId) {
      return;
    }

    let cancelled = false;

    const pollStatus = async () => {
      try {
        const snapshot = await getCurationJobStatus(curationState.jobId);
        if (cancelled) {
          return;
        }

        if (snapshot.status === "completed" && snapshot.result) {
          setCurationState((current) => ({
            ...current,
            jobId: snapshot.job_id,
            jobStatus: snapshot.status,
            currentStage: snapshot.stage,
            stageHistory: mergeStageHistory(current.stageHistory, snapshot.stage),
            progressMessage: snapshot.progress_message,
            keywords: snapshot.result?.recommended_keywords ?? [],
            pipelineTrace: snapshot.result?.pipeline_trace ?? null,
            items: snapshot.result?.accepted_items ?? [],
            lastTotal: snapshot.result?.accepted_count ?? 0,
            lastUpdatedAt: new Date().toISOString(),
            message: `Agent 完成：推荐关键词 ${(snapshot.result?.recommended_keywords ?? []).join(" / ")}；审核 ${snapshot.result?.reviewed_count ?? 0} 条，收录 ${snapshot.result?.accepted_count ?? 0} 条，入库新增 ${snapshot.result?.saved_count ?? 0} 条。`,
            running: false,
          }));
          return;
        }

        if (snapshot.status === "failed") {
          setCurationState((current) => ({
            ...current,
            jobId: snapshot.job_id,
            jobStatus: snapshot.status,
            currentStage: snapshot.stage,
            stageHistory: mergeStageHistory(current.stageHistory, snapshot.stage),
            progressMessage: snapshot.progress_message,
            error: snapshot.error_message || "智能获取失败，请检查 backend、上游接口或模型配置。",
            message: "",
            running: false,
            pipelineTrace: null,
          }));
          return;
        }

        setCurationState((current) => ({
          ...current,
          jobId: snapshot.job_id,
          jobStatus: snapshot.status,
          currentStage: snapshot.stage,
          stageHistory: mergeStageHistory(current.stageHistory, snapshot.stage),
          progressMessage: snapshot.progress_message,
          message: snapshot.progress_message,
        }));
      } catch (error) {
        if (cancelled) {
          return;
        }
        setCurationState((current) => ({
          ...current,
          error: error instanceof Error ? error.message : "智能获取状态刷新失败，请检查 backend 是否可用。",
          message: "",
          running: false,
        }));
      }
    };

    pollStatus();
    const intervalId = window.setInterval(pollStatus, 1200);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [curationState.jobId, curationState.running]);

  async function handleSearch() {
    setActiveTab("fetch");
    setFetchState((current) => ({
      ...current,
      searching: true,
      error: "",
      message: "",
    }));
    try {
      const response = await searchVideos({
        query: fetchState.query,
        filter_text: fetchState.filterText,
        limit: preferences.default_search_limit,
        source: preferences.default_source,
      });
      setFetchState((current) => ({
        ...current,
        items: response.items,
        lastTotal: response.total,
        lastUpdatedAt: new Date().toISOString(),
        message: response.total === 0 && current.filterText.trim() ? "当前筛选条件比较严格，建议先清空筛选再看原始候选。" : "",
        error: "",
      }));
    } catch (error) {
      setFetchState((current) => ({
        ...current,
        items: [],
        lastTotal: null,
        error: error instanceof Error ? error.message : "搜索失败，请确认 backend 已启动。",
      }));
    } finally {
      setFetchState((current) => ({
        ...current,
        searching: false,
      }));
    }
  }

  async function handleSync() {
    setActiveTab("fetch");
    setFetchState((current) => ({
      ...current,
      syncing: true,
      error: "",
      message: "",
    }));
    try {
      const response = await syncSearchResults({
        query: fetchState.query,
        filter_text: fetchState.filterText,
        limit: preferences.default_search_limit,
        source: preferences.default_source,
      });
      setFetchState((current) => ({
        ...current,
        message: `同步完成：新增 ${response.saved_count} 条，跳过 ${response.skipped_count} 条。`,
        lastUpdatedAt: new Date().toISOString(),
      }));
    } catch (error) {
      setFetchState((current) => ({
        ...current,
        error: error instanceof Error ? error.message : "同步失败，请确认 backend 已启动。",
      }));
    } finally {
      setFetchState((current) => ({
        ...current,
        syncing: false,
      }));
    }
  }

  async function handleCuration() {
    setActiveTab("curation");
    setCurationState((current) => ({
      ...current,
      running: true,
      error: "",
      message: "任务已创建，正在准备执行智能获取。",
      jobId: "",
      jobStatus: "",
      currentStage: "planner",
      stageHistory: [],
      progressMessage: "任务已创建，正在准备执行智能获取。",
      pipelineTrace: null,
      items: [],
      keywords: [],
      lastTotal: null,
    }));
    try {
      const job = await createCurationJob({
        objective: curationState.objective,
        extra_requirements: curationState.requirements,
        limit_per_keyword: Math.min(6, preferences.default_search_limit),
        sync_accepted: true,
      });
      setCurationState((current) => ({
        ...current,
        jobId: job.job_id,
        jobStatus: job.status,
        currentStage: job.stage,
        stageHistory: mergeStageHistory([], job.stage),
        progressMessage: job.progress_message,
        message: job.progress_message,
      }));
    } catch (error) {
      setCurationState((current) => ({
        ...current,
        error: error instanceof Error ? error.message : "智能获取失败，请检查 backend、上游接口或模型配置。",
        jobId: "",
        jobStatus: "",
        currentStage: null,
        stageHistory: [],
        progressMessage: "",
        pipelineTrace: null,
        running: false,
      }));
    }
  }

  const currentError = activeTab === "fetch" ? fetchState.error : curationState.error;
  const currentMessage = activeTab === "fetch" ? fetchState.message : curationState.message;
  const currentItems = activeTab === "fetch" ? fetchState.items : curationState.items;
  const currentTotal = activeTab === "fetch" ? fetchState.lastTotal : curationState.lastTotal;
  const currentUpdatedAt = activeTab === "fetch" ? fetchState.lastUpdatedAt : curationState.lastUpdatedAt;
  const hasActiveFilter = Boolean(fetchState.filterText.trim());

  return (
    <main className="grid gap-6">
      <section className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-3">
            <button
              className={`rounded-full border px-4 py-2 text-sm font-medium ${activeTab === "fetch" ? "border-blue-200 bg-blue-50 text-blue-700 shadow-sm" : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"}`}
              onClick={() => setActiveTab("fetch")}
              type="button"
            >
              视频获取
            </button>
            <button
              className={`rounded-full border px-4 py-2 text-sm font-medium ${activeTab === "curation" ? "border-blue-200 bg-blue-50 text-blue-700 shadow-sm" : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"}`}
              onClick={() => setActiveTab("curation")}
              type="button"
            >
              智能获取
            </button>
          </div>
          <div className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-xs text-slate-600">
            本地缓存已启用
            {currentUpdatedAt ? ` · 上次更新 ${new Date(currentUpdatedAt).toLocaleString()}` : " · 暂无历史结果"}
          </div>
        </div>
      </section>

      {activeTab === "fetch" ? (
        <section className="grid gap-4 lg:grid-cols-[2fr_1fr]">
          <SearchBar
            filterText={fetchState.filterText}
            searching={fetchState.searching}
            syncing={fetchState.syncing}
            onFilterTextChange={(value) => setFetchState((current) => ({ ...current, filterText: value }))}
            onQueryChange={(value) => setFetchState((current) => ({ ...current, query: value }))}
            onSearch={handleSearch}
            onSync={handleSync}
            query={fetchState.query}
          />
          <StatusPanel
            title="获取说明"
            description={`先输入你想学的主题，再用筛选条件把不合适的视频排掉。觉得合适的结果再同步到本地库。默认会拉取 ${preferences.default_search_limit} 条结果，而且你刚刚搜过的关键词和筛选条件会自动保留，不会因为切换页签就消失。`}
          />
        </section>
      ) : (
        <section className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="max-w-3xl">
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-blue-600/75">Smart Fetch</p>
                <h3 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">把你的学习目标交给系统，自动找出更值得留下的内容</h3>
                <p className="mt-3 text-sm leading-7 text-slate-600">
                  你只需要说明想学什么、不要什么。系统会自动扩写搜索词、合并候选、筛掉噪声，并把更合适的结果整理进本地库。
                </p>
              </div>
              <button
                className="rounded-[18px] bg-blue-600 px-5 py-3 font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500"
                data-testid="curation-run-button"
                disabled={curationState.running || fetchState.searching || fetchState.syncing || !curationState.objective.trim()}
                onClick={handleCuration}
                type="button"
              >
                {curationState.running ? "智能获取执行中..." : "开始智能获取"}
              </button>
            </div>

            <div className="mt-6 grid gap-4 lg:grid-cols-[2fr_2fr]">
              <label className="flex flex-col gap-2 text-sm text-slate-700">
                <span>你现在想重点学什么</span>
                <textarea
                  className="min-h-32 rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none placeholder:text-slate-400 focus:border-blue-500 focus:bg-white"
                  data-testid="curation-objective-input"
                  placeholder="例如：我想系统学习 AI Agent 的架构设计、工程化实践和真实案例。"
                  value={curationState.objective}
                  onChange={(event) => setCurationState((current) => ({ ...current, objective: event.target.value }))}
                />
              </label>
              <label className="flex flex-col gap-2 text-sm text-slate-700">
                <span>哪些内容不要</span>
                <textarea
                  className="min-h-32 rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none placeholder:text-slate-400 focus:border-blue-500 focus:bg-white"
                  data-testid="curation-requirements-input"
                  placeholder="例如：不要短视频，不要标题党，不要直播切片，尽量偏系统讲解。"
                  value={curationState.requirements}
                  onChange={(event) => setCurationState((current) => ({ ...current, requirements: event.target.value }))}
                />
              </label>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-3">
              {[
                {
                  title: "会帮你做什么",
                  description: "自动把一句目标拆成多组更适合 B 站搜索的方向，不用你自己反复试词。",
                },
                {
                  title: "会替你挡掉什么",
                  description: "默认会更严格地避开短视频、直播切片、明显标题党和弱相关内容。",
                },
                {
                  title: "最后会留下什么",
                  description: "保留下来的结果会自动补标签、归类，并按你的设置同步进本地库。",
                },
              ].map((card) => (
                <div key={card.title} className="rounded-[20px] border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm font-medium text-slate-900">{card.title}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{card.description}</p>
                </div>
              ))}
            </div>

          <SmartFetchOrchestrationFlow
            activeStage={curationState.currentStage}
            jobStatus={curationState.jobStatus}
            pipelineTrace={curationState.pipelineTrace}
            progressMessage={curationState.progressMessage}
            running={curationState.running}
            stageHistory={curationState.stageHistory}
          />
        </section>
      )}

      {currentError ? (
        <div className="rounded-[20px] border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700" data-testid="explore-error-banner">
          {currentError}
        </div>
      ) : null}

      {currentMessage ? (
        <div className="rounded-[20px] border border-blue-200 bg-blue-50 p-4 text-sm text-blue-700" data-testid="explore-success-banner">
          {currentMessage}
        </div>
      ) : null}

      {currentTotal !== null ? (
        <section className="grid gap-4 lg:grid-cols-[1.6fr_1fr_1fr]" data-testid="explore-query-context">
          <div className="rounded-[24px] border border-slate-200 bg-white p-5 text-sm text-slate-700 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">当前检索</p>
            <p className="mt-3 text-lg font-medium text-slate-900">{activeTab === "curation" ? curationState.objective : fetchState.query}</p>
            <p className="mt-2 text-slate-500">{activeTab === "curation" ? curationState.requirements : hasActiveFilter ? fetchState.filterText : "未设置筛选条件"}</p>
          </div>
          <div className="rounded-[24px] border border-slate-200 bg-white p-5 text-sm text-slate-700 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">结果数量</p>
            <p className="mt-3 text-3xl font-semibold text-slate-900">{currentTotal}</p>
            <p className="mt-2 text-slate-500">{currentTotal === 0 ? "当前没有命中结果" : activeTab === "curation" ? "智能获取通过数" : "实时上游候选数"}</p>
          </div>
          <div className="rounded-[24px] border border-slate-200 bg-white p-5 text-sm text-slate-700 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">当前模式</p>
            <p className="mt-3 text-lg font-medium text-slate-900">{activeTab === "curation" ? "智能获取" : "实时取数"}</p>
            <p className="mt-2 text-slate-500">
              {activeTab === "curation"
                  ? curationState.keywords.length > 0
                  ? `关键词：${curationState.keywords.join(" / ")}`
                  : "等待智能获取输出"
                : hasActiveFilter
                  ? "已启用筛选"
                  : "原始候选列表"}
            </p>
          </div>
        </section>
      ) : null}

      <VideoList
        actionMode={activeTab === "fetch" ? "search" : undefined}
        emptyMessage={
          currentTotal === 0
            ? "当前关键词或筛选没有命中结果。可以缩短关键词，或先清空筛选条件。"
            : activeTab === "curation"
              ? "还没有智能获取结果。先填写目标并执行获取。"
              : "还没有搜索结果。先输入关键词并点击搜索。"
        }
        items={currentItems}
        loading={activeTab === "fetch" ? fetchState.searching : curationState.running}
        showDetailLink
      />
    </main>
  );
}
