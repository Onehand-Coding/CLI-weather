"""Cache service for managing weather data caching."""

import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, Optional, Union
from datetime import datetime, timedelta

from .exceptions import CacheError

logger = logging.getLogger(__name__)


class CacheService:
    """Handles caching of weather data with expiry logic."""
    
    def __init__(self, cache_dir: Path, expiry: timedelta):
        """Initialize cache service.
        
        Args:
            cache_dir: Directory to store cache files
            expiry: How long cached data remains valid
        """
        self.cache_dir = cache_dir
        self.expiry = expiry
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(exist_ok=True, parents=True)
    
    def generate_key(self, *args) -> str:
        """Generate a unique MD5 hash key for cache entries."""
        key_string = "_".join(map(str, args))
        key = hashlib.md5(key_string.encode()).hexdigest()
        logger.debug(f"Generated cache key: {key}")
        return key
    
    def save(self, key: str, data: Dict) -> None:
        """Save data to cache with timestamp."""
        try:
            cache_file = self.cache_dir / key
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            
            with cache_file.open("w") as file:
                json.dump(cache_data, file)
            
            logger.debug(f"Cache data saved for key: {key}")
            
        except Exception as e:
            logger.error(f"Failed to save cache data: {e}")
            raise CacheError(f"Failed to save cache data: {e}") from e
    
    def load(self, key: str) -> Optional[Dict]:
        """Load data from cache if it exists and is not expired."""
        try:
            cache_file = self.cache_dir / key
            
            if not cache_file.exists():
                logger.debug(f"Cache file not found for key: {key}")
                return None
            
            with cache_file.open("r") as file:
                cached = json.load(file)
            
            # Check if cache is expired
            timestamp = datetime.fromisoformat(cached["timestamp"])
            if datetime.now() - timestamp >= self.expiry:
                # Cache expired, delete the file
                cache_file.unlink()
                logger.debug(f"Cache expired and deleted for key: {key}")
                return None
            
            logger.debug(f"Cache hit for key: {key}")
            return cached["data"]
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid cache file format for key {key}: {e}")
            # Remove corrupted cache file
            try:
                cache_file.unlink()
            except FileNotFoundError:
                pass
            return None
            
        except Exception as e:
            logger.error(f"Error loading cache data for key {key}: {e}")
            return None
    
    def clear(self) -> int:
        """Clear all cached files.
        
        Returns:
            Number of files cleared
        """
        try:
            files_cleared = 0
            for cache_file in self.cache_dir.iterdir():
                if cache_file.is_file():
                    cache_file.unlink()
                    files_cleared += 1
            
            logger.debug(f"Cache cleared: {files_cleared} files deleted")
            return files_cleared
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            raise CacheError(f"Failed to clear cache: {e}") from e
    
    def clear_expired(self) -> int:
        """Clear only expired cache files.
        
        Returns:
            Number of expired files cleared
        """
        try:
            files_cleared = 0
            for cache_file in self.cache_dir.iterdir():
                if not cache_file.is_file():
                    continue
                    
                try:
                    with cache_file.open("r") as file:
                        cached = json.load(file)
                    
                    timestamp = datetime.fromisoformat(cached["timestamp"])
                    if datetime.now() - timestamp >= self.expiry:
                        cache_file.unlink()
                        files_cleared += 1
                        
                except (json.JSONDecodeError, KeyError, ValueError):
                    # Remove corrupted cache files
                    cache_file.unlink()
                    files_cleared += 1
            
            logger.debug(f"Expired cache cleared: {files_cleared} files deleted")
            return files_cleared
            
        except Exception as e:
            logger.error(f"Error clearing expired cache: {e}")
            raise CacheError(f"Failed to clear expired cache: {e}") from e
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            total_files = 0
            expired_files = 0
            valid_files = 0
            
            for cache_file in self.cache_dir.iterdir():
                if not cache_file.is_file():
                    continue
                    
                total_files += 1
                
                try:
                    with cache_file.open("r") as file:
                        cached = json.load(file)
                    
                    timestamp = datetime.fromisoformat(cached["timestamp"])
                    if datetime.now() - timestamp >= self.expiry:
                        expired_files += 1
                    else:
                        valid_files += 1
                        
                except (json.JSONDecodeError, KeyError, ValueError):
                    expired_files += 1
            
            return {
                "total_files": total_files,
                "valid_files": valid_files,
                "expired_files": expired_files
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"total_files": 0, "valid_files": 0, "expired_files": 0}
