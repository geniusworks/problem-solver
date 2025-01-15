"""Temporary file management."""

import atexit
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class TempFileManager:
    """Manages temporary files for solution development and testing."""
    
    def __init__(self, base_dir: Optional[Path] = None) -> None:
        """Initialize the temp file manager.
        
        Args:
            base_dir: Base directory for temp files. If None, uses system temp dir.
        """
        if base_dir is None:
            base_dir = Path.home() / ".problem-solver" / "temp"
        
        self.temp_dir = base_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Register cleanup on exit
        atexit.register(self.cleanup_old_files)
    
    def get_temp_file(self, prefix: str, suffix: str = ".py") -> Path:
        """Get a path for a temporary file.
        
        Args:
            prefix: Prefix for the filename (e.g. year_day)
            suffix: File extension
            
        Returns:
            Path to use for the temporary file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.temp_dir / f"{prefix}_{timestamp}{suffix}"
    
    def cleanup_old_files(self, max_age: timedelta = timedelta(days=1)) -> None:
        """Remove old temporary files.
        
        Args:
            max_age: Maximum age for temp files
        """
        now = datetime.now()
        try:
            for path in self.temp_dir.iterdir():
                if path.is_file():
                    mtime = datetime.fromtimestamp(path.stat().st_mtime)
                    if now - mtime > max_age:
                        path.unlink()
                        logger.debug("Removed old temp file: %s", path)
        except Exception as e:
            logger.warning("Error cleaning up temp files: %s", e)
    
    def clear_all(self) -> None:
        """Remove all temporary files."""
        try:
            shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(parents=True)
            logger.info("Cleared all temporary files")
        except Exception as e:
            logger.warning("Error clearing temp files: %s", e)
