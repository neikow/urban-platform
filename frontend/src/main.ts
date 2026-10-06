import { installBehaviors } from "./lib/behaviors";
import { onReady } from "./lib/dom";
import { installLightbox } from "./lib/lightbox";
import { installLoginModal } from "./lib/login-modal";

installBehaviors();
onReady(() => {
  installLightbox();
  installLoginModal();
});
