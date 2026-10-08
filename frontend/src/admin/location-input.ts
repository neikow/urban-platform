import "@geoman-io/leaflet-geoman-free";
import "@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css";
import L from "leaflet";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

import { attachAddressAutocomplete } from "../lib/address-autocomplete";
import { addBoundary, createMap, fitTo, type MapConfig } from "../lib/map";

// Leaflet styles come from dist/map.css, listed in the widget media.

import "./location-input.css";

// Geoman draws L.Marker instances: point Leaflet at the bundled icon images.
delete (L.Icon.Default.prototype as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow });

type Shape = L.Marker | L.Polygon;

interface InputConfig extends MapConfig {
  /** Whether a marker may be placed; otherwise only areas are drawn. */
  markers: boolean;
  searchUrl: string;
}

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

    const config = JSON.parse(this.dataset.config ?? "{}") as InputConfig;
    const map = createMap(container, config, { scrollWheelZoom: true });
    this.map = map;

    map.pm.setLang("fr");
    // One shape per field: leave drawing mode after each shape.
    map.pm.setGlobalOptions({ continueDrawing: false });
    map.pm.addControls({
      position: "topleft",
      drawMarker: config.markers,
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

    map.on("pm:create", ({ layer }) => this.replace(layer as Shape));
    map.on("pm:remove", () => {
      this.shape = null;
      this.save();
    });

    const reference = this.addReference(map);
    const searchInput = this.querySelector<HTMLInputElement>("[data-search] input");
    if (searchInput) {
      attachAddressAutocomplete(searchInput, config.searchUrl, ({ lat, lon }) => {
        const latlng = L.latLng(lat, lon);
        // An address is a spot: it becomes the location unless an area is drawn.
        if (config.markers && !(this.shape instanceof L.Polygon)) this.replace(L.marker(latlng).addTo(map));
        map.setView(latlng, Math.max(map.getZoom(), 17));
      });
    }

    const existing = this.read();
    if (existing) {
      const layer = L.geoJSON(existing).addTo(map);
      const [shape] = layer.getLayers() as Shape[];
      if (shape) this.track(shape);
      fitTo(map, layer, 17);
    } else if (reference?.getBounds().isValid()) {
      fitTo(map, reference);
      void addBoundary(map, config.boundaryUrl);
    } else {
      void addBoundary(map, config.boundaryUrl).then((boundary) => {
        if (boundary) map.fitBounds(boundary.mainland, { padding: [24, 24] });
      });
    }
  }

  /** Shapes drawn for context (e.g. the other associations' areas): read-only, but snapped to. */
  private addReference(map: L.Map): L.GeoJSON | null {
    if (!this.dataset.reference) return null;
    const data = JSON.parse(this.dataset.reference) as GeoJSON.FeatureCollection;
    return L.geoJSON(data, {
      pmIgnore: true,
      snapIgnore: false,
      style: { className: "map-reference" },
      onEachFeature: (feature, layer) => {
        const name = (feature.properties as { name?: string } | null)?.name;
        if (name) layer.bindTooltip(name, { sticky: true });
      },
    } as L.GeoJSONOptions).addTo(map);
  }

  private replace(shape: Shape): void {
    // One shape per field: a new one replaces the previous one.
    this.shape?.remove();
    this.track(shape);
    this.save();
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
