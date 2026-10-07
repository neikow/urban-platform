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

  const meta = document.createElement("p");
  meta.className = "map-popup__meta";
  meta.textContent = project.category;
  if (project.isOpen) {
    const status = document.createElement("span");
    status.className = "map-popup__status";
    status.textContent = messages.msgOpen ?? "";
    meta.append(status);
  }

  const title = document.createElement("a");
  title.href = project.url;
  title.className = "map-popup__title";
  title.textContent = project.title;

  const description = document.createElement("p");
  description.className = "map-popup__description";
  description.textContent = project.description;

  const link = document.createElement("a");
  link.href = project.url;
  link.className = "map-popup__link";
  link.textContent = messages.msgSeeProject ?? "";

  root.append(meta, title);
  if (project.description) root.append(description);
  root.append(link);
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
      .bindPopup(() => popupContent(feature.properties, messages), { className: "map-popup-frame", maxWidth: 300 })
      .bindTooltip(feature.properties.title, { className: "map-tooltip", direction: "top" })
      .addTo(map);
  }

  void addBoundary(map, config.boundaryUrl).then((boundary) => {
    if (boundary) map.fitBounds(boundary.mainland, { padding: [16, 16] });
  });

  // Geolocation stays in the browser: the position is never sent to the server.
  const locate = document.getElementById("projects-map-locate");
  if (!locate || !("geolocation" in navigator)) return;
  locate.classList.remove("hidden");

  const status = document.createElement("p");
  status.setAttribute("role", "status");
  status.className = "text-sm text-error mt-2";
  element.after(status);

  let me: L.Layer | null = null;
  locate.addEventListener("click", () => {
    status.textContent = "";
    map.locate({ setView: true, maxZoom: 16 });
  });
  map.on("locationfound", (event: L.LocationEvent) => {
    me?.remove();
    me = L.circle(event.latlng, { radius: event.accuracy, className: "map-me" })
      .bindTooltip(messages.msgYouAreHere ?? "", { permanent: true, direction: "top" })
      .addTo(map);
  });
  map.on("locationerror", () => {
    status.textContent = messages.msgLocateError ?? "";
  });
});
