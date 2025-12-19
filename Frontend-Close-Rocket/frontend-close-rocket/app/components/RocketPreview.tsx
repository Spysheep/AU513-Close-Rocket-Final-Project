"use client";

import React from "react";
import {
  trapezoidalFinVertices,
  ellipticalFinPoints,
  svgPathFromPoints,
  diamondFinVertices,
} from "./finGeometry";

export type AileronType = "trapezoidale" | "elliptique" | "diamant";

export interface RocketPreviewProps {
  coiffe: { shape_param?: number; diameter_mm?: number; length_mm?: number };
  tube: { diameter_mm?: number; length_mm?: number };
  aileron: {
    type?: AileronType;
    number?: number;
    trapezoid?: { height?: number; length?: number; root_chord?: number; sweep_angle_deg?: number };
    elliptique?: { height?: number; root_chord?: number; segments?: number };
    diamant?: { height?: number; length?: number; root_chord?: number; sweep_angle_deg?: number };
  };
  rampInclinationDeg?: number; // theta_xy to tilt the whole rocket (2D)
  width?: number; // px
  height?: number; // px
}

// Simple helper: clamp and fallback for NaN/undefined
const num = (v: unknown, fb: number) =>
  typeof v === "number" && !isNaN(v) && isFinite(v) ? v : fb;

