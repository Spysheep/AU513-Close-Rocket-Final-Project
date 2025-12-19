// Fin geometry helpers for 2D profiles
// All angles are in degrees. Coordinates are in arbitrary units (same units as inputs).
// Coordinate convention for a single fin (local space):
// - Origin (0,0) is the inner/bottom-root corner (touching the fuselage)
// - +x goes outward from the fuselage; +y goes upward toward the tip
// - Bottom root chord lies along y=0 from x=0 to x=root_chord
// - Return order for polygon vertices is [bottom-inner, bottom-outer, top-outer, top-inner]

export type Point = [number, number];

export const deg2rad = (deg: number) => (deg * Math.PI) / 180;

// 1) Trapezoidal fin
// Inputs:
//  - height: vertical span of the fin
//  - length: top edge length (tip chord)
//  - root_chord: bottom edge length along the fuselage
//  - sweep_angle_deg: angle between bottom root (y=0) and the leading edge (p0->p3)
// Geometry:
//  The leading edge is displaced by dx = tan(angle)*height.
//  Top edge remains horizontal and has the given length.
//  Vertices (local):
//   p0 = (0, 0)
//   p1 = (root_chord, 0)
//   p2 = (dx + length, height)
//   p3 = (dx, height)
export function trapezoidalFinVertices(
  height: number,
  length: number,
  root_chord: number,
  sweep_angle_deg: number
): Point[] {
  const dx = Math.tan(deg2rad(sweep_angle_deg)) * height;
  const p0: Point = [0, 0];
  const p1: Point = [root_chord, 0];
  const p2: Point = [dx + length, height];
  const p3: Point = [dx, height];
  return [p0, p1, p2, p3];
}

// 2) Elliptical fin (half ellipse with flat side at the bottom)
// Inputs:
//  - height: vertical semi-axis (Ry)
//  - root_chord: full bottom width (2*Rx) at y=0
//  - segments: number of points to approximate the curved edge
// Geometry:
//  We build the upper half of an ellipse centered horizontally on the base:
//   x in [-Rx, Rx], y = Ry * sqrt(1 - (x^2/Rx^2))
//  Output includes the bottom endpoints to form a closed polygon: [(-Rx,0), arc..., (Rx,0)].
export function ellipticalFinPoints(
  height: number,
  root_chord: number,
  segments: number = 48
): Point[] {
  const Rx = root_chord / 2;
  const Ry = height;
  const pts: Point[] = [];
  // Start at left bottom
  pts.push([-Rx, 0]);
  for (let i = 0; i <= segments; i++) {
    const t = i / segments; // 0..1 across width
    const x = -Rx + t * (2 * Rx);
    const rad = 1 - (x * x) / (Rx * Rx);
    const y = rad > 0 ? Ry * Math.sqrt(rad) : 0;
    pts.push([x, y]);
  }
  // End at right bottom
  pts.push([Rx, 0]);
  return pts;
}

// Convenience: convert a list of points to an SVG closed path string
export function svgPathFromPoints(points: Point[]): string {
  if (!points.length) return "";
  const [x0, y0] = points[0];
  const cmds = [`M ${x0} ${y0}`];
  for (let i = 1; i < points.length; i++) {
    const [x, y] = points[i];
    cmds.push(`L ${x} ${y}`);
  }
  cmds.push("Z");
  return cmds.join(" ");
}

// Optional: directly build an SVG path for the elliptical fin
export function ellipticalFinPath(height: number, root_chord: number, segments: number = 48): string {
  return svgPathFromPoints(ellipticalFinPoints(height, root_chord, segments));
}

// 3) Diamond fin (symmetric trapezoid)
// Inputs:
//  - height
//  - length: top chord length (tip chord)
//  - root_chord: bottom chord length
//  - sweep_angle_deg: identical leading/trailing edge angle vs the bottom
// Geometry and over-constraint handling:
//  If both length and sweep_angle are provided, the geometry may be over-constrained since
//  dx = tan(angle)*height and length' = root_chord - 2*dx. We prefer to honor `length` when
//  inconsistent by recomputing the effective angle from length.
export function diamondFinVertices(
  height: number,
  length: number,
  root_chord: number,
  sweep_angle_deg: number
): Point[] {
  // Compute dx from provided length; fallback to angle if length invalid
  let dx = (root_chord - length) / 2;
  if (!isFinite(dx) || dx < 0) {
    dx = Math.tan(deg2rad(sweep_angle_deg)) * height;
  }
  // Recompute top chord according to dx for internal consistency
  const tipChord = Math.max(0, root_chord - 2 * dx);

  const p0: Point = [0, 0];
  const p1: Point = [root_chord, 0];
  const p2: Point = [dx + tipChord, height];
  const p3: Point = [dx, height];
  return [p0, p1, p2, p3];
}
