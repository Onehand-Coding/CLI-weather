import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="cli-weather-tests-"))
os.environ.setdefault("CLI_WEATHER_CONFIG_DIR", str(_TMP / "config"))
os.environ.setdefault("CLI_WEATHER_CACHE_DIR", str(_TMP / "cache"))
os.environ.setdefault("CLI_WEATHER_LOG_DIR", str(_TMP / "logs"))
os.environ.setdefault("CLI_WEATHER_DATA_DIR", str(_TMP / "data"))
os.environ["OWM_API_KEY"] = ""
