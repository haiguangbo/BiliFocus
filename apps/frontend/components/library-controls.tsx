"use client";

type LibraryControlsProps = {
  q: string;
  sort: "recent" | "views" | "published_at";
  tag: string;
  categoryTags: Array<[string, number]>;
};

function buildLibraryHref(params: { q: string; sort: string; tag?: string }) {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.sort) search.set("sort", params.sort);
  if (params.tag) search.set("tag", params.tag);
  const suffix = search.toString();
  return suffix ? `/library?${suffix}` : "/library";
}

export function LibraryControls({ q, sort, tag, categoryTags }: LibraryControlsProps) {
  return (
    <section className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
      <form className="grid gap-4 md:grid-cols-[2fr_1fr_auto]">
        <label className="flex flex-col gap-2 text-sm text-slate-700">
          <span>本地筛选</span>
          <input
            className="rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900"
            defaultValue={q}
            data-testid="library-filter-input"
            name="q"
            placeholder="语义搜索：如 少儿英语动画 / AI Agent 系统设计"
          />
        </label>
        <label className="flex flex-col gap-2 text-sm text-slate-700">
          <span>排序</span>
          <select
            className="rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900"
            defaultValue={sort}
            data-testid="library-sort-select"
            name="sort"
          >
            <option value="recent">最近同步</option>
            <option value="views">播放量</option>
            <option value="published_at">发布时间</option>
          </select>
        </label>
        <div className="flex items-end gap-3">
          <button className="rounded-[18px] bg-blue-600 px-4 py-3 font-medium text-white" data-testid="library-apply-button" type="submit">
            应用
          </button>
          <a
            className="rounded-[18px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 hover:border-slate-300"
            href="/library"
          >
            重置
          </a>
        </div>
      </form>

      {categoryTags.length > 0 ? (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-slate-900">分类导航</p>
              <p className="mt-1 text-xs text-slate-500">本地搜索会同时命中标题、摘要、标签、系列名和结构化分类字段。</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <a
              className={`rounded-full border px-3 py-2 text-sm ${tag ? "border-slate-200 bg-white text-slate-700 hover:border-slate-300" : "border-blue-200 bg-blue-50 text-blue-700"}`}
              href={buildLibraryHref({ q, sort })}
            >
              全部
            </a>
            {categoryTags.map(([entry, count]) => (
              <a
                key={entry}
                className={`rounded-full border px-3 py-2 text-sm ${tag === entry ? "border-blue-200 bg-blue-50 text-blue-700" : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"}`}
                href={buildLibraryHref({ q, sort, tag: entry })}
              >
                {entry} · {count}
              </a>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
