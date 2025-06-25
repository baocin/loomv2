"""Task scheduler for data collectors."""

import asyncio
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CollectorScheduler:
    """Scheduler for managing data collection tasks."""

    def __init__(self):
        self.collectors: dict[str, Any] = {}
        self.tasks: dict[str, asyncio.Task] = {}
        self._running = False

    def add_collector(self, name: str, collector: Any) -> None:
        """Add a collector to the scheduler."""
        if name in self.collectors:
            logger.warning("Collector already exists", collector=name)
            return

        self.collectors[name] = collector
        logger.info("Added collector to scheduler", collector=name)

    def remove_collector(self, name: str) -> None:
        """Remove a collector from the scheduler."""
        if name in self.collectors:
            del self.collectors[name]
            logger.info("Removed collector from scheduler", collector=name)

    async def start(self) -> None:
        """Start all scheduled collectors."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        logger.info("Starting collector scheduler")
        self._running = True

        # Start each collector
        for name, collector in self.collectors.items():
            task = asyncio.create_task(self._run_collector(name, collector))
            self.tasks[name] = task
            logger.info("Started collector task", collector=name)

    async def stop(self) -> None:
        """Stop all scheduled collectors."""
        if not self._running:
            return

        logger.info("Stopping collector scheduler")
        self._running = False

        # Cancel all tasks
        for name, task in self.tasks.items():
            task.cancel()
            logger.info("Cancelled collector task", collector=name)

        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)

        self.tasks.clear()
        logger.info("Scheduler stopped")

    async def _run_collector(self, name: str, collector: Any) -> None:
        """Run a single collector with its configured interval."""
        logger.info("Starting collector loop", collector=name)

        try:
            while self._running:
                try:
                    # Collect data
                    await collector.collect()

                    # Wait for the configured interval
                    await asyncio.sleep(collector.interval)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Error in collector", collector=name, error=str(e))
                    # Brief pause before retrying
                    await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info("Collector cancelled", collector=name)
        except Exception as e:
            logger.error("Collector failed", collector=name, error=str(e))
        finally:
            logger.info("Collector loop ended", collector=name)

    async def get_status(self) -> dict[str, Any]:
        """Get scheduler status."""
        task_status = {}
        for name, task in self.tasks.items():
            task_status[name] = {
                "running": not task.done(),
                "cancelled": task.cancelled(),
                "exception": (
                    str(task.exception()) if task.done() and task.exception() else None
                ),
            }

        return {
            "running": self._running,
            "collectors": list(self.collectors.keys()),
            "tasks": task_status,
        }

    async def restart_collector(self, name: str) -> bool:
        """Restart a specific collector."""
        if name not in self.collectors:
            logger.error("Collector not found", collector=name)
            return False

        # Cancel existing task
        if name in self.tasks:
            self.tasks[name].cancel()
            try:
                await self.tasks[name]
            except asyncio.CancelledError:
                pass

        # Start new task
        collector = self.collectors[name]
        task = asyncio.create_task(self._run_collector(name, collector))
        self.tasks[name] = task

        logger.info("Restarted collector", collector=name)
        return True

    def pause_collector(self, name: str) -> bool:
        """Pause a specific collector."""
        if name not in self.tasks:
            return False

        # For now, just cancel the task
        # In a more sophisticated implementation, you might pause/resume
        self.tasks[name].cancel()
        logger.info("Paused collector", collector=name)
        return True

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
