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
    
    def create_temp_file(self, filename: str) -> Path:
        """Create a temporary file with the given name.
        
        Args:
            filename: Name for the temporary file
            
        Returns:
            Path to the created temporary file
        """
        path = self.temp_dir / filename
        path.touch()  # Create the file if it doesn't exist
        return path
    
    def cleanup(self, older_than_hours: Optional[int] = None) -> None:
        """Clean up temporary files.
        
        Args:
            older_than_hours: Only remove files older than this many hours
        """
        try:
            # First clean up regular files
            for path in self.temp_dir.iterdir():
                if path.name == "__pycache__":
                    continue  # Skip __pycache__ directory for now
                if older_than_hours:
                    # Only remove old files
                    age = datetime.now().timestamp() - path.stat().st_mtime
                    if age < older_than_hours * 3600:
                        continue
                try:
                    if path.is_file():
                        path.unlink()
                except (PermissionError, OSError) as e:
                    logger.warning(f"Could not remove file {path}: {e}")
            
            # Try to clean up __pycache__ directory if it exists
            pycache_dir = self.temp_dir / "__pycache__"
            if pycache_dir.exists():
                try:
                    # Try to remove individual files first
                    for cache_file in pycache_dir.iterdir():
                        try:
                            cache_file.unlink()
                        except (PermissionError, OSError) as e:
                            logger.warning(f"Could not remove cache file {cache_file}: {e}")
                    # Try to remove the empty directory
                    pycache_dir.rmdir()
                except (PermissionError, OSError) as e:
                    logger.warning(f"Could not fully clean __pycache__ directory: {e}")
                    
        except Exception as e:
            logger.warning("Error during cleanup: %s", e)
    
    def clear_all(self) -> None:
        """Remove all temporary files."""
        try:
            shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(parents=True)
            logger.info("Cleared all temporary files")
        except Exception as e:
            logger.warning("Error clearing temp files: %s", e)
