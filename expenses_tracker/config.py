import tomllib
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

root_proj = Path(__file__).parent.parent


class Config:
    _instance = None
    _config = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        toml_filepath = 'config.toml'
        if os.getenv('DEV'):
            logger.info("dev config")
            toml_filepath = 'config_dev.toml'
        config_path = root_proj / toml_filepath
        with open(config_path, 'rb') as f:
            self._config = tomllib.load(f)

    def __getitem__(self, key):
        return self._config[key]

    @property
    def data_folder(self) -> str:
        dl_dir = self._config['data_folder']
        if dl_dir.startswith('.'):
            dl_dir = str(root_proj / dl_dir)
        return dl_dir

    @property
    def max_credentials(self):
        return self._config['max_credentials']

    @property
    def gemini(self):
        return self._config['gemini']

    @property
    def app(self):
        return self._config['app']
