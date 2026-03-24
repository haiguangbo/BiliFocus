"use client";

import { useEffect, useState } from "react";

type SearchBarProps = {
  query: string;
  filterText: string;
  searching: boolean;
  syncing: boolean;
  onQueryChange: (value: string) => void;
  onFilterTextChange: (value: string) => void;
  onSearch: () => void;
  onSync: () => void;
};

export function SearchBar({
  query,
  filterText,
  searching,
  syncing,
  onQueryChange,
  onFilterTextChange,
  onSearch,
  onSync,
}: SearchBarProps) {
  const suggestions = [
    "AI Agent 系统设计",
    "大模型 工程化",
    "RAG 实战",
    "少儿英语启蒙动画",
    "系统设计 面试",
    "Python 自动化",
  ];
  const [suggestionIndex, setSuggestionIndex] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setSuggestionIndex((current) => (current + 1) % suggestions.length);
    }, 2600);
    return () => window.clearInterval(timer);
  }, [suggestions.length]);

  return (
    <section className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
      <div className="mb-5">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-blue-600/75">视频获取</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">输入关键词，开始找片</h2>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-[2fr_2fr_auto_auto]">
        <label className="flex flex-col gap-2 text-sm text-slate-700">
          <span>搜索关键词</span>
          <input
            className="rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white"
            data-testid="search-query-input"
            placeholder={`例如：${suggestions[suggestionIndex]}`}
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-2 text-sm text-slate-700">
          <span>筛选条件</span>
          <input
            className="rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none ring-0 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white"
            data-testid="search-filter-input"
            placeholder="例如：只看教程，排除直播切片，不要标题党"
            value={filterText}
            onChange={(event) => onFilterTextChange(event.target.value)}
          />
        </label>
        <div className="flex items-end">
          <button
            className="w-full rounded-[18px] bg-blue-600 px-4 py-3 font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:text-slate-500"
            data-testid="search-submit-button"
            onClick={onSearch}
            disabled={searching || syncing || !query.trim()}
            type="button"
          >
            {searching ? "搜索中..." : "搜索"}
          </button>
        </div>
        <div className="flex items-end">
          <button
            className="w-full rounded-[18px] border border-slate-200 bg-white px-4 py-3 font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
            data-testid="search-sync-button"
            onClick={onSync}
            disabled={searching || syncing || !query.trim()}
            type="button"
          >
            {syncing ? "同步中..." : "同步到本地库"}
          </button>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-slate-500">推荐主题</span>
        {suggestions.slice(suggestionIndex, suggestionIndex + 3).concat(suggestions.slice(0, Math.max(0, suggestionIndex + 3 - suggestions.length))).map((suggestion) => (
          <button
            key={suggestion}
            className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-700 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
            onClick={() => onQueryChange(suggestion)}
            type="button"
          >
            {suggestion}
          </button>
        ))}
        <span className="text-xs text-slate-400">筛选示例：排除直播切片 / 不要标题党 / 只看教程</span>
      </div>
    </section>
  );
}
