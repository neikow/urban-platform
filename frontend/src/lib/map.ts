// Styles: the "map" CSS entry (styles/map.css), linked by templates that show a map.
import L from "leaflet";
import { leafletLayer } from "protomaps-leaflet";

export interface MapConfig {
  boundaryUrl: string;
  center: [number, number];
  zoom: number;
  /** Self-hosted PMTiles archive covering `maxBounds` only. */
  tilesUrl: string;
  tilesMaxZoom: number;
  /** [[south, west], [north, east]]: the maps cannot leave the tiled area. */
  maxBounds: [[number, number], [number, number]];
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

const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>, ' +
  '<a href="https://protomaps.com">Protomaps</a>';

/**
 * A Leaflet map on the self-hosted basemap, locked to the tiled area: it can
 * neither be panned out of it nor zoomed out past the level where it fills
 * the container. Scroll-wheel zoom is off so the page keeps scrolling.
 */
export function createMap(element: HTMLElement, config: MapConfig, options: L.MapOptions = {}): L.Map {
  const maxBounds = L.latLngBounds(config.maxBounds);
  const map = L.map(element, {
    center: config.center,
    zoom: config.zoom,
    maxZoom: 19,
    maxBounds,
    maxBoundsViscosity: 1,
    scrollWheelZoom: false,
    ...options,
  });
  leafletLayer({
    url: config.tilesUrl,
    maxDataZoom: config.tilesMaxZoom,
    flavor: "light",
    lang: "fr",
    attribution: ATTRIBUTION,
  }).addTo(map);

  // Containers inside tabs or collapsed panels start with no size.
  new ResizeObserver(() => {
    map.invalidateSize();
    if (element.clientWidth && element.clientHeight) map.setMinZoom(map.getBoundsZoom(maxBounds, true));
  }).observe(element);
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
    // Context only: drawing tools (Geoman, in the admin) must not edit or delete
    // it, but new shapes may snap to it.
    const options = { interactive: false, pmIgnore: true, snapIgnore: false, style: { className: "map-boundary" } };
    const layer = L.geoJSON(data, options as L.GeoJSONOptions).addTo(map);

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
