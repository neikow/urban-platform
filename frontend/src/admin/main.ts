import { installBehaviors } from "../lib/behaviors";

// Keep Wagtail's admin in its light theme: the custom overrides assume it.
document.documentElement.setAttribute("data-theme", "light");
installBehaviors();
