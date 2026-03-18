from PIL import Image, ImageDraw, ImageFont
import os

def generate_icon(size, output_path):
    """
    Generates a custom icon with a lettermark.
    """
    # Constants
    linkedin_blue = "#0A66C2"
    padding = size // 8
    radius = size // 4
    font_size = int(size * 0.55)
    letter = "R"

    # Create a transparent image
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Draw the rounded square background
    rect_coords = [(padding, padding), (size - padding, size - padding)]
    draw.rounded_rectangle(rect_coords, fill=linkedin_blue, radius=radius)

    # Select the font
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except IOError:
        print("DejaVuSans-Bold.ttf not found. Using default font.")
        font = ImageFont.load_default()

    # Calculate text position for centering
    text_bbox = draw.textbbox((0, 0), letter, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (size - text_width) / 2
    text_y = (size - text_height) / 2 - (size * 0.05) # Small vertical adjustment

    # Draw the lettermark
    draw.text((text_x, text_y), letter, font=font, fill="white")

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save the image
    img.save(output_path, "PNG")
    print(f"Generated icon at {output_path}")

if __name__ == "__main__":
    # Generate the required icons
    generate_icon(16, "extension/icons/icon16.png")
    generate_icon(48, "extension/icons/icon48.png")
    generate_icon(128, "extension/icons/icon128.png")
    
    print("\nRunning the script from the project root should place icons in 'extension/icons/'.")
