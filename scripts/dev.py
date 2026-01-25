import argparse
import atexit
import os
import signal
import subprocess  # nosec
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCKER_COMPOSE_FILE = PROJECT_ROOT / "docker-compose.dev.yml"


@dataclass
class Service:
    name: str
    start: Callable[[], subprocess.Popen | None]
    stop: Callable[[], None] | None = None
    process: subprocess.Popen | None = None


def _stop_docker_compose() -> None:
    print("🐳 Stopping Docker Compose services...")
    try:
        subprocess.run(  # nosec
            ["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "down"],
            check=True,
            cwd=PROJECT_ROOT,
        )
        print("✅ Docker Compose services stopped")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Warning: Failed to stop Docker Compose: {e}")


def _wait_for_redis(timeout: int = 30) -> None:
    print("⏳ Waiting for Redis to be ready...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            result = subprocess.run(  # nosec
                [
                    "docker",
                    "compose",
                    "-f",
                    str(DOCKER_COMPOSE_FILE),
                    "exec",
                    "-T",
                    "cache",
                    "redis-cli",
                    "ping",
                ],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
            )
            if "PONG" in result.stdout:
                print("✅ Redis is ready")
                return
        except subprocess.CalledProcessError:
            pass
        time.sleep(1)

    print("⚠️ Warning: Redis health check timed out, continuing anyway...")


class DevServer:
    def __init__(self, use_docker: bool = True):
        self.use_docker = use_docker
        self.processes: list[subprocess.Popen] = []
        self.services: list[Service] = []
        self._setup_services()
        self._setup_signal_handlers()

    def _setup_services(self) -> None:
        if self.use_docker:
            self.services.append(
                Service(
                    name="Docker Compose",
                    start=self._start_docker_compose,
                    stop=_stop_docker_compose,
                )
            )

        self.services.append(
            Service(
                name="Tailwind CSS Watcher",
                start=self._start_tailwind_watcher,
            )
        )

        self.services.append(
            Service(
                name="Django Dev Server",
                start=self._start_django,
            )
        )

        self.services.append(
            Service(
                name="Celery Worker",
                start=self._start_celery_worker,
            )
        )

        # Future: Add Celery beat here
        # self.services.append(
        #     Service(
        #         name="Celery Beat",
        #         start=self._start_celery_beat,
        #     )
        # )

    def _setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        atexit.register(self.cleanup)

    def _handle_shutdown(self, signum: int, frame: FrameType | None) -> None:
        print("\n\n🛑 Shutting down services...")
        self.cleanup()
        sys.exit(0)

    def _start_tailwind_watcher(self) -> subprocess.Popen:
        print("🎨 Starting Tailwind CSS watcher...")
        process = subprocess.Popen(  # nosec
            ["npm", "run", "styles:watch"],
            cwd=PROJECT_ROOT,
        )
        self.processes.append(process)
        print("✅ Tailwind CSS watcher started")
        return process

    def _start_docker_compose(self) -> subprocess.Popen | None:
        print("🐳 Starting Docker Compose services...")
        try:
            subprocess.run(  # nosec
                ["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "up", "-d"],
                check=True,
                cwd=PROJECT_ROOT,
            )
            print("✅ Docker Compose services started")
            # Wait for services to be ready
            _wait_for_redis()
            return None
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to start Docker Compose: {e}")
            sys.exit(1)

    def _start_django(self) -> subprocess.Popen:
        print("🚀 Starting Django development server...")
        env = os.environ.copy()
        env["DJANGO_SETTINGS_MODULE"] = "urban_platform.settings.dev"

        process = subprocess.Popen(  # nosec
            ["uv", "run", "python", "manage.py", "runserver"],
            cwd=PROJECT_ROOT,
            env=env,
        )
        self.processes.append(process)
        print("✅ Django dev server started at http://localhost:8000")
        return process

    def _start_celery_worker(self) -> subprocess.Popen:
        print("🌿 Starting Celery worker...")
        env = os.environ.copy()
        env["DJANGO_SETTINGS_MODULE"] = "urban_platform.settings.dev"

        process = subprocess.Popen(  # nosec
            [
                "uv",
                "run",
                "celery",
                "-A",
                "urban_platform",
                "worker",
                "--loglevel=info",
            ],
            cwd=PROJECT_ROOT,
            env=env,
        )
        self.processes.append(process)
        print("✅ Celery worker started")
        return process

    def _start_celery_beat(self) -> subprocess.Popen:
        print("⏰ Starting Celery beat...")
        env = os.environ.copy()
        env["DJANGO_SETTINGS_MODULE"] = "urban_platform.settings.dev"

        process = subprocess.Popen(  # nosec
            [
                "uv",
                "run",
                "celery",
                "-A",
                "urban_platform",
                "beat",
                "--loglevel=info",
            ],
            cwd=PROJECT_ROOT,
            env=env,
        )
        self.processes.append(process)
        print("✅ Celery beat started")
        return process

    def start(self) -> None:
        print("=" * 50)
        print("🔧 Urban Platform Development Server")
        print("=" * 50)
        print()

        for service in self.services:
            service.process = service.start()

        print()
        print("=" * 50)
        print("✨ All services started! Press Ctrl+C to stop.")
        print("=" * 50)
        print()

        try:
            for process in self.processes:
                if process:
                    process.wait()
        except KeyboardInterrupt:
            pass

    def cleanup(self) -> None:
        for process in self.processes:
            if process and process.poll() is None:
                print(f"Terminating process {process.pid}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

        for service in self.services:
            if service.stop:
                service.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Urban Platform development services")
    parser.add_argument(
        "--no-docker",
        action="store_true",
        help="Skip starting Docker Compose (assumes services are already running)",
    )
    parser.add_argument(
        "--keep-docker",
        action="store_true",
        help="Keep Docker containers running after stopping the dev server",
    )

    args = parser.parse_args()

    server = DevServer(use_docker=not args.no_docker)

    if args.keep_docker:
        for service in server.services:
            if service.name == "Docker Compose":
                service.stop = None

    server.start()


if __name__ == "__main__":
    main()
