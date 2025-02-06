# image-titler

A Python CLI utility for adding logos and text overlays to images, optimized for video conferencing backgrounds.

## Features

- Resize and crop input images to 1920x1080 (Full HD)
- Configurable blurring of the background (amount and radius)
- Add a semi-transparent white bar at the top
- Place a logo on the left side
- Add right-aligned text
- Smart font selection and sizing
- Maintains proper spacing and alignment within a centered 1080x1080 viewport

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/image-titler.git
cd image-titler

# Install with uv
uv pip install -e .
```

## Usage

```bash
# Basic usage
image-titler --logo path/to/logo.png --text "Your Text" path/to/image.jpg

# With custom font
image-titler --logo path/to/logo.png --text "Your Text" --font "Arial" path/to/image.jpg

# Process multiple images
image-titler --logo path/to/logo.png --text "Your Text" image1.jpg image2.png

# Additional options
image-titler --help
```

### Command Line Options

- `--logo PATH`: Path to logo image (PNG with transparency recommended)
- `--text TEXT`: Text to overlay on the image
- `--font FONT`: Font family to use (defaults to Arial)
- `--transparency INT`: Transparency percentage for the overlay bar (0-100, default: 20)
- `--blur INT`: Blur amount (0-100%)
- `--blur-radius INT`: Blur radius (default: 5)
- `--no-crop`: Disable automatic cropping to 1920x1080
- `--debug`: Enable debug output
- Multiple image paths can be provided as arguments

### Output

The utility creates new files with "_labeled" suffix:
- `image.jpg` → `image_labeled.jpg`
- `photo.png` → `photo_labeled.png`

If an output file already exists, you'll be prompted to:
1. Cancel
2. Overwrite
3. Use a new name (automatic numbering)

## Design Principles

- Images are cropped and resized to 1920x1080 while maintaining aspect ratio
- Blurring is applied by applying an extra layer of the blurred image at configurable opacity
- A semi-transparent white bar (10% of image height) is added at the top
- The logo is scaled to fit within the bar height (with 10% margins)
- Text is right-aligned and sized to:
  - Not exceed 50% of the bar height
  - Not overlap with the logo
  - Remain within a centered 1080x1080 viewport
- Font selection prioritizes regular/standard variants over stylized ones

## Requirements

- Python 3.12 or higher
- Dependencies:
  - click
  - Pillow
  - typing-extensions

## Development

The project uses:
- `uv` for dependency management
- Click for CLI interface
- Pillow for image processing
- Type hints throughout the codebase

## License

MIT
