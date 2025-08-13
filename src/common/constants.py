"""
Module with constants. In some cases, constants are defined locally, typically if it has a niche use case.


"""
import datetime
import os
from pathlib import Path

TZ_CET: datetime.timezone = datetime.timezone(datetime.timedelta(hours=1), name="CET")
"""Central European Timezone"""


URL_PREFIXES = "http://", "https://"
"""Various prefixes that indicate a string is a URL"""


YOUTUBE_SQLITE_TABLE = "youtube"
"""Name of the SQLite table associated with YouTube data"""


MONTHS_NL = "jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"
"""Abbreviated months in dutch"""


AUDIO_EXTENSIONS = "mp3", "wav", "flac", "aac", "ogg", "wma", "alac", "m4a", "aiff", "opus"
"""Frequently used audio file extensions"""


VIDEO_EXTENSIONS = "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "mpeg", "mpg", "3gp"
"""Frequently used video file extensions"""


INFO_JSON_EXTENSIONS = "json",
"""info json file extension"""


METADATA_FILE_LIFESPAN = 2_592_000
"""30 day metadata file lifespan in seconds. If the metadata file is older than this, it is to be downloaded again"""


root: Path = Path(os.getenv('APPDATA', Path.home())) / "youtube_summarizer"
"""Root folder for the data of the project."""

if os.name == 'nt':  # Windows
    pass
else:  # Linux, macOS, etc.
    root = Path.home() / '.config' / "youtube_summarizer"

path_cookies_downloaded: str = os.path.join(Path.home() / 'Downloads' / "cookies_downloaded.txt")
"""Default folder for downloaded cookies from a browser."""