import { onReady, readJsonScript } from "../lib/dom";
import { createMap, fitTo, type MapConfig, type ProjectFeature, projectLayer } from "../lib/map";

onReady(() => {
  const element = document.getElementById("project-location-map");
  if (!element) return;

  const { feature, ...config } = readJsonScript<MapConfig & { feature: ProjectFeature }>("project-location-data");
  const map = createMap(element, config, { zoomControl: true });
  const layer = projectLayer(feature, "map-project map-project--open").addTo(map);
  fitTo(map, layer);
});
