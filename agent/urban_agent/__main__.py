"""python -m urban_agent: poll the control plane, apply, report, forever."""

import logging
import signal
import sys
import time
from types import FrameType

from . import VERSION
from .config import ConfigError, from_environment
from .control_plane import ControlPlane, ControlPlaneError
from .journal import Journal
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
    journal = Journal(config.state_dir / "journal.json")
    reconciler = Reconciler(config, journal=journal)
    updater = Updater(config)
    logger.info("Agent %s, control plane %s", VERSION, config.control_plane_url)
    journal.record("info", f"Agent {VERSION} started.")
    unreachable_since = 0.0
    update_errors: list[str] = []
    while not stopping:
        wait = config.poll_seconds
        try:
            desired = control_plane.desired_state()
            if unreachable_since:
                minutes = (time.time() - unreachable_since) / 60
                journal.record("info", f"Control plane reachable again after {minutes:.0f} min.")
                unreachable_since = 0.0
            report = reconciler.reconcile(desired)
            report["errors"] = [*report["errors"], *updater.errors]
            journal.acknowledge(control_plane.report(report))
            # Between two polls, nothing under way: the helper may replace this container.
            if updater.start(desired.get("agent")):
                journal.record("info", f"Updating to {desired['agent'].get('version')}.")
                wait = HANDOVER_SECONDS
            for update_error in updater.errors:
                if update_error not in update_errors:
                    journal.record("error", update_error)
            update_errors = updater.errors or update_errors  # empty between two tries
        except ControlPlaneError as error:
            # Websites keep running as they are; try again at the next poll.
            if not unreachable_since:
                unreachable_since = time.time()
                journal.record("warning", f"Control plane unreachable: {error}")
            else:
                logger.warning("Control plane unreachable: %s", error)
        for _ in range(wait):
            if stopping:
                break
            time.sleep(1)
    logger.info("Stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
