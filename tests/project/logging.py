import logging
import traceback
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_PATH = str(Path(__file__).resolve().parent.parent)


class DotPathFormatter(logging.Formatter):
    def format(self, record):
        self._style._defaults = {"dotpath": self.get_dotpath(record)}
        return super().format(record)

    def get_dotpath(self, record: logging.LogRecord) -> str:
        """Try to fetch the full dot import path for the module the log happened at."""
        # For library logs
        split_path = record.pathname.split("site-packages")
        if len(split_path) > 1:
            return self.format_dotpath(split_path[-1][1:])

        # For our logs
        split_path = record.pathname.split(str(BASE_PATH))
        if len(split_path) > 1:
            return self.format_dotpath(split_path[-1][1:])

        # Fall back to the module name, which doesn't include the full path info
        return record.module

    @staticmethod
    def format_dotpath(path: str) -> str:
        return path.removesuffix(".py").replace("/", ".").replace("\\", ".")


class TracebackMiddleware:
    def resolve(self, next, root, info, **kwargs):
        try:
            return next(root, info, **kwargs)
        except Exception as err:
            logger.info(traceback.format_exc())
            return err
