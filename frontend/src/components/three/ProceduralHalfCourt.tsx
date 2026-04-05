"use client";

import { useMemo } from "react";
import { Line } from "@react-three/drei";
import { COURT_3D } from "@/lib/shot3d";

interface ProceduralHalfCourtProps {
  tone?: "light" | "dark";
}

const PALETTE = {
  light: {
    floor: "#f4efe5",
    panel: "#faf7f0",
    line: "rgba(35,55,49,0.72)",
    faint: "rgba(35,55,49,0.28)",
    glow: "rgba(255,232,156,0.2)",
    rim: "#21483b",
    backboard: "#d8d0c2",
  },
  dark: {
    floor: "#172033",
    panel: "#243149",
    line: "rgba(236,243,255,0.9)",
    faint: "rgba(236,243,255,0.34)",
    glow: "rgba(255,229,153,0.15)",
    rim: "#fff4c7",
    backboard: "#b7c3d4",
  },
} as const;

function arcPoints(radius: number, start = -68, end = 68, step = 2): [number, number, number][] {
  const points: [number, number, number][] = [];
  for (let degree = start; degree <= end; degree += step) {
    const radians = (degree * Math.PI) / 180;
    points.push([radius * Math.sin(radians), 0.06, radius * Math.cos(radians)]);
  }
  return points;
}

export default function ProceduralHalfCourt({ tone = "light" }: ProceduralHalfCourtProps) {
  const palette = PALETTE[tone];
  const threeArc = useMemo(() => arcPoints(COURT_3D.threePointRadius), []);
  const centerCircle = useMemo(() => arcPoints(COURT_3D.centerCircleRadius, 0, 360, 4), []);

  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 19.5]}>
        <planeGeometry args={[COURT_3D.halfWidth * 2, COURT_3D.floorEndZ - COURT_3D.floorStartZ]} />
        <meshStandardMaterial color={palette.floor} roughness={0.92} metalness={0.02} />
      </mesh>

      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 19.5]}>
        <planeGeometry args={[COURT_3D.halfWidth * 2 - 2, COURT_3D.floorEndZ - COURT_3D.floorStartZ - 2]} />
        <meshStandardMaterial color={palette.panel} transparent opacity={0.18} />
      </mesh>

      <Line
        points={[
          [-COURT_3D.halfWidth, 0.03, COURT_3D.baselineZ],
          [-COURT_3D.halfWidth, 0.03, COURT_3D.floorEndZ],
          [COURT_3D.halfWidth, 0.03, COURT_3D.floorEndZ],
          [COURT_3D.halfWidth, 0.03, COURT_3D.baselineZ],
          [-COURT_3D.halfWidth, 0.03, COURT_3D.baselineZ],
        ]}
        color={palette.line}
        lineWidth={1.2}
      />

      <Line
        points={[
          [-COURT_3D.cornerThreeX, 0.05, COURT_3D.baselineZ],
          [-COURT_3D.cornerThreeX, 0.05, 14],
          [COURT_3D.cornerThreeX, 0.05, 14],
          [COURT_3D.cornerThreeX, 0.05, COURT_3D.baselineZ],
        ]}
        color={palette.glow}
        lineWidth={5.2}
      />
      <Line
        points={[
          [-COURT_3D.cornerThreeX, 0.06, COURT_3D.baselineZ],
          [-COURT_3D.cornerThreeX, 0.06, 14],
          [COURT_3D.cornerThreeX, 0.06, 14],
          [COURT_3D.cornerThreeX, 0.06, COURT_3D.baselineZ],
        ]}
        color={palette.line}
        lineWidth={2.2}
      />
      <Line points={threeArc} color={palette.glow} lineWidth={5.2} />
      <Line points={threeArc} color={palette.line} lineWidth={2.2} />

      <Line
        points={[
          [-COURT_3D.laneHalfWidth, 0.07, COURT_3D.baselineZ],
          [-COURT_3D.laneHalfWidth, 0.07, COURT_3D.laneDepthFromBaseline - 4],
          [COURT_3D.laneHalfWidth, 0.07, COURT_3D.laneDepthFromBaseline - 4],
          [COURT_3D.laneHalfWidth, 0.07, COURT_3D.baselineZ],
        ]}
        color={palette.faint}
        lineWidth={1.2}
      />
      <Line points={centerCircle} color={palette.faint} lineWidth={1} />
      <Line
        points={[
          [-8, 0.08, COURT_3D.baselineZ],
          [-8, 0.08, COURT_3D.freeThrowLineZ],
          [8, 0.08, COURT_3D.freeThrowLineZ],
          [8, 0.08, COURT_3D.baselineZ],
        ]}
        color={palette.faint}
        lineWidth={1}
      />

      <mesh position={[0, COURT_3D.rimHeight, COURT_3D.rimZ]}>
        <torusGeometry args={[COURT_3D.hoopRadius, 0.08, 12, 32]} />
        <meshStandardMaterial color={palette.rim} emissive={palette.rim} emissiveIntensity={0.32} />
      </mesh>

      <mesh position={[0, COURT_3D.rimHeight + 2.9, COURT_3D.backboardZ]}>
        <boxGeometry args={[COURT_3D.backboardWidth, COURT_3D.backboardHeight, 0.2]} />
        <meshStandardMaterial color={palette.backboard} roughness={0.82} metalness={0.04} />
      </mesh>

      <mesh position={[0, COURT_3D.rimHeight - 0.4, COURT_3D.rimZ - 0.55]}>
        <sphereGeometry args={[0.12, 12, 12]} />
        <meshStandardMaterial color={palette.rim} emissive={palette.rim} emissiveIntensity={0.55} />
      </mesh>

    </group>
  );
}
