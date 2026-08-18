import logging
import time
from typing import Optional


class ProgressLogger:
    """Utility class to track and log the execution progress of batch tasks.

    Logs progress updates at INFO level including current step, total items,
    percentage completed, and elapsed execution time.
    """

    def __init__(
        self,
        task_name: str,
        total_steps: int,
        logger: Optional[logging.Logger] = None
    ) -> None:
        """Initialize the ProgressLogger.

        :param task_name: Human-readable name of the task being tracked.
        :param total_steps: Total number of iterations or items to process.
        :param logger: Logger instance to output messages. Defaults to root logger.
        """
        self.task_name: str = task_name
        self.total_steps: int = max(1, total_steps)
        self.current_step: int = 0
        self.logger: logging.Logger = logger or logging.getLogger(__name__)
        self.start_time: Optional[float] = None

    def start(self) -> None:
        """Start tracking and log the initial message.

        :return: None
        """
        self.start_time = time.time()
        self.current_step = 0
        self.logger.info(
            "[%s] Started: 0/%d items (0.0%%)",
            self.task_name,
            self.total_steps
        )

    def step(self, increment: int = 1, item_name: str = "") -> None:
        """Advance progress by a given number of steps and log the update.

        :param increment: Number of steps to increment by.
        :param item_name: Optional detail/label about the current item.
        :return: None
        """
        self.current_step = min(self.total_steps, self.current_step + increment)
        percentage: float = (self.current_step / self.total_steps) * 100.0

        detail: str = f" - Processing '{item_name}'" if item_name else ""
        self.logger.info(
            "[%s] Progress: %d/%d (%.1f%%)%s",
            self.task_name,
            self.current_step,
            self.total_steps,
            percentage,
            detail
        )

    def finish(self) -> None:
        """Finalize tracking and log the summary with elapsed time.

        :return: None
        """
        elapsed_seconds: float = (
            time.time() - self.start_time if self.start_time else 0.0
        )
        self.logger.info(
            "[%s] Finished: %d/%d items in %.2fs",
            self.task_name,
            self.current_step,
            self.total_steps,
            elapsed_seconds
        )

    def __enter__(self) -> "ProgressLogger":
        """Support context manager syntax for automated lifecycle management.

        :return: Current ProgressLogger instance.
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Ensure finish() is logged even if an error occurs.

        :param exc_type: Exception type if raised.
        :param exc_val: Exception instance.
        :param exc_tb: Traceback object.
        :return: None
        """
        self.finish()