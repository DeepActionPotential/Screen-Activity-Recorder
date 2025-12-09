from PIL import Image
import numpy as np
import base64
import io
import os
from PIL import Image, ImageFilter, ImageDraw
import re
from typing import List, Dict

from schemas.ner_schemas import NEREntites


def open_image(img):
    """
    Convert an image input to a PIL Image.

    Supported input types:
    - str: File path or Base64 string
    - bytes: Base64-encoded image
    - numpy.ndarray: OpenCV image or similar
    - PIL.Image.Image: Already a PIL image (returns as is)

    Args:
        img (str | bytes | np.ndarray | PIL.Image.Image): Image input.

    Returns:
        PIL.Image.Image: Converted PIL Image object.

    Raises:
        ValueError: If the input type is unsupported or the image cannot be processed.
    """
    # Case 1: Already PIL image
    if isinstance(img, Image.Image):
        return img

    # Case 2: Numpy array
    if isinstance(img, np.ndarray):
        return Image.fromarray(img)

    # Case 3: String input
    if isinstance(img, str):
        # Check if it's a file path
        if os.path.isfile(img):
            return Image.open(img).convert("RGB")
        # Otherwise, treat as base64
        try:
            img_data = base64.b64decode(img)
            return Image.open(io.BytesIO(img_data)).convert("RGB")
        except Exception:
            raise ValueError("Invalid string input. Must be file path or base64-encoded image.")

    # Case 4: Bytes (base64-encoded image)
    if isinstance(img, bytes):
        try:
            img_data = base64.b64decode(img)
            return Image.open(io.BytesIO(img_data)).convert("RGB")
        except Exception:
            raise ValueError("Invalid bytes input. Must be base64-encoded image.")

    raise ValueError("Unsupported input type. Provide a path, base64 string, bytes, PIL image, or numpy array.")




