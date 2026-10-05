"""
Script to generate a realistic product label image for testing Node 3: AI / Image Scan.
Uses Pillow (PIL) to render barcode and text.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

output_dir = Path(__file__).resolve().parent
output_path = output_dir / "artisan_cheese_label.png"

# Create a clean white card image
width, height = 600, 350
img = Image.new("RGB", (width, height), color=(255, 255, 255))
draw = ImageDraw.Draw(img)

# Border
draw.rectangle([10, 10, width - 10, height - 10], outline=(40, 40, 40), width=3)
draw.rectangle([20, 20, width - 20, 80], fill=(230, 240, 255))

# Header / Product Name
draw.text((35, 35), "ORGANIC ARTISAN CHEDDAR CHEESE 250G", fill=(10, 30, 80))

# Metadata
draw.text((35, 100), "PRODUCT OF NEW ZEALAND | 100% GRASS FED", fill=(90, 90, 90))
draw.text((35, 130), "SKU / LOT NUMBER: SKU-CHD-9021", fill=(0, 0, 0))
draw.text((35, 160), "EXPIRATION DATE: 2026-10-25", fill=(180, 0, 0))
draw.text((35, 190), "NET QUANTITY: 6 UNITS PER CASE", fill=(0, 0, 0))

# Simulated barcode lines
barcode_top = 230
barcode_bottom = 300
start_x = 35
for i in range(45):
    line_w = 2 if (i % 3 != 0) else 5
    draw.line([(start_x, barcode_top), (start_x, barcode_bottom)], fill=(0, 0, 0), width=line_w)
    start_x += line_w + 3

draw.text((start_x + 20, 250), "* 8 9 0 1 2 4 4 9 0 2 1 *", fill=(60, 60, 60))

img.save(str(output_path))
print(f"Sample label image generated at: {output_path}")
