import { LibraryControls } from "@/components/library-controls";
import { PageHeader } from "@/components/page-header";
import { VideoList } from "@/components/video-list";
import { getPreferences, listVideosWithParams } from "@/lib/api";
import { VideoItem } from "@/types/api";

const ALLOWED_SORTS = ["recent", "views", "published_at"] as const;
const PAGE_SIZE = 24;

type LibrarySort = (typeof ALLOWED_SORTS)[number];

type LibraryPageProps = {
  searchParams?: {
    q?: string;
    tag?: string;
    sort?: string;
    page?: string;
  };
};

function buildLibraryHref(params: { q: string; sort: string; tag?: string; page?: number }) {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.sort) search.set("sort", params.sort);
  if (params.tag) search.set("tag", params.tag);
  if (params.page && params.page > 1) search.set("page", String(params.page));
  const suffix = search.toString();
  return suffix ? `/library?${suffix}` : "/library";
}

function groupByCategory(items: VideoItem[]) {
  const grouped = new Map<string, VideoItem[]>();
  for (const item of items) {
    const key = item.primary_category || item.secondary_category || "未分类";
    grouped.set(key, [...(grouped.get(key) ?? []), item]);
  }
  return Array.from(grouped.entries()).sort((left, right) => right[1].length - left[1].length);
}

export default async function LibraryPage({ searchParams }: LibraryPageProps) {
  try {
    const preferences = await getPreferences();
    const q = searchParams?.q ?? "";
    const tag = searchParams?.tag ?? "";
    const page = Math.max(1, Number(searchParams?.page ?? "1") || 1);
    const requestedSort = searchParams?.sort ?? preferences.library_sort;
    const sort: LibrarySort = ALLOWED_SORTS.includes(requestedSort as LibrarySort)
      ? (requestedSort as LibrarySort)
      : "recent";
    const response = await listVideosWithParams({ q, tag, sort, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE });
    const categoryTags = Array.from(
      response.items.reduce((map, item) => {
        const candidates = [
          item.primary_category,
          item.secondary_category,
          ...item.tags.filter((entry) => !["real", "bilibili"].includes(entry.toLowerCase())),
        ].filter((entry): entry is string => Boolean(entry && entry.length >= 2));
        for (const entry of candidates) {
          map.set(entry, (map.get(entry) ?? 0) + 1);
        }
        return map;
      }, new Map<string, number>()).entries(),
    )
      .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0], "zh-CN"))
      .slice(0, 16);
    const clusteredSections = groupByCategory(response.items);
    const totalPages = Math.max(1, Math.ceil(response.total / PAGE_SIZE));
    return (
      <main className="grid gap-6">
        <PageHeader
          aside={
            <div className="grid gap-1 rounded-[20px] border border-slate-200 bg-slate-50 px-4 py-3 text-right">
              <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">当前视图</span>
              <span className="text-2xl font-semibold tracking-tight text-slate-950">{response.total}</span>
              <span className="text-xs text-slate-500">总条目 · 第 {page} / {totalPages} 页</span>
            </div>
          }
          description={`这里展示的是已经同步到本地 SQLite 的内容。当前排序策略：${sort}。${tag ? `当前分类：${tag}。` : ""}支持关键词检索、分类导航与分页浏览。`}
          eyebrow="Library"
          title="本地片库与分类整理"
        />
        <LibraryControls categoryTags={categoryTags} q={q} sort={sort} tag={tag} />
        {clusteredSections.length > 0 ? (
          <section className="grid gap-6">
            {clusteredSections.map(([categoryName, items]) => (
              <section key={categoryName} className="grid gap-4">
                <div className="flex items-end justify-between gap-3 rounded-[24px] border border-slate-200 bg-white px-5 py-4 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-600/75">分类簇</p>
                    <h3 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">{categoryName}</h3>
                    <p className="mt-1 text-sm text-slate-500">
                      {items[0]?.secondary_category && items[0]?.secondary_category !== categoryName ? `子类：${items[0].secondary_category} · ` : ""}
                      本页 {items.length} 条
                    </p>
                  </div>
                  {items[0]?.series_title ? (
                    <span className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs text-blue-700">
                      代表系列：{items[0].series_title}
                    </span>
                  ) : null}
                </div>
                <VideoList actionMode="library" emptyMessage="当前分类暂无内容。" items={items} showDetailLink />
              </section>
            ))}
          </section>
        ) : (
          <VideoList actionMode="library" emptyMessage="本地库为空。" items={response.items} showDetailLink />
        )}
        <section className="flex flex-wrap items-center justify-between gap-3 rounded-[24px] border border-slate-200 bg-white px-5 py-4 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
          <p className="text-sm text-slate-600">
            分页浏览：第 {page} / {totalPages} 页
          </p>
          <div className="flex flex-wrap gap-2">
            <a
              className={`rounded-[18px] px-4 py-2 text-sm ${page > 1 ? "border border-slate-200 bg-white text-slate-700 hover:border-slate-300" : "cursor-not-allowed border border-slate-200 bg-slate-100 text-slate-400"}`}
              href={page > 1 ? buildLibraryHref({ q, sort, tag: tag || undefined, page: page - 1 }) : "#"}
            >
              上一页
            </a>
            <a
              className={`rounded-[18px] px-4 py-2 text-sm ${page < totalPages ? "border border-slate-200 bg-white text-slate-700 hover:border-slate-300" : "cursor-not-allowed border border-slate-200 bg-slate-100 text-slate-400"}`}
              href={page < totalPages ? buildLibraryHref({ q, sort, tag: tag || undefined, page: page + 1 }) : "#"}
            >
              下一页
            </a>
          </div>
        </section>
      </main>
    );
  } catch {
    return (
      <main className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
        本地片库加载失败，请确认 backend 已启动且接口可访问。
      </main>
    );
  }
}
