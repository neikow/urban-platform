// Styles: the "map" CSS entry (styles/map.css), linked by templates that show a map.
import L from "leaflet";

export interface MapConfig {
  boundaryUrl: string;
  center: [number, number];
  zoom: number;
}

export interface ProjectProperties {
  title: string;
  url: string;
  category: string;
  description: string;
  participation: "NONE" | "VOTING" | "IDEAS";
  isOpen: boolean;
}

export type ProjectFeature = GeoJSON.Feature<GeoJSON.Point | GeoJSON.Polygon, ProjectProperties>;

const OSM_TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

/** A Leaflet map on OpenStreetMap tiles. Scroll-wheel zoom is off so the page keeps scrolling. */
export function createMap(element: HTMLElement, config: MapConfig, options: L.MapOptions = {}): L.Map {
  const map = L.map(element, {
    center: config.center,
    zoom: config.zoom,
    scrollWheelZoom: false,
    ...options,
  });
  L.tileLayer(OSM_TILES, {
    maxZoom: 19,
    attribution: OSM_ATTRIBUTION,
    // The OSM tile policy requires a Referer and blocks requests without one
    // ("403 Access blocked"). Pages use Django's "same-origin" Referrer-Policy,
    // which drops it on cross-origin requests: send the origin for tiles.
    referrerPolicy: "strict-origin-when-cross-origin",
  }).addTo(map);

  // Containers inside tabs or collapsed panels start with no size.
  new ResizeObserver(() => map.invalidateSize()).observe(element);
  return map;
}

export interface Boundary {
  layer: L.GeoJSON;
  /** Bounds of the largest polygon: the 7e also covers the Frioul islands, mostly sea. */
  mainland: L.LatLngBounds;
}

/** Planar area of a ring (shoelace formula), enough to compare polygons of one city. */
function ringArea(ring: GeoJSON.Position[]): number {
  let sum = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    const [x1 = 0, y1 = 0] = ring[i] ?? [];
    const [x2 = 0, y2 = 0] = ring[i + 1] ?? [];
    sum += x1 * y2 - x2 * y1;
  }
  return Math.abs(sum) / 2;
}

/** Draw the local area outline and return it with the bounds to fit the view to. */
export async function addBoundary(map: L.Map, url: string): Promise<Boundary | null> {
  try {
    const response = await fetch(url);
    const data = (await response.json()) as GeoJSON.GeoJsonObject;
    const layer = L.geoJSON(data, { interactive: false, style: { className: "map-boundary" } }).addTo(map);

    let mainland = layer.getBounds();
    const multi = (data as GeoJSON.Feature).geometry;
    if (multi?.type === "MultiPolygon") {
      const largest = multi.coordinates.reduce((best, polygon) =>
        ringArea(polygon[0] ?? []) > ringArea(best[0] ?? []) ? polygon : best,
      );
      mainland = L.polygon(L.GeoJSON.coordsToLatLngs(largest, 1) as L.LatLng[][]).getBounds();
    }
    return { layer, mainland };
  } catch (error) {
    console.error("Could not load the area boundary", error);
    return null;
  }
}

/** Points become circle markers (no image assets) and areas polygons, styled by class. */
export function projectLayer(feature: ProjectFeature | GeoJSON.Geometry, className: string): L.GeoJSON {
  return L.geoJSON(feature, {
    pointToLayer: (_point, latlng) => L.circleMarker(latlng, { radius: 9, className }),
    style: { className },
  });
}

export function fitTo(map: L.Map, layer: L.GeoJSON, maxZoom = 16): void {
  const bounds = layer.getBounds();
  if (bounds.isValid()) map.fitBounds(bounds, { padding: [24, 24], maxZoom });
}
