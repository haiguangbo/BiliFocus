"use client";

import { useEffect, useMemo, useState } from "react";

import { VideoCard } from "@/components/video-card";
import { VideoItem } from "@/types/api";

type VideoListProps = {
  items: VideoItem[];
  loading?: boolean;
  emptyMessage: string;
  showDetailLink?: boolean;
  actionMode?: "search" | "library";
};

export function VideoList({ items, loading = false, emptyMessage, showDetailLink = false, actionMode }: VideoListProps) {
  const [localItems, setLocalItems] = useState(items);

  useEffect(() => {
    setLocalItems(items);
  }, [items]);

  const listClassName = useMemo(
    () =>
      actionMode === "library"
        ? "grid gap-5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4"
        : "grid gap-4",
    [actionMode],
  );

  if (loading) {
    return (
      <div className="rounded-[24px] border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500 shadow-[0_16px_40px_rgba(15,23,42,0.04)]">
        正在加载视频数据...
      </div>
    );
  }

  if (localItems.length === 0) {
    return (
      <div className="rounded-[24px] border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500 shadow-[0_16px_40px_rgba(15,23,42,0.04)]" data-testid="video-list-empty">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className={listClassName} data-testid="video-list">
      {localItems.map((video) => (
        <VideoCard
          actionMode={actionMode}
          key={video.bvid}
          onDeleted={(deletedBvid) => setLocalItems((current) => current.filter((item) => item.bvid !== deletedBvid))}
          showDetailLink={showDetailLink}
          video={video}
        />
      ))}
    </div>
  );
}
