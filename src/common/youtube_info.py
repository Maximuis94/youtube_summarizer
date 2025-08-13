"""
Module that manages downloading and accessing info.json files. Additionally, it houses the YouTube class, which is
derived from the info.json file.
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from warnings import warn

import time
import yt_dlp

from src.common.constants import METADATA_FILE_LIFESPAN, root, path_cookies_downloaded
from src.common.util import extract_id, reformat_json

_root = os.path.join(root, "meta_data")
"""Folder in which all json info files are stored"""


if not os.path.exists(_root):
    os.makedirs(_root)

os.chdir(_root)


def generate_file_name(url: str, extension: str = ".info.json") -> str:
    """Generate a file name for the info json file"""
    return os.path.join(_root, extract_id(url) + extension)


def probe_url(url: str, add_cookies_file: bool = False, add_comments: bool = False, force_download: bool = None, **kwargs) -> Optional[str]:
    """
    Download the info json associated with the URL. Save the JSON at the designated folder, using the ID extracted from
    the URL as file name

    Parameters
    ----------
    url : str
        URL to the YouTube video.
    add_cookies_file : bool, False by default
        If True, add the cookies file to the command.
    add_comments : bool, optional, False by default
        If True, download the comments along with the video metadata
    force_download : bool, False by default
        If True, download the metadata even if the file already exists.
    
    Other Parameters
    ----------------
    languages : Optional[str, Sequence[str]], optional, ('nl', 'en') by default
        The CC url languages that are to be included.
    force_new_probe : bool, False by default
        Probe the URL again, even if such a json file already exists.

    Returns
    -------
    Dict[str, any]
        Parsed json file
    """
    out_file = generate_file_name(url, extension=".info.json")
    
    if os.path.exists(out_file) and (force_download or
            not force_download and time.time() - os.path.getmtime(out_file) > METADATA_FILE_LIFESPAN):
        os.remove(out_file)
    
    if os.path.exists(out_file) and not force_download:
        return out_file
    
    ydl_kwargs = {
        'no_mtime': True,
        'buffersize': '128k',
        'ratelimit': '2M',
        'windowsfilenames': True,
        'writeinfojson': True,
        'skip_download': True,
        'outtmpl': '%(id)s', # Example output template
    }
    
    if add_cookies_file :
        ydl_kwargs['cookies'] = path_cookies_downloaded
    
    if add_comments:
        ydl_kwargs['write_comments'] = True
    
    yt_dlp.YoutubeDL(ydl_kwargs).download([url])
    
    # Include any explicitly defined languages other than nl and en
    caption_languages = ["en", "nl"]
    caption_languages.extend(frozenset(kwargs.pop('languages', [])).difference(caption_languages))
    
    # Make the file easier to read and ditch some of the unused keys
    if kwargs.pop('reformat_json', True):
        try:
            reformat_json(out_file, preserve_captions=caption_languages)
        except FileNotFoundError:
            return None
    return out_file


def get_info_json(url: str) -> Dict[str, any]:
    """Load the *.info.json metadata file associated with `url` and return its contents as a dict."""
    file_name = generate_file_name(url)
    
    if not os.path.exists(file_name):
        file_name = probe_url(url)
    
    return json.load(open(file_name, 'r', encoding='utf-8'))


@dataclass(slots=True, frozen=True)
class Thumbnail:
    """Represents a single video thumbnail."""
    id: str
    url: str
    preference: int
    width: Optional[int] = None
    height: Optional[int] = None
    resolution: Optional[str] = None


@dataclass(slots=True, frozen=True)
class Caption:
    """Represents a single caption track."""
    url: str
    ext: str
    name: str
    impersonate: bool


@dataclass(slots=True, frozen=True)
class Format:
    """Represents a single media format (video or audio)."""
    format_id: Optional[str] = field(default=None)
    url: Optional[str] = field(default=None)
    ext: Optional[str] = field(default=None)
    resolution: Optional[str] = field(default=None)
    vcodec: Optional[str] = field(default=None)
    acodec: Optional[str] = field(default=None)
    fps: Optional[float] = field(default=None)
    filesize: Optional[int] = field(default=None)
    filesize_approx: Optional[int] = field(default=None)
    tbr: Optional[float] = field(default=None)
    width: Optional[int] = field(default=None)
    height: Optional[int] = field(default=None)
    format_note: Optional[str] = field(default=None)
    
    def __post_init__(self):
        if self.filesize_approx and isinstance(self.filesize_approx, str):
            object.__setattr__(self, "filesize_approx", int(self.filesize_approx))


@dataclass(slots=True, frozen=True)
class YouTube:
    """Immutable class representing a single YouTube video. It can be initialized with a video ID or a URL."""
    # This is the only field passed during initialization.
    video_id: str
    
    # These fields are populated in __post_init__ and are not part of the constructor.
    display_id: str = field(init=False)
    title: str = field(init=False)
    full_title: str = field(init=False)
    description: str = field(init=False)
    uploader: str = field(init=False)
    uploader_id: str = field(init=False)
    uploader_url: str = field(init=False)
    channel_id: str = field(init=False)
    channel_url: str = field(init=False)
    duration: int = field(init=False)
    duration_string: str = field(init=False)
    view_count: int = field(init=False)
    like_count: int = field(init=False)
    comment_count: int = field(init=False)
    upload_date: str = field(init=False)
    webpage_url: str = field(init=False)
    tags: List[str] = field(init=False)
    categories: List[str] = field(init=False)
    thumbnails: List[Thumbnail] = field(init=False)
    formats: List[Format] = field(init=False)
    automatic_captions: Dict[str, List[Caption]] = field(init=False)
    
    def __post_init__(self):
        json_data = get_info_json(self.video_id)
        if not json_data:
            msg = f"Unable to fetch metadata for youtube video {self.video_id}"
            warn(msg)
            
            for f in self.__dataclass_fields__:
                if not f.init:
                    object.__setattr__(self, f.name, None)
            return
        
        # Use object.__setattr__ to assign values to the frozen fields.
        object.__setattr__(self, 'display_id', json_data.get("display_id"))
        object.__setattr__(self, 'title', json_data.get("title"))
        object.__setattr__(self, 'full_title', json_data.get("fulltitle"))
        object.__setattr__(self, 'description', json_data.get("description"))
        object.__setattr__(self, 'uploader', json_data.get("uploader"))
        object.__setattr__(self, 'uploader_id', json_data.get("uploader_id"))
        object.__setattr__(self, 'uploader_url', json_data.get("uploader_url"))
        object.__setattr__(self, 'channel_id', json_data.get("channel_id"))
        object.__setattr__(self, 'channel_url', json_data.get("channel_url"))
        object.__setattr__(self, 'duration', json_data.get("duration"))
        object.__setattr__(self, 'duration_string', json_data.get("duration_string"))
        object.__setattr__(self, 'view_count', json_data.get("view_count"))
        object.__setattr__(self, 'like_count', json_data.get("like_count"))
        object.__setattr__(self, 'comment_count', json_data.get("comment_count"))
        object.__setattr__(self, 'upload_date', json_data.get("upload_date"))
        object.__setattr__(self, 'webpage_url', json_data.get("webpage_url"))
        object.__setattr__(self, 'tags', json_data.get("tags", []))
        object.__setattr__(self, 'categories', json_data.get("categories", []))
        
        # --- Parse nested objects directly here ---
        
        # Parse thumbnails
        thumbs = [Thumbnail(**thumb) for thumb in json_data.get("thumbnails", [])]
        object.__setattr__(self, 'thumbnails', tuple(thumbs))  # Use tuple for immutability
        
        # Parse formats
        parsed_formats = []
        for f in json_data.get("formats", []):
            valid_keys = {key: f[key] for key in f if key in Format.__annotations__}
            parsed_formats.append(Format(**valid_keys))
        object.__setattr__(self, 'formats', tuple(parsed_formats))  # Use tuple
        
        # Parse captions
        captions_dict = {}
        for lang, cap_list in json_data.get("automatic_captions", {}).items():
            captions_dict[lang] = tuple([Caption(**cap) for cap in cap_list])
        object.__setattr__(self, 'automatic_captions', captions_dict)
    
    @property
    def best_thumbnail(self) -> Optional[Thumbnail]:
        """Returns the thumbnail with the highest preference."""
        if not self.thumbnails:
            return None
        return max(self.thumbnails, key=lambda t: t.preference)
    
    def get_audio_only_formats(self) -> List[Format]:
        """Filters for formats that are audio-only."""
        return [f for f in self.formats if f.vcodec == "none" and f.acodec != "none"]
    
    def get_video_only_formats(self) -> List[Format]:
        """Filters for formats that are video-only."""
        return [f for f in self.formats if f.acodec == "none" and f.vcodec != "none"]
    
    def get_best_audio(self, codec: str = 'opus') -> Optional[Format]:
        """
        Gets the best audio-only format, optionally by a specific codec.
        'tbr' (total bitrate) is used to determine quality.
        """
        audio_formats = [f for f in self.get_audio_only_formats() if f.acodec and codec in f.acodec]
        if not audio_formats:
            return None
        return max(audio_formats, key=lambda f: f.tbr or 0)
