"""python -m urban_agent: poll the control plane, apply, report, forever."""

import logging
import signal
import sys
import time
from types import FrameType

from . import VERSION
from .config import ConfigError, from_environment
from .control_plane import ControlPlane, ControlPlaneError
from .reconcile import Reconciler
from .update import HANDOVER_SECONDS, Updater

logger = logging.getLogger("urban_agent")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        config = from_environment()
    except ConfigError as error:
        logger.error("%s", error)
        return 2

    stopping = False

    def stop(signum: int, frame: FrameType | None) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    control_plane = ControlPlane(config)
    reconciler = Reconciler(config)
    updater = Updater(config)
    logger.info("Agent %s, control plane %s", VERSION, config.control_plane_url)
    while not stopping:
        wait = config.poll_seconds
        try:
            desired = control_plane.desired_state()
            report = reconciler.reconcile(desired)
            report["errors"] = [*report["errors"], *updater.errors]
            control_plane.report(report)
            # Between two polls, nothing under way: the helper may replace this container.
            if updater.start(desired.get("agent")):
                wait = HANDOVER_SECONDS
        except ControlPlaneError as error:
            # Websites keep running as they are; try again at the next poll.
            logger.warning("Control plane unreachable: %s", error)
        for _ in range(wait):
            if stopping:
                break
            time.sleep(1)
    logger.info("Stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