export default function RocketPreview({
  coiffe,
  tube,
  aileron,
  rampInclinationDeg = 0,
  width = 360,
  height = 520,
}: RocketPreviewProps) {
  // Defaults when form not fully filled
  const coneLen = num(coiffe.length_mm, 150);
  const coneDia = num(coiffe.diameter_mm, 60);
  const shape = Math.max(0, Math.min(1, num(coiffe.shape_param, 0.5)));

  const tubeLen = num(tube.length_mm, 300);
  const tubeDia = num(tube.diameter_mm, coneDia);

  const totalLen = coneLen + tubeLen;
  const maxDia = Math.max(coneDia, tubeDia);

  const padding = 24; // px
  const scaleLen = (height - padding * 2) / totalLen;
  const scaleDia = (width - padding * 2) / maxDia;
  const scale = Math.min(scaleLen, scaleDia);

  const centerX = width / 2;
  const topY = padding;

  const coneH = coneLen * scale;
  const coneW = coneDia * scale;
  const bodyH = tubeLen * scale;
  const bodyW = tubeDia * scale;
  const bodyTop = topY + coneH;
  const bodyBottom = bodyTop + bodyH;

  // Fins configuration
  const finType = aileron.type ?? "trapezoidale";
  const finCount = Math.max(3, Math.floor(num(aileron.number, 3)));

  // Definitions per user:
  // emplanture = longueur le long du bord de la fusée (root chord)
  // longueur (trapezoïde) = distance voulue au bout de l'aileron (span outboard)
  // hauteur (elliptique) = distance verticale jusqu'au sommet de l'arc
  // longueur (diamant) = longueur du bord supérieur (tip chord)

  // Nose shape: shape in [0,1] biases cone curve. We'll approximate with a quadratic curve between triangle and ogive.
  const nosePath = () => {
    const apexX = centerX;
    const apexY = topY;
    const baseY = topY + coneH;
    const leftBaseX = centerX - coneW / 2;
    const rightBaseX = centerX + coneW / 2;

    // Control points move with shape: 0 -> straight cone, 1 -> more curved ogive
    const ctrlOffset = (coneW / 2) * (0.6 * shape);

    return `M ${apexX} ${apexY}
            Q ${apexX - ctrlOffset} ${apexY + coneH * 0.5}, ${leftBaseX} ${baseY}
            L ${rightBaseX} ${baseY}
            Q ${apexX + ctrlOffset} ${apexY + coneH * 0.5}, ${apexX} ${apexY}
            Z`;
  };

  // Fin paths (left/right) using geometry functions
  const finPaths = () => {
    const yBase = bodyBottom;
    const xLeft = centerX - bodyW / 2;
    const xRight = centerX + bodyW / 2;

    // Rotate local fin geometry by ±90° so the fins stick out perpendicularly from the fuselage.
    // Right fin: +90° (outward to the right) -> (x', y') = (-y, x)
    // Left fin:  -90° (outward to the left)  -> (x', y') = ( y, -x)
    const rotatePlus90 = (p: [number, number]): [number, number] => {
      const [x, y] = p; return [-y, x];
    };
    // Note: rotateMinus90 is no longer needed since both fins use +90° rotation and differ only by lateral translation.

    if (finType === "diamant") {
      // Inputs with safe fallbacks
      const height = num(aileron.diamant?.height, Math.max(18, bodyH * 0.18));
      const root = num(aileron.diamant?.root_chord, Math.max(14, bodyW * 0.7));
      const tip = num(aileron.diamant?.length, Math.max(40, bodyW * 1.0));
      const sweep = num(aileron.diamant?.sweep_angle_deg, 15);

      // Local vertices (origin at inner-bottom corner)
      const vertsLocal = diamondFinVertices(height, tip, root, sweep);
      const rotated = vertsLocal.map(rotatePlus90);
      // After rotation, align bottom edge of fin with bottom of rocket body
      // The fin's root chord (y=0 in local coords) becomes x=0 after rotation
      // We need to align the maximum Y (which corresponds to root_chord) with yBase
      const maxY = Math.max(...rotated.map((p) => p[1]));
      const yOffset = yBase - maxY;

      const right = svgPathFromPoints(
        rotated.map(([xr, yr]) => [xRight + xr, yOffset + yr] as [number, number])
      );
      const left = svgPathFromPoints(
        rotated.map(([xl, yl]) => [xLeft + xl, yOffset + yl] as [number, number])
      );
      return { left, right };
    }

    if (finType === "elliptique") {
      // Half-ellipse above the base: height and root chord
      const root = num(aileron.elliptique?.root_chord, Math.max(14, bodyW * 0.7));
      const h = num(aileron.elliptique?.height, Math.max(18, bodyH * 0.18));
      const segs = Math.max(8, Math.floor(num(aileron.elliptique?.segments, 48)));
      const ptsLocal = ellipticalFinPoints(h, root, segs);
      const rotated = ptsLocal.map(rotatePlus90);
      // After rotation, align bottom edge of fin with bottom of rocket body
      const maxY = Math.max(...rotated.map((p) => p[1]));
      const yOffset = yBase - maxY;

      const right = svgPathFromPoints(
        rotated.map(([xr, yr]) => [xRight + xr, yOffset + yr] as [number, number])
      );
      const left = svgPathFromPoints(
        rotated.map(([xl, yl]) => [xLeft + xl, yOffset + yl] as [number, number])
      );
      return { left, right };
    }

    // default trapezoidale
    const h = num(aileron.trapezoid?.height, Math.max(18, bodyH * 0.18));
    const root = num(aileron.trapezoid?.root_chord, Math.max(14, bodyW * 0.7));
    const topLen = num(aileron.trapezoid?.length, Math.max(8, root * 0.6));
    const angle = num(aileron.trapezoid?.sweep_angle_deg, 10);
    const vertsLocal = trapezoidalFinVertices(h, topLen, root, angle);
    const rotated = vertsLocal.map(rotatePlus90);
    // After rotation, align bottom edge of fin with bottom of rocket body
    // The fin's root chord (y=0 in local coords, from x=0 to x=root) becomes vertical after rotation
    // maxY corresponds to the bottom of the fin that should align with yBase
    const maxY = Math.max(...rotated.map((p) => p[1]));
    const yOffset = yBase - maxY;

    const right = svgPathFromPoints(
      rotated.map(([xr, yr]) => [xRight + xr, yOffset + yr] as [number, number])
    );
    const left = svgPathFromPoints(
      rotated.map(([xl, yl]) => [xLeft + xl, yOffset + yl] as [number, number])
    );
    return { left, right };
  };

  const fins = finPaths();

  // Rotate entire rocket by rampInclinationDeg and slightly apply fin inclination as a small rotation to fins
  const rocketCenterY = (topY + bodyBottom) / 2;

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
      <defs>
        <linearGradient id="body" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#8ea6ff" />
          <stop offset="100%" stopColor="#5b6dd8" />
        </linearGradient>
        <linearGradient id="nose" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#f0f4ff" />
          <stop offset="100%" stopColor="#b9c8ff" />
        </linearGradient>
      </defs>

      {/* background frame */}
      <rect x={0.5} y={0.5} width={width - 1} height={height - 1} rx={12} className="fill-white dark:fill-zinc-900" stroke="#e5e7eb" />

      <g transform={`rotate(${rampInclinationDeg} ${centerX} ${rocketCenterY})`}>
        {/* Nose */}
        <path d={nosePath()} fill="url(#nose)" stroke="#111827" strokeWidth={1} />

        {/* Body */}
        <rect
          x={centerX - bodyW / 2}
          y={bodyTop}
          width={bodyW}
          height={bodyH}
          rx={bodyW * 0.08}
          fill="url(#body)"
          stroke="#111827"
          strokeWidth={1}
        />

        {/* Fins */}
        <g>
          <path d={fins.left} fill="#9CA3AF" stroke="#111827" strokeWidth={1} />
          <path d={fins.right} fill="#9CA3AF" stroke="#111827" strokeWidth={1} />
        </g>

        {/* Exhaust nozzle suggestion */}
        <ellipse cx={centerX} cy={bodyBottom + 6} rx={bodyW * 0.18} ry={6} fill="#4B5563" />
      </g>

      {/* Info text */}
      <g>
        <text x={padding} y={height - 40} className="fill-zinc-500" fontSize={12}>
          L = {Math.round(totalLen)} mm, Dmax = {Math.round(maxDia)} mm
        </text>
        <text x={padding} y={height - 22} className="fill-zinc-500" fontSize={12}>
          Fins: {finCount} • {finType}
        </text>
      </g>
    </svg>
  );
}
