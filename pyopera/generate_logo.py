from io import BytesIO
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFont


# Cached function to generate the logo with a transparent background
@st.cache_resource
def generate_text_image(
    text: str,
    font_path: Path,
    font_size: int = 50,
    width: int = 400,
    height: int = 200,
) -> BytesIO:
    font_path = Path(font_path)

    image = Image.new(
        "RGBA", (width, height), (255, 255, 255, 0)
    )  # (R, G, B, A) - A=0 means fully transparent
    draw = ImageDraw.Draw(image)

    # Load the font
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        st.error("Font not found. Please check the font path.")
        return None

    # Calculate text size using textbbox
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Position the text in the center
    text_position = ((width - text_width) / 2, (height - text_height) / 2)

    # Draw the text in black (or any other color you prefer)
    draw.text(text_position, text, font=font, fill="black")

    # Save the image to a BytesIO object
    logo_bytes = BytesIO()
    image.save(logo_bytes, format="PNG")
    logo_bytes.seek(0)

    return logo_bytes


def load_font_path():
    return Path(__file__).parent.parent / "assets" / "SourceSans3-Bold.ttf"


def generate_logo() -> BytesIO:
    # Load the font path
    font_path = load_font_path()

    # Generate the logo with the specified text and font
    logo_bytes = generate_text_image(
        text="OperArchive",
        font_path=font_path,
        font_size=100,  # Adjust this value as needed
        width=550,  # Adjust this value as needed
        height=160,  # Adjust this value as needed
    )

    return logo_bytes
