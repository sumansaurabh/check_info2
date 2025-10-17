"""
Script to create placeholder fixture images for integration tests
Run this to generate placeholder images that you can replace with real test images
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FIXTURES_DIR = Path(__file__).parent

def create_placeholder(filename: str, text: str, size: tuple = (512, 512), color: tuple = (73, 109, 137)):
    """Create a placeholder image with text"""
    img = Image.new('RGB', size, color=color)
    draw = ImageDraw.Draw(img)

    # Try to use a system font, fallback to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        except:
            font = ImageFont.load_default()

    # Center text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)

    draw.text(position, text, fill=(255, 255, 255), font=font)

    # Add instructions at bottom
    instruction_text = f"Replace this placeholder with a real {text.lower()}"
    try:
        small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except:
        small_font = font

    bbox = draw.textbbox((0, 0), instruction_text, font=small_font)
    text_width = bbox[2] - bbox[0]
    inst_position = ((size[0] - text_width) // 2, size[1] - 60)
    draw.text(inst_position, instruction_text, fill=(200, 200, 200), font=small_font)

    output_path = FIXTURES_DIR / filename
    img.save(output_path, 'JPEG', quality=95)
    print(f"✓ Created: {output_path}")
    return output_path

if __name__ == "__main__":
    print("Creating placeholder fixture images...\n")

    # Create source face placeholder
    create_placeholder(
        "source.jpg",
        "SOURCE FACE",
        size=(512, 512),
        color=(73, 109, 137)  # Blue
    )

    # Create target image placeholder
    create_placeholder(
        "target.jpg",
        "TARGET IMAGE",
        size=(512, 512),
        color=(109, 137, 73)  # Green
    )

    print("\n" + "="*60)
    print("IMPORTANT: Replace placeholder images with real test data!")
    print("="*60)
    print(f"\nFixtures directory: {FIXTURES_DIR}")
    print("\nRequired:")
    print("  - source.jpg: Image with a clear front-facing human face")
    print("  - target.jpg: Image with one or more faces to swap")
    print("\nOptional:")
    print("  - target.mp4: Short video with faces (for video tests)")
    print("\nRecommended specs:")
    print("  - Format: JPEG or PNG")
    print("  - Resolution: 512x512 or higher")
    print("  - Clear, well-lit faces")
    print("  - Front-facing poses work best")
    print("="*60)
