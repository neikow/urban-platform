// Loaded on demand by association-select.ts: Leaflet stays out of the form pages
// until the map is opened. Styles: dist/map.css, listed in the widget media.
import L from "leaflet";

import { addBoundary, createMap, type MapConfig } from "./map";

export interface AssociationShape {
  id: number;
  name: string;
  area: GeoJSON.Polygon | GeoJSON.MultiPolygon | null;
  seat: GeoJSON.Point | null;
}

/** [lon, lat], as GeoJSON writes it. */
export type LonLat = [number, number];

const SELECTED = "map-ciq--selected";

/**
 * The associations on the basemap: their area, when drawn, and their seat. A tap
 * on either picks the association; the picked one is highlighted.
 */
export class AssociationMap {
  private readonly map: L.Map;
  private readonly groups = new Map<string, L.FeatureGroup>();
  private home: L.Layer | null = null;

  constructor(element: HTMLElement, config: MapConfig, shapes: AssociationShape[], onPick: (id: string) => void) {
    // A dialog, not a page section: the wheel can zoom without hijacking the scroll.
    this.map = createMap(element, config, { scrollWheelZoom: true });

    for (const shape of shapes) {
      const id = String(shape.id);
      const group = L.featureGroup();
      if (shape.area) L.geoJSON(shape.area, { style: { className: "map-ciq" } }).addTo(group);
      if (shape.seat) {
        const [lon = 0, lat = 0] = shape.seat.coordinates;
        L.circleMarker([lat, lon], { radius: 7, className: "map-ciq-seat" }).addTo(group);
      }
      if (!group.getLayers().length) continue;
      group
        .bindTooltip(shape.name, { className: "map-tooltip", direction: "top", sticky: true })
        .on("click", () => onPick(id))
        .addTo(this.map);
      this.groups.set(id, group);
    }

    const all = L.featureGroup([...this.groups.values()]);
    if (all.getBounds().isValid()) {
      this.map.fitBounds(all.getBounds(), { padding: [16, 16], animate: false });
    } else {
      void addBoundary(this.map, config.boundaryUrl).then((boundary) => {
        if (boundary) this.map.fitBounds(boundary.mainland, { padding: [16, 16], animate: false });
      });
    }
  }

  /** Highlight the association; with `reveal`, also bring it into view. */
  select(id: string, reveal: boolean): void {
    for (const [key, group] of this.groups) {
      const selected = key === id;
      group.eachLayer((layer) => {
        const paths = layer instanceof L.GeoJSON ? layer.getLayers() : [layer];
        for (const path of paths) (path as L.Path).getElement()?.classList.toggle(SELECTED, selected);
      });
      if (selected) group.bringToFront();
    }
    const group = this.groups.get(id);
    if (reveal && group) this.map.flyToBounds(group.getBounds(), { padding: [32, 32], maxZoom: 16, duration: 0.4 });
  }

  /** Mark the address the associations are ranked from. */
  setHome(point: LonLat | null, label: string): void {
    this.home?.remove();
    this.home = null;
    if (!point) return;
    const [lon, lat] = point;
    this.home = L.circleMarker([lat, lon], { radius: 6, className: "map-home", interactive: false })
      .bindTooltip(label, { permanent: true, direction: "top", className: "map-tooltip" })
      .addTo(this.map);
  }

  showHome(): void {
    const home = this.home as L.CircleMarker | null;
    if (home) this.map.setView(home.getLatLng(), Math.max(this.map.getZoom(), 15), { animate: false });
  }

  /** Leaflet measures its container once; the dialog may have resized since. */
  refresh(): void {
    this.map.invalidateSize();
  }
}
