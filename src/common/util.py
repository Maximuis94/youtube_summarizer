"""
Various helper functions related to yt-dlp

"""
import json
import os
import re
from collections.abc import Sequence
from typing import Optional

ID_LENGTH: int = 11
"""The amount of characters in a YouTube ID"""

illegal_chars = ':*|<>/\\\"\''
"""Characters that are to be removed from fields"""


def is_youtube_url(string: str) -> bool:
    """Returns True if the given string is a URL, False if not"""
    return any([segment in string for segment in ("youtu.be/", "youtube.com/shorts/", "youtube.com/watch?v=")])


def extract_id(url: str) -> str:
    """Extract the ID from the YouTube URL `url`"""
    # Is this already a display id?
    if len(url) == 11 and "?" not in url and "=" not in url and "/" not in url:
        return url
    for segment in ("youtu.be/", "youtube.com/shorts/", "youtube.com/watch?v="):
        if segment in url:
            return url.split(segment)[1][:ID_LENGTH]
    raise RuntimeError(f"Could not extract ID from URL {url}")


def reformat_json(input_path: str, output_path: Optional[str] = None,
                  preserve_captions: Optional[Sequence[str]] = ('nl', 'en'), remove_input: bool = False):
    """
    Reformats a json file to make it better manually readable.
    *** NOTE: this will replace the old json file with the reformatted json file without further warnings ***

    Parameters
    ----------
    input_path : str
        Path to the json file
    output_path : Optional[str], None by default
        Rename the original file to `output_path`, if passed. Note that this will also
    preserve_captions : Sequence[str], ('nl', 'en') by default
        Which automated captions to preserve. If not passed, preserve all automatic captions.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"input_path='{input_path}' does not exist")
    
    rename_output = not output_path
    if rename_output:
        output_path = input_path.replace('.json', '_.json')
    
    if os.path.exists(output_path):
        raise FileExistsError(f"Output path at '{output_path}' already exists")
    
    try:
        # Load the JSON data from the input file
        with open(input_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if preserve_captions:
                if isinstance(preserve_captions, str):
                    preserve_captions = [preserve_captions]
                captions = {k: v for k, v in data.get("automatic_captions", {}).items() if k in preserve_captions}
                data["automatic_captions"] = captions
        
        # Convert the JSON data to a pretty-printed string
        formatted_json = json.dumps(data, indent=4, sort_keys=True)
        
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(formatted_json)
    
    finally:
        if os.path.exists(output_path) and rename_output or remove_input and input_path != output_path:
            os.remove(input_path)
            os.rename(output_path, input_path)


def remove_illegal_chars(s: str, *, to_remove: Optional[str] = None) -> str:
    """Remove all 'illegal' chars from str `s` and return it."""
    chars = illegal_chars if to_remove is None else to_remove + illegal_chars
    return s.translate({ord(c): None for c in chars}) if len(chars) > 0 else s


def remove_emoji(text: str) -> str:
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # Emoticons
        "\U0001F300-\U0001F5FF"  # Symbols & Pictographs
        "\U0001F680-\U0001F6FF"  # Transport & Map
        "\U0001F700-\U0001F77F"  # Alchemical Symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols, Symbols & Pictographs Extended-A
        "\U0001FA70-\U0001FAFF"  # Symbols & Pictographs Extended-B
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"  # Enclosed characters
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text).strip()


def preprocess_string(s: any) -> str:
    """Converts `s` into a string and removes illegal characters before returning it."""
    s = remove_emoji(s)
    s = s.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    s = remove_illegal_chars(s)
    return s
