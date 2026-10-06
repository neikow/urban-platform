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
  root.className = "space-y-1";

  const title = document.createElement("a");
  title.href = project.url;
  title.className = "font-semibold link link-primary block";
  title.textContent = project.title;

  const meta = document.createElement("p");
  meta.className = "text-xs opacity-70 !m-0";
  meta.textContent = [project.category, project.isOpen ? messages.msgOpen : ""].filter(Boolean).join(" · ");

  const description = document.createElement("p");
  description.className = "text-sm !m-0";
  description.textContent = project.description;

  const link = document.createElement("a");
  link.href = project.url;
  link.className = "text-sm link";
  link.textContent = messages.msgSeeProject ?? "";

  root.append(title, meta);
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
      .bindPopup(() => popupContent(feature.properties, messages))
      .bindTooltip(feature.properties.title)
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
