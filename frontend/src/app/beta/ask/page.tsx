import { Suspense } from "react";
import AskWorkspace from "@/components/AskWorkspace";

export default function AskPage() {
  return (
    <Suspense>
      <AskWorkspace />
    </Suspense>
  );
}
