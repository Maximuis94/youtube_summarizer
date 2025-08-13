"""
Module with various implementations for specific parts of the info.json file.

At the very end there is also a single function that can be called to apply all methods


"""

import json
import os.path
from collections.abc import Iterable
from enum import Enum
from typing import Any, Dict, Optional, Tuple
from typing import Literal, LiteralString, Sequence

import requests
import time

from src.common.constants import URL_PREFIXES
from src.common.dtypes import CC_EXT_TYPE
from src.common.youtube_info import generate_file_name, probe_url


def _load_json(path: str):
    """JSON load function that will be applied throughout this module"""
    return json.load(open(path, encoding='utf-8'))


def extract_comments(path: str, content: Optional[Any] = None, remove_keys: Optional[Iterable[str]] = None, **kwargs):
    """Extract the comments from the file at `path`"""
    out_file = kwargs.get("out_file", path[:-5] + ".comments.json")
    
    load_content = content is None
    if load_content:
        content = _load_json(path)
    
    display_id = content["display_id"]
    output = []
    
    comments = content.pop("comments", None)
    if comments is None:
        return content
    
    for _next in comments:
        if remove_keys is not None:
            for k in remove_keys:
                _next.pop(k, None)
        _next['display_id'] = display_id
        output.append(_next)
        # print(Comment.from_json(**_next), end='\n\n')
    
    if len(output) > 0:
        json.dump(output, open(out_file, 'w'), indent=2)
        
        if load_content and kwargs.get('save_content', True):
            json.dump(content, open(path, 'w'), indent=2)
    if not load_content:
        return content


def extract_all(path: str, **kwargs):
    """Single call that will execute all extract functions listed above"""
    content = _load_json(path)
    content = extract_comments(path, content, remove_keys=("_time_text", "author_thumbnail", "author_url"))
    json.dump(content, open(path, 'w'), indent=2)

"""Typing used to refer to CC extensions"""


class CC_EXT(Enum):
    """Allowed closed caption extensions"""
    JSON3 = 0
    SRV1 = 1
    SRV2 = 2
    SRV3 = 3
    TTML = 4
    VTT = 5
    
    def __str__(self) -> CC_EXT_TYPE:
        return ('json3', 'srv1', 'srv2', 'srv3', 'ttml', 'vtt')[self.value]


STRING_ENCODING = "utf-8"
"""The encoding that is to be applied when opening text file parsers"""


def load_data(source: str):
    """
    Loads data from a URL or from a local path
    
    Parameters
    ----------
    source : str
        The source from which the data is accessed. Can be a local path or a URL.

    Returns
    -------
    Dict[str, any]
        The parsed JSON

    """
    
    # If the source looks like a URL, download the content.
    if source.startswith(URL_PREFIXES):
        response = requests.get(source)
        s = response.status_code  # Raise an error for bad responses
        if s == 200:
            return response.json()
        else:
            msg = f"An error ({s}) occurred while loading data for source={source}"
            raise RuntimeError(msg)
        
    elif os.path.exists(source):
        # Otherwise, assume it's a local file path.
        with open(source, 'r', encoding=STRING_ENCODING) as f:
            return json.load(f)
    msg = f"The source that was passed, {source}, is neither a URL not an existing local file..."
    raise RuntimeError(msg)


def extract_cc_url(json_file: str, language: str = "en",
                   cc_ext: Optional[Literal['json3', 'srv1', 'srv2', 'srv3', 'ttml', 'vtt']] = None) -> str:
    """
    Load the JSON file at `json_file` and extract a URL that can be used to download the automatically generated Closed
    Caption.
    
    Parameters
    ----------
    json_file : str
        Path to the JSON file
    language : str, optional, "en" by default
        The language of the to-be extracted closed-caption URL
    cc_ext : Optional[Literal['json3', 'srv1', 'srv2', 'srv3', 'ttml', 'vtt']], optional, None by default
        If passed, actively search for this extension within the available URLs. If undefined, pick the first ext.
    Returns
    -------
    str
        URL that can be used to download the automatically generated Closed Caption.

    """
    json_data = load_data(json_file)
    try:
        captions = json_data["automatic_captions"]
    except KeyError:
        raise RuntimeError(f"""json_file at "{json_file}" does not appear to have closed caption URLs""")
    
    try:
        cc_urls = captions[language]
    except KeyError:
        raise RuntimeError(f'json_file at "{json_file}" has closed caption urls, but not of language "{language}". '
                           f'It does have the following languages: {" ".join(captions.keys())}')
    
    ext = str(cc_ext)
    for _next in cc_urls:
        if cc_ext is None or _next.get("ext") == ext:
            return _next["url"]
    msg = (f'Unable to find the requested ext={cc_ext} in the json file. '
           f'It does have the following extensions: {" ".join([k.get('ext') for k in cc_urls])}')
    raise RuntimeError(msg)
    
    
