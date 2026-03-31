import { redirect } from "next/navigation";

interface LegacyLeaderboardsPageProps {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}

function toQueryString(searchParams?: Record<string, string | string[] | undefined>) {
  const params = new URLSearchParams();
  Object.entries(searchParams ?? {}).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((entry) => params.append(key, entry));
      return;
    }
    if (value) {
      params.set(key, value);
    }
  });
  return params.toString();
}

export default async function LegacyLeaderboardsPage({ searchParams }: LegacyLeaderboardsPageProps) {
  const resolvedSearchParams = searchParams ? await searchParams : undefined;
  const query = toQueryString(resolvedSearchParams);
  redirect(query ? `/player-stats?${query}` : "/player-stats");
}
