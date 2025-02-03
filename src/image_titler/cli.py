import click
from pathlib import Path
import os
import sys
from .processor import process_image

def get_unique_output_path(base_path: Path) -> Path:
    """Generate a unique output path if file exists."""
    if not base_path.exists():
        return base_path

    counter = 1
    while True:
        new_path = base_path.parent / f"{base_path.stem}_{counter}{base_path.suffix}"
        if not new_path.exists():
            return new_path
        counter += 1

def handle_existing_file(output_path: Path) -> Path | None:
    """Handle existing output file with user interaction."""
    if output_path.exists():
        choice = click.prompt(
            f"\nFile {output_path} already exists. Choose action:\n"
            "[1] Cancel\n"
            "[2] Overwrite\n"
            "[3] Use new name\n"
            "Enter choice (1-3)",
            type=click.Choice(['1', '2', '3']),
            show_choices=False
        )

        if choice == '1':
            return None
        elif choice == '2':
            return output_path
        else:
            return get_unique_output_path(output_path)
    return output_path

@click.command()
@click.option('--logo', type=click.Path(exists=True, dir_okay=False), help='Path to logo image')
@click.option('--text', help='Text to overlay on image')
@click.option('--font', help='Font family to use for text')
@click.option('--no-crop', is_flag=True, help='Disable automatic cropping to 1920x1080')
@click.option('--transparency', type=int, default=20, help='Transparency percentage (0-100) for the overlay bar')
@click.option('--debug', is_flag=True, help='Enable debug output')
@click.argument('images', nargs=-1, type=click.Path(exists=True, dir_okay=False), required=True)
def main(logo: str | None, text: str | None, font: str | None, no_crop: bool,
         transparency: int, debug: bool, images: tuple[str, ...]) -> None:
    """Add logo and text overlay to images, optimized for video conferencing backgrounds."""

    # Set debug mode from either flag or environment variable
    if debug or os.environ.get("IMAGE_TITLER_DEBUG") == "1":
        os.environ["IMAGE_TITLER_DEBUG"] = "1"

    # Validate transparency
    if not 0 <= transparency <= 100:
        click.echo("Error: Transparency must be between 0 and 100", err=True)
        sys.exit(1)

    for image_path in images:
        try:
            output_path = Path(image_path).parent / f"{Path(image_path).stem}_labeled{Path(image_path).suffix}"

            # Handle existing file
            output_path = handle_existing_file(output_path)
            if output_path is None:
                click.echo(f"Skipping {image_path}")
                continue

            process_image(
                input_path=Path(image_path),
                output_path=output_path,
                logo_path=Path(logo) if logo else None,
                text=text,
                font_name=font,
                crop_to_hd=not no_crop,
                transparency=transparency
            )
            click.echo(f"Processed {image_path} -> {output_path}")
        except Exception as e:
            click.echo(f"Error processing {image_path}: {str(e)}", err=True)
