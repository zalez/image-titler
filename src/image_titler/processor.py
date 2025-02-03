from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Optional
import sys
import os

class FontError(Exception):
    """Custom exception for font-related errors."""
    pass

class ImageProcessor:
    TARGET_WIDTH = 1920
    TARGET_HEIGHT = 1080
    OVERLAY_HEIGHT_RATIO = 0.1  # 10% of height
    MARGIN_RATIO = 0.1  # 10% of overlay height
    DEFAULT_BLUR_RADIUS = 5

    def __init__(self, input_path: Path, crop_to_hd: bool = True):
        try:
            self.input_image = Image.open(input_path)
        except Exception as e:
            raise RuntimeError(f"Failed to open image: {str(e)}")

        self.crop_to_hd = crop_to_hd

    def _find_system_font(self, font_name: str) -> str:
        """Find system font path with smart variant selection."""
        font_dirs = []
        if sys.platform == "darwin":  # macOS
            font_dirs.extend([
                "/System/Library/Fonts",
                "/Library/Fonts",
                os.path.expanduser("~/Library/Fonts")
            ])
        elif sys.platform == "win32":  # Windows
            font_dirs.append(os.path.join(os.environ["WINDIR"], "Fonts"))
        else:  # Linux/Unix
            font_dirs.extend([
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.fonts")
            ])

        # Common name variations
        name_variations = [
            font_name,
            font_name.replace(" ", ""),
            font_name.replace(" ", "_"),
            font_name.replace(" ", "-"),
            font_name.split()[0],  # First word only
            ''.join(font_name.split()),  # Remove all spaces
        ]

        # Style priority (from most to least preferred)
        style_priorities = [
            "regular",
            "rg",
            "normal",
            "book",
            "medium",
            "roman",
            "standard"
        ]

        # Styles to avoid unless specifically requested
        variant_styles = [
            "italic",
            "oblique",
            "bold",
            "light",
            "thin",
            "heavy",
            "black",
            "condensed",
            "expanded",
            "narrow",
            "wide"
        ]

        debug = os.environ.get("IMAGE_TITLER_DEBUG") == "1"
        if debug:
            print(f"Searching for font: {font_name}")
            print(f"Font directories: {font_dirs}")
            print(f"Name variations: {name_variations}")

        # First, collect all matching fonts
        matching_fonts = []

        for font_dir in font_dirs:
            if not os.path.exists(font_dir):
                continue

            for root, _, files in os.walk(font_dir):
                for file in files:
                    if not file.lower().endswith(('.ttf', '.otf')):
                        continue

                    if debug:
                        print(f"Checking file: {file}")

                    # Check if the file matches any of our name variations
                    if any(var.lower() in file.lower() for var in name_variations):
                        font_path = os.path.join(root, file)
                        matching_fonts.append((file, font_path))

        if not matching_fonts:
            raise FontError(
                f"Font '{font_name}' not found in system fonts.\n"
                "Try setting IMAGE_TITLER_DEBUG=1 for more detailed font search information."
            )

        # Score each matching font
        def score_font(font_file: str) -> int:
            font_lower = font_file.lower()
            score = 0

            # Highest priority: exact match
            if font_lower == f"{font_name.lower()}.ttf" or font_lower == f"{font_name.lower()}.otf":
                return 1000

            # High priority: contains "regular" or similar
            for i, style in enumerate(style_priorities):
                if style in font_lower:
                    score += 100 - i
                    break

            # Lower priority: contains variant styles
            for style in variant_styles:
                if style in font_lower:
                    score -= 50

            # Penalize longer names (they're usually variants)
            score -= len(font_lower)

            return score

        # Sort fonts by score
        matching_fonts.sort(key=lambda x: score_font(x[0]), reverse=True)

        if debug:
            print("\nMatching fonts (in priority order):")
            for font_file, font_path in matching_fonts:
                print(f"  {font_file} (score: {score_font(font_file)})")

        best_match = matching_fonts[0][1]
        if debug:
            print(f"\nSelected font: {best_match}")

        return best_match

    def process(
        self,
        output_path: Path,
        logo_path: Optional[Path] = None,
        text: Optional[str] = None,
        font_name: Optional[str] = None,
        transparency: int = 20,
        blur: int = 0,  # 0-100%
        blur_radius: int = DEFAULT_BLUR_RADIUS
    ) -> None:
        try:
            if self.input_image.mode != 'RGB':
                self.input_image = self.input_image.convert('RGB')

            if self.crop_to_hd:
                self.input_image = self._resize_and_crop()

            if blur > 0:
                self._apply_blur(blur, blur_radius)

            self._add_overlay_bar(transparency)

            if logo_path:
                try:
                    self._add_logo(logo_path)
                except Exception as e:
                    raise RuntimeError(f"Failed to process logo: {str(e)}")

            if text:
                try:
                    self._add_text(text, font_name)
                except FontError as e:
                    raise FontError(str(e))

            self.input_image.save(output_path)
        except Exception as e:
            raise RuntimeError(f"Image processing failed: {str(e)}")

    def _apply_blur(self, blur_amount: int, radius: int) -> None:
        """Apply gaussian blur as an overlay with specified opacity."""
        # Create a blurred version of the image
        blurred = self.input_image.copy()
        blurred = blurred.filter(ImageFilter.GaussianBlur(radius=radius))

        # Convert both images to RGBA if needed
        if self.input_image.mode != 'RGBA':
            self.input_image = self.input_image.convert('RGBA')
        if blurred.mode != 'RGBA':
            blurred = blurred.convert('RGBA')

        # Calculate opacity for the blur layer
        opacity = int(255 * (blur_amount / 100))

        # Create a new image with the same size and mode
        result = Image.new('RGBA', self.input_image.size)

        # Paste the original image
        result.paste(self.input_image, (0, 0))

        # Apply the blurred image with specified opacity
        blurred.putalpha(opacity)
        result = Image.alpha_composite(result, blurred)

        self.input_image = result

        debug = os.environ.get("IMAGE_TITLER_DEBUG") == "1"
        if debug:
            print("\nBlur settings:")
            print(f"Blur amount: {blur_amount}%")
            print(f"Blur radius: {radius}px")

    def _resize_and_crop(self) -> Image.Image:
        # Calculate dimensions to maintain aspect ratio
        ratio = max(self.TARGET_WIDTH / self.input_image.width,
                   self.TARGET_HEIGHT / self.input_image.height)

        new_size = (int(self.input_image.width * ratio),
                   int(self.input_image.height * ratio))

        # Resize
        resized = self.input_image.resize(new_size, Image.Resampling.LANCZOS)

        # Calculate crop box
        left = (resized.width - self.TARGET_WIDTH) // 2
        top = (resized.height - self.TARGET_HEIGHT) // 2
        right = left + self.TARGET_WIDTH
        bottom = top + self.TARGET_HEIGHT

        # Crop and return
        return resized.crop((left, top, right, bottom))

    def _add_overlay_bar(self, transparency: int) -> None:
        overlay_height = int(self.input_image.height * self.OVERLAY_HEIGHT_RATIO)
        # Convert transparency percentage to alpha value (0-255)
        alpha = int(255 * (1 - transparency / 100))
        overlay = Image.new('RGBA', (self.input_image.width, overlay_height),
                          (255, 255, 255, alpha))

        if self.input_image.mode != 'RGBA':
            self.input_image = self.input_image.convert('RGBA')

        self.input_image.paste(overlay, (0, 0), overlay)

    def _add_logo(self, logo_path: Path) -> None:
        # Load and convert logo to RGBA to preserve transparency
        logo = Image.open(logo_path).convert('RGBA')

        # Calculate dimensions
        overlay_height = int(self.input_image.height * self.OVERLAY_HEIGHT_RATIO)
        margin = int(overlay_height * self.MARGIN_RATIO)
        max_logo_height = overlay_height - (2 * margin)

        # Calculate logo scaling
        scale_ratio = max_logo_height / logo.height
        new_logo_size = (
            int(logo.width * scale_ratio),
            int(logo.height * scale_ratio)
        )

        # Resize logo
        logo = logo.resize(new_logo_size, Image.Resampling.LANCZOS)

        # Calculate position within 1080x1080 viewport
        viewport_start_x = (self.TARGET_WIDTH - self.TARGET_HEIGHT) // 2
        logo_x = viewport_start_x + margin
        logo_y = margin  # Top margin

        # Store the logo's right boundary for text positioning
        self.logo_right_x = logo_x + new_logo_size[0] + margin

        # Create a temporary image for alpha compositing
        temp = Image.new('RGBA', self.input_image.size, (0, 0, 0, 0))
        temp.paste(logo, (logo_x, logo_y))

        # Composite the logo onto the main image
        self.input_image = Image.alpha_composite(
            self.input_image.convert('RGBA'),
            temp
        )

    def _add_text(self, text: str, font_name: str | None) -> None:
        try:
            if font_name:
                font_path = self._find_system_font(font_name)
            else:
                font_path = self._find_system_font("Arial")
        except FontError as e:
            raise FontError(f"Font error: {str(e)}")

        # Create drawing context
        draw = ImageDraw.Draw(self.input_image)

        # Calculate dimensions
        overlay_height = int(self.input_image.height * self.OVERLAY_HEIGHT_RATIO)
        margin = int(overlay_height * self.MARGIN_RATIO)
        max_text_height = int(overlay_height * 0.5)  # 50% of overlay height

        # Calculate viewport boundaries
        viewport_start_x = (self.TARGET_WIDTH - self.TARGET_HEIGHT) // 2
        viewport_end_x = viewport_start_x + self.TARGET_HEIGHT

        # Text positioning within viewport
        text_right_x = viewport_end_x - margin
        text_left_min_x = getattr(self, 'logo_right_x', viewport_start_x + margin)

        debug = os.environ.get("IMAGE_TITLER_DEBUG") == "1"
        if debug:
            print(f"\nText layout calculations:")
            print(f"Overlay height: {overlay_height}")
            print(f"Max text height: {max_text_height}")
            print(f"Viewport: {viewport_start_x} to {viewport_end_x}")
            print(f"Text right position: {text_right_x}")
            print(f"Minimum text left position: {text_left_min_x}")

        # Binary search for optimal font size
        min_size = 1
        max_size = max_text_height * 2  # Start with larger max size
        current_font_size = None
        current_bbox = None

        while min_size <= max_size:
            mid_size = (min_size + max_size) // 2
            try:
                font = ImageFont.truetype(font_path, mid_size)
            except OSError as e:
                raise FontError(f"Failed to load font: {str(e)}")

            # Get text dimensions
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Calculate where text would start if right-aligned
            potential_text_left = text_right_x - text_width

            if text_height <= max_text_height and potential_text_left >= text_left_min_x:
                current_font_size = mid_size
                current_bbox = bbox
                min_size = mid_size + 1
            else:
                max_size = mid_size - 1

        if current_font_size is None or current_bbox is None:
            raise RuntimeError("Could not find suitable font size for text")

        if debug:
            print(f"Selected font size: {current_font_size}")
            print(f"Final text dimensions: {current_bbox[2] - current_bbox[0]}x{current_bbox[3] - current_bbox[1]}")

        # Use the optimal font size
        font = ImageFont.truetype(font_path, current_font_size)

        # Calculate text dimensions for final positioning
        final_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = final_bbox[2] - final_bbox[0]
        text_height = final_bbox[3] - final_bbox[1]

        # Calculate vertical center of overlay bar
        overlay_center_y = overlay_height // 2

        # Center text vertically based on its bounding box
        text_y = overlay_center_y - (text_height // 2) - final_bbox[1]

        if debug:
            print(f"Overlay height: {overlay_height}")
            print(f"Overlay center Y: {overlay_center_y}")
            print(f"Text bbox: top={final_bbox[1]}, bottom={final_bbox[3]}")
            print(f"Text height: {text_height}")
            print(f"Text Y position: {text_y}")

        # Calculate final horizontal position (right-aligned within viewport)
        text_x = text_right_x - text_width

        # Draw text
        draw.text((text_x, text_y), text, font=font, fill=(0, 0, 0))

def process_image(
    input_path: Path,
    output_path: Path,
    logo_path: Optional[Path] = None,
    text: Optional[str] = None,
    font_name: Optional[str] = None,
    crop_to_hd: bool = True,
    transparency: int = 20,
    blur: int = 0,
    blur_radius: int = ImageProcessor.DEFAULT_BLUR_RADIUS
) -> None:
    processor = ImageProcessor(input_path, crop_to_hd)
    processor.process(output_path, logo_path, text, font_name, transparency, blur, blur_radius)
