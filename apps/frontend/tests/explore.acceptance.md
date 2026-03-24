# Frontend Acceptance Note

This note defines the minimum reusable frontend verification for the MVP.

## Explore flow

1. Open `/`.
2. Confirm the page renders:
   - search input
   - filter input
   - `搜索` button
   - `同步到本地库` button
   - result area
3. Click `搜索`.
4. Verify the page uses the centralized client in `apps/frontend/lib/api.ts` via `searchVideos(...)`.
5. Verify loading state is shown while waiting.
6. Verify returned items render through `VideoList` and `VideoCard`.
7. Click `同步到本地库`.
8. Verify the page calls `syncSearchResults(...)` and shows a success message.

## Library flow

1. Open `/library`.
2. Verify the page renders local SQLite-backed items after a sync.
3. Verify empty state appears when no local data exists.

## Detail flow

1. Open `/videos/[bvid]` from a synced item.
2. Verify the page renders title, author, metrics, tags, recommendation reasons, and source link.
3. Verify unsynced or missing `bvid` shows a stable error state.

## Settings flow

1. Open `/settings`.
2. Verify the form reads values from `GET /api/preferences`.
3. Save the form.
4. Verify the page writes through the centralized client in `apps/frontend/lib/api.ts` via `savePreferences(...)`.

## Code path

- Route pages:
  - `apps/frontend/app/page.tsx`
  - `apps/frontend/app/library/page.tsx`
  - `apps/frontend/app/settings/page.tsx`
- Client calls:
  - `apps/frontend/lib/api.ts`
- UI components:
  - `apps/frontend/components/search-bar.tsx`
  - `apps/frontend/components/video-list.tsx`
  - `apps/frontend/components/video-card.tsx`
  - `apps/frontend/components/preferences-form.tsx`
