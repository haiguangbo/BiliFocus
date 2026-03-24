"use client";

import { Brain, DatabaseZap, SearchCheck, ShieldCheck, UploadCloud } from "lucide-react";

import { CurationJobStage, CurationJobStatus, PipelineStageTrace } from "@/types/api";

type SmartFetchOrchestrationFlowProps = {
  jobStatus?: CurationJobStatus | "";
  running: boolean;
  activeStage?: CurationJobStage | null;
  progressMessage?: string;
  stageHistory?: CurationJobStage[];
  pipelineTrace: {
    planner: PipelineStageTrace;
    reviewer: PipelineStageTrace;
    classifier: PipelineStageTrace;
  } | null;
};

type FlowStage = {
  key: CurationJobStage;
  title: string;
  detail: string;
  source: string;
  status: "waiting" | "running" | "completed" | "fallback" | "skipped";
  Icon: typeof Brain;
};

function resolveSource(agent: string | undefined, fallback: string): string {
  if (!agent) {
    return fallback;
  }
  if (agent.startsWith("crewai.")) {
    return "CrewAI Agent";
  }
  if (agent.startsWith("volcengine.")) {
    return "火山模型";
  }
  if (agent.startsWith("openai.")) {
    return "OpenAI 模型";
  }
  if (agent.startsWith("local.")) {
    return "本地规则";
  }
  return fallback;
}

function normalizeStatus(trace: PipelineStageTrace | undefined, running: boolean, index: number): FlowStage["status"] {
  if (trace?.status === "completed") {
    return "completed";
  }
  if (trace?.status === "fallback") {
    return "fallback";
  }
  if (running && index === 0) {
    return "running";
  }
  return "waiting";
}

const FLOW_ORDER = ["planner", "collector", "reviewer", "classifier", "sync"] as const;

function stageToFlowIndex(stage: CurationJobStage | null | undefined): number {
  if (!stage) {
    return -1;
  }
  if (stage === "completed") {
    return FLOW_ORDER.length;
  }
  return FLOW_ORDER.indexOf(stage as (typeof FLOW_ORDER)[number]);
}

function runtimeStatus(stageKey: CurationJobStage, running: boolean, activeFlowIndex: number): FlowStage["status"] {
  if (!running) {
    return "waiting";
  }
  const currentIndex = FLOW_ORDER.indexOf(stageKey as (typeof FLOW_ORDER)[number]);
  if (currentIndex === -1) {
    return "waiting";
  }
  if (activeFlowIndex > currentIndex) {
    return "completed";
  }
  if (activeFlowIndex === currentIndex) {
    return "running";
  }
  return "waiting";
}

function finalStatusForStage(
  stageKey: CurationJobStage,
  {
    jobStatus,
    stageHistory,
  }: {
    jobStatus: CurationJobStatus | "" | undefined;
    stageHistory: CurationJobStage[];
  },
): FlowStage["status"] {
  if (stageHistory.includes(stageKey)) {
    return "completed";
  }
  if (jobStatus === "completed" || jobStatus === "failed") {
    return "skipped";
  }
  return "waiting";
}

function statusLabel(status: FlowStage["status"]): string {
  if (status === "completed") {
    return "已完成";
  }
  if (status === "fallback") {
    return "已执行";
  }
  if (status === "running") {
    return "进行中";
  }
  if (status === "skipped") {
    return "未执行";
  }
  return "等待中";
}

function statusClassName(status: FlowStage["status"]): string {
  if (status === "completed") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (status === "fallback") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  if (status === "running") {
    return "border-blue-200 bg-blue-50 text-blue-700";
  }
  if (status === "skipped") {
    return "border-slate-200 bg-slate-100 text-slate-500";
  }
  return "border-slate-200 bg-slate-50 text-slate-500";
}

