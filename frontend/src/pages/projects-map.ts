import L from "leaflet";

import { onReady, readJsonScript } from "../lib/dom";
import {
  addBoundary,
  createMap,
  type MapConfig,
  type ProjectFeature,
  type ProjectProperties,
  projectLayer,
} from "../lib/map";

function popupContent(project: ProjectProperties, messages: DOMStringMap): HTMLElement {
  const root = document.createElement("div");
  root.className = "map-popup";

  // One truncated line: the full category is in the tooltip.
  const category = document.createElement("p");
  category.className = "map-popup__category";
  category.textContent = project.category;
  category.title = project.category;

  const title = document.createElement("a");
  title.href = project.url;
  title.className = "map-popup__title";
  title.textContent = project.title;

  const description = document.createElement("p");
  description.className = "map-popup__description";
  description.textContent = project.description;

  const footer = document.createElement("div");
  footer.className = "map-popup__footer";
  const link = document.createElement("a");
  link.href = project.url;
  link.className = "map-popup__link";
  link.textContent = messages.msgSeeProject ?? "";
  footer.append(link);
  if (project.isOpen) {
    const status = document.createElement("span");
    status.className = "map-popup__status";
    status.textContent = messages.msgOpen ?? "";
    footer.append(status);
  }

  if (project.category) root.append(category);
  root.append(title);
  if (project.description) root.append(description);
  root.append(footer);
  return root;
}

onReady(() => {
  const element = document.getElementById("projects-map");
  if (!element) return;

  const messages = element.dataset;
  const config = readJsonScript<MapConfig>("projects-map-config");
  const projects = readJsonScript<GeoJSON.FeatureCollection<ProjectFeature["geometry"], ProjectProperties>>(
    "projects-map-data",
  );

  const map = createMap(element, config);

  for (const feature of projects.features) {
    const className = feature.properties.isOpen ? "map-project map-project--open" : "map-project";
    projectLayer(feature as ProjectFeature, className)
      // A fixed minimum: Leaflet sizes the popup to its content, which the truncated category shrinks.
      .bindPopup(() => popupContent(feature.properties, messages), {
        className: "map-popup-frame",
        minWidth: 260,
        maxWidth: 300,
      })
      .bindTooltip(feature.properties.title, { className: "map-tooltip", direction: "top" })
      .addTo(map);
  }

  // The user's position, once shown: the boundary loading later must not move away from it.
  // Not animated either: it is the initial view, and Leaflet would finish the
  // animation over a position found meanwhile.
  let me: L.Layer | null = null;
  void addBoundary(map, config.boundaryUrl).then((boundary) => {
    if (boundary && !me) map.fitBounds(boundary.mainland, { padding: [16, 16], animate: false });
  });

  // Geolocation stays in the browser: the position is never sent to the server.
  const locate = document.getElementById("projects-map-locate");
  if (!locate || !("geolocation" in navigator)) return;
  locate.classList.remove("hidden");

  const status = document.createElement("p");
  status.setAttribute("role", "status");
  status.className = "text-sm mt-2";
  element.after(status);
  const showStatus = (message: string | undefined, isError: boolean) => {
    status.textContent = message ?? "";
    status.classList.toggle("text-error", isError);
    status.classList.toggle("text-base-content/70", !isError);
  };

  // There are no tiles outside the extract: say so instead of moving there.
  const tiledArea = L.latLngBounds(config.maxBounds);

  locate.addEventListener("click", () => {
    showStatus("", false);
    map.locate();
  });
  map.on("locationfound", (event: L.LocationEvent) => {
    me?.remove();
    me = null;
    if (!tiledArea.contains(event.latlng)) {
      showStatus(messages.msgOutsideArea, false);
      return;
    }
    map.setView(event.latlng, Math.min(map.getBoundsZoom(event.bounds), 16));
    me = L.circle(event.latlng, { radius: event.accuracy, className: "map-me", interactive: false })
      .bindTooltip(messages.msgYouAreHere ?? "", { permanent: true, direction: "top" })
      .addTo(map);
  });
  map.on("locationerror", () => {
    showStatus(messages.msgLocateError, true);
  });
});