def blur_region_with_bbox(pil_img, bbox):
    """
    Blur a region in a PIL Image specified by a quadrilateral bounding box.

    Args:
        pil_img (PIL.Image.Image): Input PIL image.
        bbox (list): Bounding box coordinates in the format:
                     [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]

    Returns:
        PIL.Image.Image: PIL image with the specified region blurred.

    Raises:
        ValueError: If bbox is not in the correct format or the image is invalid.
    """
    if not isinstance(pil_img, Image.Image):
        raise ValueError("Input must be a PIL.Image.Image object.")
    if len(bbox) != 4 or not all(len(point) == 2 for point in bbox):
        raise ValueError("Bounding box must be a list of four [x, y] points.")

    # Create a mask for the region to blur
    mask = Image.new("L", pil_img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(bbox, fill=255)

    # Apply blur to the entire image
    blurred_img = pil_img.filter(ImageFilter.GaussianBlur(radius=10))

    # Composite original and blurred images using the mask
    final_img = Image.composite(blurred_img, pil_img, mask)

    return final_img



from PIL import Image, ImageDraw, ImageFilter
from typing import List
from PIL import Image, ImageDraw, ImageFilter
from typing import List

def blur_regions_with_bboxs(pil_img: Image.Image, bboxes: List[List[List[int]]], blur_radius: int = 8) -> Image.Image:
    """
    Blur multiple regions in a PIL Image specified by a list of quadrilateral bounding boxes.

    Args:
        pil_img (PIL.Image.Image): Input PIL image.
        bboxes (List[List[List[int]]]): List of bounding boxes, each in format:
                                         [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
        blur_radius (int): Radius for Gaussian blur. Default = 8.

    Returns:
        PIL.Image.Image: Image with all specified regions blurred.
    """
    img = pil_img.convert("RGBA")

    for bbox in bboxes:
        # Convert all points to integers
        xs = [int(point[0]) for point in bbox]
        ys = [int(point[1]) for point in bbox]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        # Ensure positive width and height
        if max_x <= min_x or max_y <= min_y:
            continue  # Skip invalid bbox

        # Crop and blur
        region = img.crop((min_x, min_y, max_x, max_y))
        blurred_region = region.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        # Create mask matching blurred_region size
        mask_width, mask_height = blurred_region.size
        mask = Image.new("L", (mask_width, mask_height), 0)
        draw = ImageDraw.Draw(mask)
        polygon_points = [(x - min_x, y - min_y) for x, y in zip(xs, ys)]
        draw.polygon(polygon_points, fill=255)

        # Paste blurred region with mask
        img.paste(blurred_region, (min_x, min_y), mask)

    return img





def extract_common_pii_sequences(text: str) -> List[str]:
    """
    Detects common PII sequences in the given text using regex patterns.
    Returns a list of detected PII values (flat list, no categories).

    Args:
        text (str): Input text to scan for PII patterns.

    Returns:
        List[str]: List of detected PII sequences.
    """


    # Pre-clean: fix common OCR mistakes
    text = re.sub(r"\s+@\s+", "@", text)        # remove spaces around @
    text = re.sub(r"@\s+([a-zA-Z]+)\s+([a-zA-Z]+)", r"@\1.\2", text)  # fix domain spaces like 'gmail com'

    patterns = [
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",  # email
        r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b",  # phone
        r"\b(?:\d[ -]*?){13,16}\b",  # credit card
        r"\b\d{3,4}\b",  # CVV
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"(?i)\b(password|pwd)\s*[:=]\s*[^\s]{4,}\b",  # password
    ]

    matches = []
    for pattern in patterns:
        found = re.findall(pattern, text)
        for f in found:
            if isinstance(f, tuple):
                matches.append(f[0])
            else:
                matches.append(f)
    return matches



def extract_sensitive_sequences(ner_entities: NEREntites, non_sensitive_labels: dict) -> List[str]:
    """
    Extract sequences of sensitive entities by merging consecutive tokens of the same
    entity type (e.g., FIRSTNAME, LASTNAME), excluding non-sensitive labels (e.g., {"O": 110}).

    - Closes the current sequence when a non-sensitive label is encountered.
    - Starts a new sequence on B-<TYPE>.
    - Appends to the current sequence on I-<TYPE> if the TYPE matches; otherwise closes and starts new.

    Args:
        ner_entities (NEREntites): Container with NEREntity objects.
        non_sensitive_labels (dict): Dict of labels to treat as non-sensitive.

    Returns:
        List[str]: Merged sensitive entity strings.
    """
    sequences: List[str] = []
    current_sequence: List[str] = []
    current_label_type: str = None

    for entity in ner_entities.to_list():
        label = entity.entity_label

        # If this is a non-sensitive label (e.g., "O"), close any open sequence and skip.
        if label in non_sensitive_labels:
            if current_sequence:
                sequences.append("".join(current_sequence))
                current_sequence = []
                current_label_type = None
            continue

        # Expect labels like "B-FIRSTNAME" or "I-FIRSTNAME"
        if "-" in label:
            prefix, label_type = label.split("-", 1)
        else:
            # Unknown/unsupported label format: close any open sequence and skip.
            if current_sequence:
                sequences.append("".join(current_sequence))
                current_sequence = []
                current_label_type = None
            continue

        clean_text = entity.entity_text.replace("##", "")

        if prefix == "B":
            # Start a new entity: close previous if exists
            if current_sequence:
                sequences.append("".join(current_sequence))
            current_sequence = [clean_text]
            current_label_type = label_type

        elif prefix == "I":
            if current_label_type == label_type and current_sequence:
                current_sequence.append(clean_text)
            else:
                # Label type changed or no open sequence: close previous (if any) and start new
                if current_sequence:
                    sequences.append("".join(current_sequence))
                current_sequence = [clean_text]
                current_label_type = label_type

    # Flush tail
    if current_sequence:
        sequences.append("".join(current_sequence))

    return sequences


import base64
from io import BytesIO
from PIL import Image

# ---------------------------
# Function: Convert image to Base64
# ---------------------------
def image_to_base64(img: Image.Image) -> str:
    """
    Convert a PIL Image to a Base64-encoded string.

    Args:
        img (Image.Image): Input PIL image.

    Returns:
        str: Base64-encoded string of the image (PNG format).
    """
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()
    return base64.b64encode(img_bytes).decode("utf-8")



def run_command_against_image(image_base64: str, model: str, prompt: str):

    response = model.generate_content(
        prompt=prompt,
        context=[{"image": {"content": image_base64}}],
        response_modalities=["TEXT", "IMAGE"]
    )
    return response


def run_command_against_text(text: str, model: str, prompt: str) -> str:

    
    try:
        response = model.generate_content([prompt + text])
        return response.text
    
    except Exception as e:
        return "error:" + str(e)


import time
import random
import string

def generate_timestamp_id(length: int = 10) -> str:
    """
    Generate a random ID starting with the current timestamp (in milliseconds),
    followed by random alphanumeric characters.

    Args:
        length (int): Number of random characters to append after the timestamp. Default is 6.

    Returns:
        str: Timestamp-based random ID.
    """
    # Current timestamp in milliseconds
    timestamp = str(int(time.time() * 1000))

    # Random alphanumeric suffix
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    return str(f"{timestamp}{suffix}")




import win32gui
import win32process
import psutil

def get_active_window_info():
    """
    Fetch the active window's process name, title, executable path, and command line.
    Returns (process_name, window_title, exe_path, cmd_command) with default values if any step fails.
    """
    try:
        # Get the foreground window handle
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return 'unknown', 'No active window', '', ''
            
        # Get window title
        window_title = win32gui.GetWindowText(hwnd)
        
        # Get process ID
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid <= 0:
                return 'unknown', window_title or 'No title', '', ''
                
            # Get process info
            try:
                process = psutil.Process(pid)
                process_name = process.name()
                exe_path = process.exe() or ''
                try:
                    cmd_command = ' '.join(process.cmdline())
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    cmd_command = ''
                
                return process_name, window_title, exe_path, cmd_command
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                return 'unknown', window_title or 'No title', '', ''
                
        except Exception as e:
            return 'unknown', window_title or 'No title', '', ''
            
    except Exception as e:
        # Fallback for any other errors
        return 'unknown', 'Error getting window info', '', ''
