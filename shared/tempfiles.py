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
    
    def __init__(self, repo_root: Path) -> None:
        """Initialize the temporary file manager.

        Args:
            repo_root: Repository root directory path
        """
        self.temp_dir = repo_root / "tmp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
    
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
    
    def cleanup(self, older_than_hours: Optional[int] = None) -> None:
        """Clean up temporary files.
        
        Args:
            older_than_hours: Only remove files older than this many hours
        """
        try:
            for path in self.temp_dir.iterdir():
                if older_than_hours:
                    # Only remove old files
                    age = datetime.now().timestamp() - path.stat().st_mtime
                    if age < older_than_hours * 3600:
                        continue
                path.unlink()
            
            # Try to remove the directory and recreate it
            shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(parents=True)
        except PermissionError as e:
            raise PermissionError(f"Permission error cleaning up directory {self.temp_dir}: {str(e)}")
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