def parse_cc(source: str, out_file: Optional[str | LiteralString | bytes] = None, **kwargs) -> Optional[Sequence[str]]:
    """
    Parse the downloaded CC file
    
    Parameters
    ----------
    source : str
        URL or local path that provides the input
    out_file : str
        The path to the file that is to be produced

    Returns
    -------
    

    """
    try:
        data = load_data(source)
    except RuntimeError:
        return
    
    paragraphs = []
    current_paragraph = ""
    
    # Process events in order
    for event in data.get("events", []):
        # Combine all text segments in this event
        segs = event.get("segs", [])
        text = "".join(seg.get("utf8", "") for seg in segs)
        
        # If the event is just a newline or empty after stripping, treat as a break
        if text.strip() == "":
            if current_paragraph.strip():
                paragraphs.append(current_paragraph.strip())
                current_paragraph = ""
            continue
        
        # If the event is marked as "append", then add to the current paragraph
        if event.get("aAppend") == 1:
            current_paragraph += " " + text.strip()
        else:
            # If current_paragraph already has content, flush it as a separate paragraph
            if current_paragraph.strip():
                paragraphs.append(current_paragraph.strip())
            current_paragraph = text.strip()
    
    # Append any remaining text as the last paragraph
    if current_paragraph.strip():
        paragraphs.append(current_paragraph.strip())

    with open(str(out_file), 'w', encoding=STRING_ENCODING) as f:
        f.writelines(" ".join(paragraphs))
    
    if kwargs.get("output_file"):
        with open(kwargs.get("output_file"), 'w', encoding=STRING_ENCODING) as f:
            f.writelines(" ".join(paragraphs))
    
    return paragraphs


def process_url(url: str, output_folder: str, add_cookies: bool = False, add_comments: bool = False, path_cookies_downloaded: Optional[str] = None, **kwargs) -> Tuple[str, str]:
    """
    Function that extracts the info json from a URL, then parses this json file to extract a generated CC url and
    finally converts the text file downloaded from this URL into a parsed file.
    
    Parameters
    ----------
    url : str
        YouTube URL
    output_folder : str
        Folder in which the output files are to be placed.
    add_cookies : bool, optional, False by default
        If True, add cookies to the command executed
    add_comments : bool, optional, False by default
        If True, download the comments along with the video metadata
    path_cookies_downloaded: str, optional, None by default
        Path where cookies extract is saved, should it be needed.
    
    Other Parameters
    ----------------
    language : str, optional, "en" by default
        The language of the Closed Caption that is to be downloaded
    cc_ext : Optional[Literal['json3', 'srv1', 'srv2', 'srv3', 'ttml', 'vtt']], optional, None by default
        If passed, actively search for this extension within the available URLs. If undefined, pick the first ext.
    

    Returns
    -------
    Tuple[str, str]
        A pair of paths; the former referring to the .info.json file, the latter to the parser CC file.

    """
    if len(url) == 11:
        url = f"https://www.youtube.com/watch?v={url}"
    json_file = generate_file_name(url) + ".info.json"
    
    if not os.path.exists(json_file):
        probe_url(url=url, add_cookies_file=add_cookies, add_comments=add_comments)
    
    if not os.path.exists(json_file):
        if path_cookies_downloaded is not None and os.path.exists(path_cookies_downloaded) and not add_cookies:
            
            if os.path.exists(path_cookies_downloaded) and os.path.getmtime(
                    path_cookies_downloaded) + 1800 < time.time():
                print(f"The cookies file located at '{path_cookies_downloaded}' has expired. "
                      f"Extract a new file to be able to use cookies again.")
                os.remove(path_cookies_downloaded)
            else:
                print("Failed to process URL - retrying with cookies...")
                return process_url(url, add_cookies=True, path_cookies_downloaded=path_cookies_downloaded)
        else:
            print(f"Failed to process URL {url}")
            return
    extract_all(json_file)
    output_file = os.path.splitext(os.path.split(json_file)[-1])[0] + ".txt"
    # print(f"Generated json file at '{json_file}'")
    
    try:
        cc_ext = getattr(CC_EXT, kwargs.get("cc_ext", 'json3').upper())
    except AttributeError:
        raise RuntimeError(f"Non-existent keyword arg {kwargs.get('cc_ext')} was submitted for getting cc extension. "
                           f"Legal extensions are; {CC_EXT._member_names_}")
    try:
        cc_url = extract_cc_url(json_file, language=kwargs.get("language", "en"), cc_ext=cc_ext)
    except RuntimeError:
        return
    output_file = os.path.join(output_folder, output_file)
    parse_cc(cc_url, out_file=output_file)
    
    # if kwargs.get("output_folder") is not None:
    #     if not os.path.exists(kwargs['output_folder']):
    #         msg = f"Output folder at {kwargs['output_folder']} does not exist. "
    #         warn(msg)
    #     else:
    #         additional_output_file = os.path.join(kwargs['output_folder'], os.path.basename(output_file))
    #         shutil.copy(output_file, additional_output_file)
    
    return json_file, output_file
