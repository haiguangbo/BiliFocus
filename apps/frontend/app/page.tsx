import { ExploreView } from "@/components/explore-view";
import { getPreferences } from "@/lib/api";

export default async function ExplorePage() {
  const preferences = await getPreferences();
  return <ExploreView preferences={preferences} />;
}
