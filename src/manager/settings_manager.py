"""
Manages loading and saving application settings.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict

from src.common.constants import root


class SettingsManager:
    """
    Manages loading and saving GUI settings to a JSON file.

    Settings are stored in a platform-appropriate user configuration
    directory.

    Attributes
    ----------
    app_name : str
        The name of the application, used for the config folder.
    config_path : Path
        The full path to the settings.json file.
    settings : dict
        The currently loaded settings.
    """
    
    def __init__(self, app_name: str = "youtube_downloader"):
        """
        Initializes the SettingsManager.

        Parameters
        ----------
        app_name : str, optional
            The name of the application, by default "youtube_downloader".
        """
        self.app_name = app_name
        self.config_path = self._get_config_path()
        self.settings = self.load_settings()
    
    def _get_config_path(self) -> Path:
        """
        Gets the platform-specific path for the application's config file.

        Returns
        -------
        Path
            The path to the settings.json file.
        """
        path = root
        
        path.mkdir(parents=True, exist_ok=True)
        return path / 'settings.json'
    
    def load_settings(self) -> Dict[str, str]:
        """
        Loads settings from the JSON file.

        If the file doesn't exist or is invalid, returns default values.

        Returns
        -------
        Dict[str, str]
            A dictionary containing the application settings.
        """
        cfg_root = os.path.dirname(self._get_config_path())
        defaults = {'api_key': '', 'output_folder': os.path.join(cfg_root, "summaries"),
                    'cc_folder': os.path.join(cfg_root, "cc")}
        if not self.config_path.exists():
            self.make_dirs(defaults)
            return defaults
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                for key, value in defaults.items():
                    settings.setdefault(key, value)
                self.make_dirs(settings)
                return settings
        except (json.JSONDecodeError, IOError):
            return defaults
    
    def save_settings(self, new_settings: Dict[str, Any]):
        """
        Saves settings to the JSON file.

        Parameters
        ----------
        new_settings : Dict[str, Any]
            A dictionary with the settings to save.
        """
        self.settings.update(new_settings)
        self.make_dirs(new_settings)
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Gets a specific setting value.

        Parameters
        ----------
        key : str
            The key of the setting to retrieve.
        default : Any, optional
            The value to return if the key is not found, by default None.

        Returns
        -------
        Any
            The value of the setting, or the default.
        """
        return self.settings.get(key, default)
    
    @staticmethod
    def make_dirs(settings: Dict[str, Any]):
        output_folder = settings.get('output_folder')
        
        # Safeguard to prevent endless sequence of folders being created
        if not os.path.exists(os.path.dirname(output_folder)):
            raise FileNotFoundError("Root config directory does not exist. Please create it manually.")
        
        if output_folder and not os.path.exists(output_folder):
            os.mkdir(output_folder)
            
        cc_folder = settings.get('cc_folder')
        if cc_folder and not os.path.exists(cc_folder):
            os.mkdir(cc_folder)