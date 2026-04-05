"use client";

import type { GameVisualizationElement, GameVisualizationStep, ShotChartShot } from "@/lib/types";

export interface CourtPoint3D {
  x: number;
  y: number;
  z: number;
}

export const COURT_3D = {
  halfWidth: 25,
  halfLength: 47,
  hoopRadius: 0.75,
  rimHeight: 10,
  rimZ: 0,
  backboardZ: -1.25,
  backboardWidth: 6,
  backboardHeight: 3.5,
  laneHalfWidth: 8,
  laneDepthFromBaseline: 19,
  freeThrowLineZ: 15,
  centerCircleRadius: 6,
  threePointRadius: 23.75,
  cornerThreeX: 22,
  baselineZ: -4,
  floorStartZ: -4,
  floorEndZ: 43,
} as const;

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function getShotDistance(shot: ShotChartShot): number {
  if (typeof shot.distance === "number" && Number.isFinite(shot.distance)) {
    return Math.max(0, shot.distance);
  }
  const launch = shotToCourtPoint(shot);
  return Math.sqrt(launch.x * launch.x + launch.z * launch.z);
}

export function shotToCourtPoint(shot: ShotChartShot): CourtPoint3D {
  const x = clamp((shot.loc_x ?? 0) / 10, -COURT_3D.halfWidth + 0.5, COURT_3D.halfWidth - 0.5);
  const z = clamp((shot.loc_y ?? 0) / 10, COURT_3D.baselineZ, COURT_3D.floorEndZ);
  return { x, y: 0.12, z };
}

export function shotLaunchPoint(shot: ShotChartShot): CourtPoint3D {
  const floorPoint = shotToCourtPoint(shot);
  const height = 6.1 + Math.min(shot.distance ?? getShotDistance(shot), 34) * 0.04;
  return { ...floorPoint, y: height };
}

export function shotArcHeight(shot: ShotChartShot): number {
  const distance = getShotDistance(shot);
  const shotValueBonus = shot.shot_value === 3 ? 1.1 : 0.4;
  return clamp(7.5 + distance * 0.34 + shotValueBonus, 12.5, 21);
}

export function shotArcPoints(shot: ShotChartShot, segments = 28): CourtPoint3D[] {
  const start = shotLaunchPoint(shot);
  const rim = { x: 0, y: COURT_3D.rimHeight, z: COURT_3D.rimZ };
  const apex = {
    x: start.x * 0.26,
    y: shotArcHeight(shot),
    z: start.z * 0.26,
  };
  const points: CourtPoint3D[] = [];
  for (let index = 0; index <= segments; index += 1) {
    const t = index / segments;
    const omt = 1 - t;
    points.push({
      x: omt * omt * start.x + 2 * omt * t * apex.x + t * t * rim.x,
      y: omt * omt * start.y + 2 * omt * t * apex.y + t * t * rim.y,
      z: omt * omt * start.z + 2 * omt * t * apex.z + t * t * rim.z,
    });
  }
  return points;
}

export function visualizationStepCenter(step: GameVisualizationStep): CourtPoint3D {
  const exactElements = step.elements.filter(
    (element) =>
      (element.exactness === "exact" || element.kind === "shot") &&
      element.x != null &&
      element.z != null
  );
  const source = exactElements.length > 0 ? exactElements : step.elements.filter((element) => element.x != null && element.z != null);
  if (source.length === 0) {
    return { x: 0, y: 0, z: 16 };
  }
  const totals = source.reduce(
    (acc, element) => ({
      x: acc.x + (element.x ?? 0),
      y: acc.y + (element.y ?? 0),
      z: acc.z + (element.z ?? 0),
    }),
    { x: 0, y: 0, z: 0 }
  );
  return {
    x: totals.x / source.length,
    y: totals.y / source.length,
    z: totals.z / source.length,
  };
}

export function visualizationStepPositions(step: GameVisualizationStep): CourtPoint3D[] {
  return step.elements
    .filter((element) => element.x != null && element.z != null)
    .map((element) => ({
      x: element.x ?? 0,
      y: element.y ?? 0,
      z: element.z ?? 0,
    }));
}

export function elementExactnessColor(exactness: GameVisualizationElement["exactness"]): string {
  switch (exactness) {
    case "exact":
      return "#38bdf8";
    case "inferred":
      return "#f59e0b";
    default:
      return "#94a3b8";
  }
}

export function supportsWebGL(): boolean {
  if (typeof window === "undefined") {
    return true;
  }
  try {
    const canvas = document.createElement("canvas");
    return Boolean(
      window.WebGLRenderingContext &&
        (canvas.getContext("webgl2") || canvas.getContext("webgl") || canvas.getContext("experimental-webgl"))
    );
  } catch {
    return false;
  }
}
