import BracketClient from "./BracketClient";

// Render fresh on every request. The bracket page was previously static-
// prerendered (`○ /bracket` in the build output), which meant Next.js's
// Router Cache would re-serve the stale prerendered fallback (skeleton or
// off-season empty state) when users navigated away and back, so the bracket
// content never showed up on revisit. Forcing dynamic rendering pushes the
// page through the SSR pipeline each time; SWR then hydrates with the live
// bracket data immediately.
export const dynamic = "force-dynamic";

export default function BracketPage() {
  return <BracketClient />;
}
