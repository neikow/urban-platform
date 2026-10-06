import "@geoman-io/leaflet-geoman-free";
import "@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css";
import L from "leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

import { addBoundary, createMap, fitTo, type MapConfig } from "../lib/map";

// Leaflet styles come from dist/map.css, listed in the widget media.

import "./location-input.css";

// Geoman draws L.Marker instances: point Leaflet at the bundled icon images.
delete (L.Icon.Default.prototype as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow });

type Shape = L.Marker | L.Polygon;

/**
 * <geojson-map-input> wraps a hidden textarea holding a GeoJSON geometry and
 * lets editors place one marker or draw one polygon. As a custom element it
 * initialises itself whenever Wagtail inserts the field into the page.
 */
class GeoJSONMapInput extends HTMLElement {
  private map: L.Map | null = null;
  private shape: Shape | null = null;
  private textarea!: HTMLTextAreaElement;

  connectedCallback(): void {
    if (this.map) return;
    const textarea = this.querySelector("textarea");
    const container = this.querySelector<HTMLElement>("[data-map]");
    if (!textarea || !container) return;
    this.textarea = textarea;

    const config = JSON.parse(this.dataset.config ?? "{}") as MapConfig;
    const map = createMap(container, config, { scrollWheelZoom: true });
    this.map = map;

    map.pm.setLang("fr");
    // One location per project: leave drawing mode after each shape.
    map.pm.setGlobalOptions({ continueDrawing: false });
    map.pm.addControls({
      position: "topleft",
      drawMarker: true,
      drawPolygon: true,
      drawRectangle: true,
      drawPolyline: false,
      drawCircle: false,
      drawCircleMarker: false,
      drawText: false,
      cutPolygon: false,
      rotateMode: false,
      editMode: true,
      dragMode: true,
      removalMode: true,
    });

    map.on("pm:create", ({ layer }) => {
      // One location per project: a new shape replaces the previous one.
      this.shape?.remove();
      this.track(layer as Shape);
      this.save();
    });
    map.on("pm:remove", () => {
      this.shape = null;
      this.save();
    });

    const existing = this.read();
    if (existing) {
      const layer = L.geoJSON(existing).addTo(map);
      const [shape] = layer.getLayers() as Shape[];
      if (shape) this.track(shape);
      fitTo(map, layer, 17);
    } else {
      void addBoundary(map, config.boundaryUrl).then((boundary) => {
        if (boundary) map.fitBounds(boundary.mainland, { padding: [24, 24] });
      });
    }
  }

  private track(shape: Shape): void {
    this.shape = shape;
    shape.on("pm:edit pm:dragend", () => this.save());
  }

  private read(): GeoJSON.Geometry | null {
    try {
      return this.textarea.value ? (JSON.parse(this.textarea.value) as GeoJSON.Geometry) : null;
    } catch {
      return null;
    }
  }

  private save(): void {
    this.textarea.value = this.shape ? JSON.stringify(this.shape.toGeoJSON().geometry) : "";
    // Lets Wagtail notice unsaved changes.
    this.textarea.dispatchEvent(new Event("change", { bubbles: true }));
  }
}

if (!customElements.get("geojson-map-input")) {
  customElements.define("geojson-map-input", GeoJSONMapInput);
}
