"""
Manages loading and saving custom API prompts.
"""
import json
import os
from pathlib import Path
from typing import Dict

DEFAULT_PROMPT_NAME = "Default Summary"
DEFAULT_PROMPT_TEXT = """Please summarize the following closed captioning (CC) and try to rate it across the following dimensions on a scale from 1-10:
- Political (1 being apolitical - 10 highly political)
- Controversial (1 being not controversial - 10 highly controversial)
- Subjective (1 being objective - 10 being subjective/opinionated)
For each of the ratings, provide a concise, one/two sentence explanation for the rating.
Furthermore, please describe the CC in a few keywords (e.g. educational, entertainment, computer science).

Please apply the following format:
Video url: {video_url}
Keywords: <KEYWORDS>
Political rating: <POLITICAL RATING> - <EXPLANATION>
Controversial rating: <CONTROVERSIAL RATING> - <EXPLANATION>
Subjective rating: <SUBJECTIVE RATING> - <EXPLANATION>

Summary: <SUMMARY>

This is the CC of the video:
{cc_text}
"""

class PromptManager:
    """
    Manages loading and saving prompts to a JSON file.
    """
    DEFAULT_PROMPT_NAME = "Default Summary"
    
    def __init__(self, app_name: str = "youtube_downloader"):
        self.app_name = app_name
        self.config_path = self._get_config_path()
        self.prompts = self.load_prompts()

    def _get_config_path(self) -> Path:
        """Gets the platform-specific path for app config."""
        if os.name == 'nt':
            path = Path(os.getenv('APPDATA', Path.home())) / self.app_name
        else:
            path = Path.home() / '.config' / self.app_name
        path.mkdir(parents=True, exist_ok=True)
        return path / 'prompts.json'

    def load_prompts(self) -> Dict[str, {Dict[str, str]}]:
        """Loads prompts from the JSON file."""
        defaults = {DEFAULT_PROMPT_NAME: {"model": "gemini-1.5-flash-latest","text": DEFAULT_PROMPT_TEXT}}
        if not self.config_path.exists():
            self.prompts = defaults
            self.save_prompts()
            return defaults
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                prompts = json.load(f)
            if not prompts: return defaults
            return prompts
        except (json.JSONDecodeError, IOError):
            return defaults

    def save_prompts(self):
        """Saves the current prompts to the JSON file."""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.prompts, f, indent=4)

    def add_prompt(self, name: str, text: str, model: str):
        """Adds a new prompt and saves the file."""
        self.prompts[name] = {"model": model, "text": text}
        self.save_prompts()
        
    def delete_prompt(self, name: str):
        if name == self.DEFAULT_PROMPT_NAME: return
        
        self.prompts.pop(name)
        self.save_prompts()

    def get_prompts(self) -> Dict[str, str]:
        """Returns all loaded prompts."""
        return self.prompts

    def get_prompt(self, name: str) -> str:
        """Returns a specific prompt by name."""
        return self.prompts.get(name)