export function SmartFetchOrchestrationFlow({
  jobStatus,
  running,
  activeStage,
  progressMessage,
  stageHistory = [],
  pipelineTrace,
}: SmartFetchOrchestrationFlowProps) {
  const activeFlowIndex = stageToFlowIndex(activeStage);
  const hasVisitedStage = (stage: CurationJobStage) => stageHistory.includes(stage);
  const stages: FlowStage[] = [
    {
      key: "planner",
      title: "理解目标",
      detail:
        running && activeStage === "planner" && progressMessage
          ? progressMessage
          : pipelineTrace?.planner.summary || "先理解你的学习目标，拆成更适合检索的方向。",
      source: resolveSource(pipelineTrace?.planner.agent, "模型服务"),
      status: pipelineTrace
        ? normalizeStatus(pipelineTrace.planner, false, 0)
        : running
          ? runtimeStatus("planner", running, activeFlowIndex)
          : finalStatusForStage("planner", { jobStatus, stageHistory }),
      Icon: Brain,
    },
    {
      key: "collector",
      title: "拉取候选",
      detail:
        running && activeStage === "collector" && progressMessage
          ? progressMessage
          : pipelineTrace?.planner.outputs.length
          ? `会围绕 ${pipelineTrace.planner.outputs.slice(0, 4).join(" / ")} 这些方向拉取候选。`
          : "使用规划出的关键词，从 Bilibili 拉取候选视频并汇总结果。",
      source: "Bilibili 提供方",
      status: pipelineTrace || hasVisitedStage("collector")
        ? "completed"
        : running
          ? runtimeStatus("collector", running, activeFlowIndex)
          : finalStatusForStage("collector", { jobStatus, stageHistory }),
      Icon: SearchCheck,
    },
    {
      key: "reviewer",
      title: "筛掉噪声",
      detail:
        running && activeStage === "reviewer" && progressMessage
          ? progressMessage
          : pipelineTrace?.reviewer.summary || "把短视频、切片、标题党和弱相关内容先排掉。",
      source: resolveSource(pipelineTrace?.reviewer.agent, "内容规则"),
      status: pipelineTrace
        ? normalizeStatus(pipelineTrace.reviewer, false, 2)
        : running
          ? runtimeStatus("reviewer", running, activeFlowIndex)
          : finalStatusForStage("reviewer", { jobStatus, stageHistory }),
      Icon: ShieldCheck,
    },
    {
      key: "classifier",
      title: "分类整理",
      detail:
        running && activeStage === "classifier" && progressMessage
          ? progressMessage
          : pipelineTrace?.classifier.summary || "把通过的结果补标签、归类，并准备写入本地库。",
      source: resolveSource(pipelineTrace?.classifier.agent, "本地整理"),
      status: pipelineTrace
        ? normalizeStatus(pipelineTrace.classifier, false, 3)
        : running
          ? runtimeStatus("classifier", running, activeFlowIndex)
          : finalStatusForStage("classifier", { jobStatus, stageHistory }),
      Icon: DatabaseZap,
    },
    {
      key: "sync",
      title: "同步入库",
      detail:
        running && activeStage === "sync" && progressMessage
          ? progressMessage
          : hasVisitedStage("sync")
            ? "已将通过审核的结果同步到本地片库。"
            : jobStatus === "completed"
              ? "本次没有进入同步入库阶段。"
              : "把通过审核的内容写入本地 SQLite 片库，供后续浏览和整理。",
      source: "本地片库",
      status: hasVisitedStage("sync")
        ? "completed"
        : running
          ? runtimeStatus("sync", running, activeFlowIndex)
          : finalStatusForStage("sync", { jobStatus, stageHistory }),
      Icon: UploadCloud,
    },
  ];

  const headerStatus =
    running
      ? progressMessage || "任务执行中"
      : jobStatus === "failed"
        ? "本次执行失败"
        : jobStatus === "completed"
          ? progressMessage || "本次执行已完成"
          : "等待执行";
  const headerClassName =
    jobStatus === "failed"
      ? "border-rose-200 bg-rose-50 text-rose-700"
      : running || jobStatus === "running" || jobStatus === "queued"
        ? "border-blue-200 bg-blue-50 text-blue-700"
        : jobStatus === "completed"
          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
          : "border-slate-200 bg-white text-slate-600";

  return (
    <section className="mt-6 rounded-[24px] border border-slate-200 bg-slate-50/70 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-blue-700">Flow</p>
          <h4 className="mt-2 text-lg font-semibold text-slate-950">当前编排流</h4>
          <p className="mt-1 text-sm leading-6 text-slate-600">展示这次智能获取会经过哪些步骤，以及当前由谁在执行。</p>
        </div>
        <div className={`rounded-full border px-3 py-1.5 text-xs font-medium ${headerClassName}`}>
          {headerStatus}
        </div>
      </div>

      <div className="mt-5 grid gap-3 xl:grid-cols-5">
        {stages.map((stage, index) => {
          const Icon = stage.Icon;
          return (
            <div key={stage.key} className="relative rounded-[20px] border border-slate-200 bg-white p-4">
              {index < stages.length - 1 ? (
                <div className="pointer-events-none absolute -right-2 top-1/2 hidden h-px w-4 bg-slate-200 xl:block" />
              ) : null}
              <div className="flex items-start justify-between gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-blue-50 text-blue-700">
                  <Icon className="h-4 w-4" />
                </div>
                <span className={`rounded-full border px-2.5 py-1 text-[11px] font-medium ${statusClassName(stage.status)}`}>
                  {statusLabel(stage.status)}
                </span>
              </div>
              <p className="mt-4 text-sm font-medium text-slate-900">{stage.title}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">{stage.detail}</p>
              <p className="mt-3 text-xs text-slate-500">执行者：{stage.source}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
