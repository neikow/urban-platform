import { installBehaviors } from "./lib/behaviors";
import { onReady } from "./lib/dom";
import { installInstantResults } from "./lib/instant-results";
import { installLightbox } from "./lib/lightbox";
import { installLoginModal } from "./lib/login-modal";

installBehaviors();
onReady(() => {
  installLightbox();
  installLoginModal();
  installInstantResults();
});
