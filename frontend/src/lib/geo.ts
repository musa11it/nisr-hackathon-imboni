import type { FeatureCollection } from './types'

type Ring = number[][]

function signedArea(ring: Ring): number {
  let s = 0
  // Σ (x2 − x1)(y2 + y1) over edges (prev -> current): > 0 means clockwise in the lon/lat plane
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) s += (ring[i][0] - ring[j][0]) * (ring[i][1] + ring[j][1])
  return s
}

function orient(ring: Ring, clockwise: boolean): Ring {
  const cw = signedArea(ring) > 0
  return cw === clockwise ? ring : [...ring].reverse()
}

/** d3-geo expects exterior rings clockwise and holes counter-clockwise (opposite of RFC 7946). */
export function rewindForD3(fc: FeatureCollection): FeatureCollection {
  return {
    ...fc,
    features: fc.features.map((f) => {
      const g = f.geometry as any
      if (g.type === 'Polygon') {
        return { ...f, geometry: { ...g, coordinates: g.coordinates.map((r: Ring, i: number) => orient(r, i === 0)) } }
      }
      if (g.type === 'MultiPolygon') {
        return { ...f, geometry: { ...g, coordinates: g.coordinates.map((p: Ring[]) => p.map((r, i) => orient(r, i === 0))) } }
      }
      return f
    }),
  }
}
