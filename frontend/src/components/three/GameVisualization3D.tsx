"use client";

import { Suspense, startTransition, useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { Line, OrbitControls } from "@react-three/drei";
import type { GameVisualizationElement, GameVisualizationResponse } from "@/lib/types";
import {
  COURT_3D,
  elementExactnessColor,
  supportsWebGL,
  visualizationStepCenter,
  visualizationStepPositions,
} from "@/lib/shot3d";
import ProceduralHalfCourt from "./ProceduralHalfCourt";
import ThreeUnavailableState from "./ThreeUnavailableState";

interface GameVisualization3DProps {
  data: GameVisualizationResponse;
}

function SceneMarker({ element }: { element: GameVisualizationElement }) {
  const color = elementExactnessColor(element.exactness);
  return (
    <group>
      <mesh position={[element.x ?? 0, (element.y ?? 0) + 0.25, element.z ?? 0]}>
        <sphereGeometry args={[element.exactness === "exact" ? 0.42 : 0.34, 18, 18]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={element.exactness === "exact" ? 0.45 : 0.26}
        />
      </mesh>
    </group>
  );
}

function ConnectorLine({ points, color }: { points: Array<[number, number, number]>; color: string }) {
  if (points.length < 2) {
    return null;
  }
  return <Line points={points} color={color} lineWidth={1.2} />;
}

export default function GameVisualization3D({ data }: GameVisualization3DProps) {
  const [stepIndex, setStepIndex] = useState(0);
  const [hasWebGL] = useState<boolean>(() => supportsWebGL());

  useEffect(() => {
    const exactIndex = data.steps.findIndex((step) => step.exact_shot_match);
    startTransition(() => {
      setStepIndex(exactIndex >= 0 ? exactIndex : 0);
    });
  }, [data.steps]);

  const activeStep = data.steps[Math.min(stepIndex, Math.max(0, data.steps.length - 1))];
  const focus = activeStep ? visualizationStepCenter(activeStep) : { x: 0, y: 0, z: 16 };
  const cameraPosition: [number, number, number] = useMemo(
    () => [focus.x + 18, 18, Math.min(COURT_3D.floorEndZ, focus.z + 22)],
    [focus.x, focus.z]
  );
  const elementPoints = activeStep ? visualizationStepPositions(activeStep) : [];
  const connectorColor = activeStep?.exact_shot_match ? "#38bdf8" : "#94a3b8";
  const activeLinkageLabel =
    activeStep?.linkage_quality === "exact"
      ? "Exact shot linkage"
      : activeStep?.linkage_quality === "derived"
      ? "Derived shot linkage"
      : "Timeline context";

  if (hasWebGL === false) {
    return (
      <ThreeUnavailableState
        title="WebGL is unavailable on this device"
        description="The 3D visualizer needs WebGL support. The feed and exact-shot highlight path remain available in the normal Game Explorer view."
        note="If you are on a low-power browser or remote desktop session, try a hardware-accelerated browser to enable the 3D scene."
      />
    );
  }

  return (
    <div className="space-y-3 rounded-[1.5rem] border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-blue-500">3D Visualizer</p>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            {activeStep ? `Play ${activeStep.action_number}` : "No active step"}
          </h4>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {data.exact_shot_match
              ? "Exact shot linkage where available, timeline anchors otherwise."
              : activeStep?.linkage_quality === "derived"
              ? "Derived shot linkage from synced event timing and result."
              : "Analytical reconstruction from synced event order."}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <button
            onClick={() => setStepIndex((value) => Math.max(0, value - 1))}
            disabled={data.steps.length === 0}
            className="rounded-full border px-3 py-1.5"
          >
            Prev
          </button>
          <span>
            {data.steps.length === 0 ? "0 / 0" : `${Math.min(stepIndex + 1, data.steps.length)} / ${data.steps.length}`}
          </span>
          <button
            onClick={() => setStepIndex((value) => Math.min(data.steps.length - 1, value + 1))}
            disabled={data.steps.length === 0}
            className="rounded-full border px-3 py-1.5"
          >
            Next
          </button>
        </div>
      </div>

      <div className="h-[26rem] overflow-hidden rounded-[1rem] border border-gray-200 bg-[linear-gradient(180deg,#0f172a,#1e293b)] dark:border-gray-700">
        {hasWebGL === null ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-300">
            Checking 3D support...
          </div>
        ) : (
          <Suspense fallback={<div className="flex h-full items-center justify-center text-sm text-slate-300">Loading 3D visualizer…</div>}>
            <Canvas
              camera={{ position: cameraPosition, fov: 38, near: 0.1, far: 220 }}
              dpr={[1, 1.6]}
              gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
            >
              <color attach="background" args={["#111827"]} />
              <fog attach="fog" args={["#111827", 52, 140]} />
              <ambientLight intensity={0.8} />
              <hemisphereLight args={["#dbeafe", "#0f172a", 1.05]} />
              <directionalLight position={[18, 28, 22]} intensity={1.2} />
              <ProceduralHalfCourt tone="dark" />

              {activeStep?.elements.map((element, index) => (
                <SceneMarker key={`${element.kind}-${index}`} element={element} />
              ))}

              <ConnectorLine points={elementPoints.map((point) => [point.x, point.y + 0.12, point.z])} color={connectorColor} />

              <OrbitControls enablePan={false} maxPolarAngle={Math.PI / 2.05} minDistance={10} maxDistance={64} />
            </Canvas>
          </Suspense>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 text-[11px] text-gray-500 dark:text-gray-400">
        <span className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1.5 dark:border-gray-800 dark:bg-gray-800/60">
          <span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-sky-400" />
          Exact
        </span>
        <span className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1.5 dark:border-gray-800 dark:bg-gray-800/60">
          <span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-amber-400" />
          Inferred
        </span>
        <span className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1.5 dark:border-gray-800 dark:bg-gray-800/60">
          <span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-slate-400" />
          Timeline
        </span>
      </div>

      <div className="rounded-[1rem] bg-gray-50 px-3 py-2 text-xs text-gray-600 dark:bg-gray-800/60 dark:text-gray-300">
        {activeStep
          ? `${activeLinkageLabel} · ${activeStep.period ? `Q${activeStep.period}` : "Event"} ${activeStep.clock ?? ""} · ${activeStep.description ?? "No description"}`
          : "No visualization step available."}
      </div>
    </div>
  );
}
