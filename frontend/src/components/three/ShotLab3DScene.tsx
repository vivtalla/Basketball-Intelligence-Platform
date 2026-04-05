"use client";

import { Suspense, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { Line, OrbitControls } from "@react-three/drei";
import type { ShotChartShot } from "@/lib/types";
import {
  shotArcPoints,
  shotLaunchPoint,
  shotToCourtPoint,
  supportsWebGL,
} from "@/lib/shot3d";
import ProceduralHalfCourt from "./ProceduralHalfCourt";
import ThreeUnavailableState from "./ThreeUnavailableState";

interface ShotLab3DSceneProps {
  shots: ShotChartShot[];
}

type CameraPreset = "hero" | "sideline" | "rim";

function ShotMarker({ shot }: { shot: ShotChartShot }) {
  const arcPoints = useMemo(
    () => shotArcPoints(shot).map((point) => [point.x, point.y, point.z] as [number, number, number]),
    [shot]
  );
  const floorPoint = shotToCourtPoint(shot);
  const launchPoint = shotLaunchPoint(shot);
  const color = shot.shot_made ? "#2f855a" : "#c05621";

  return (
    <group>
      <Line points={arcPoints} color={color} lineWidth={1.8} />
      <mesh position={[floorPoint.x, floorPoint.y + 0.05, floorPoint.z]}>
        <circleGeometry args={[0.55, 24]} />
        <meshStandardMaterial color={color} transparent opacity={0.28} />
      </mesh>
      <mesh position={[launchPoint.x, launchPoint.y, launchPoint.z]}>
        <sphereGeometry args={[0.17, 16, 16]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.42} />
      </mesh>
    </group>
  );
}

export default function ShotLab3DScene({ shots }: ShotLab3DSceneProps) {
  const [cameraPreset, setCameraPreset] = useState<CameraPreset>("hero");
  const [hasWebGL] = useState<boolean>(() => supportsWebGL());

  const cameraPosition: [number, number, number] = useMemo(() => {
    if (cameraPreset === "sideline") {
      return [38, 22, 24];
    }
    if (cameraPreset === "rim") {
      return [0, 16, 11];
    }
    return [0, 32, 54];
  }, [cameraPreset]);

  const visibleShots = shots.slice(0, 180);
  const madeCount = visibleShots.filter((shot) => shot.shot_made).length;

  if (hasWebGL === false) {
    return (
      <ThreeUnavailableState
        title="WebGL is unavailable on this device"
        description="The 3D shot scene needs WebGL support. The 2D shot lab remains fully usable, and this view will render automatically once the browser can create a WebGL context."
        note="If you are on a low-power or remote browser, try a different device or enable hardware acceleration."
      />
    );
  }

  return (
    <div className="space-y-3 rounded-[1.5rem] border border-[rgba(25,52,42,0.12)] bg-[rgba(255,255,255,0.72)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="bip-kicker mb-1">3D View</p>
          <h4 className="text-sm font-semibold text-[var(--foreground)]">
            Reconstructed shot arcs on a procedural half-court
          </h4>
          <p className="mt-1 text-xs text-[var(--muted)]">
            {visibleShots.length} shots · {madeCount} made · arcs are reconstructed, not tracked ball flight
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs">
          {[
            ["hero", "Hero orbit"],
            ["sideline", "Sideline"],
            ["rim", "Rim lock"],
          ].map(([id, label]) => (
            <button
              key={id}
              onClick={() => setCameraPreset(id as CameraPreset)}
              className={`rounded-full px-3 py-1.5 ${cameraPreset === id ? "bip-toggle-active" : "bip-toggle"}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-[1.25rem] bg-[linear-gradient(180deg,#f5efe4,#efe6d5)] p-2">
        <div className="h-[28rem] overflow-hidden rounded-[1rem] border border-[rgba(25,52,42,0.08)] bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.84),rgba(241,232,214,0.92))]">
          {hasWebGL === null ? (
            <div className="flex h-full items-center justify-center text-sm text-[var(--muted)]">
              Checking 3D support...
            </div>
          ) : (
            <Suspense fallback={<div className="flex h-full items-center justify-center text-sm text-[var(--muted)]">Loading 3D scene…</div>}>
              <Canvas
                camera={{ position: cameraPosition, fov: 34, near: 0.1, far: 220 }}
                dpr={[1, 1.6]}
                gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}
              >
                <color attach="background" args={["#f6f1e7"]} />
                <fog attach="fog" args={["#f6f1e7", 48, 130]} />
                <ambientLight intensity={0.86} />
                <hemisphereLight args={["#fff8e1", "#c7bca7", 1.08]} />
                <directionalLight position={[16, 30, 20]} intensity={1.15} castShadow={false} />
                <ProceduralHalfCourt tone="light" />

                {visibleShots.map((shot, index) => (
                  <ShotMarker key={`${shot.game_id ?? "shot"}-${shot.shot_event_id ?? index}`} shot={shot} />
                ))}

                <OrbitControls enablePan={false} maxPolarAngle={Math.PI / 2.08} minDistance={18} maxDistance={74} />
              </Canvas>
            </Suspense>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-[11px] text-[var(--muted)]">
        <span className="rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.78)] px-3 py-1.5">
          <span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-[#2f855a]" />
          Made
        </span>
        <span className="rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.78)] px-3 py-1.5">
          <span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-[#c05621]" />
          Missed
        </span>
        <span className="rounded-full border border-[rgba(25,52,42,0.1)] bg-[rgba(255,255,255,0.78)] px-3 py-1.5">
          <span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-[#94a3b8]" />
          Label / event context
        </span>
      </div>

      <p className="text-xs text-[var(--muted)]">
        Arcs are reconstructed from shot location and distance. They visualize spatial context, not tracked ball-flight data.
      </p>
    </div>
  );
}
