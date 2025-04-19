from PIL import Image
import os

# Configuration
INPUT_FOLDER = "cards_raw"         # folder with original card images
OUTPUT_FOLDER = "cards_resized"    # where resized images will be saved
TARGET_SIZE = (60, 94)             # width x height

# Create output folder if it doesn't exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Go through all files in the input folder
for filename in os.listdir(INPUT_FOLDER):
    if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
        continue  # skip non-image files

    input_path = os.path.join(INPUT_FOLDER, filename)
    output_path = os.path.join(OUTPUT_FOLDER, os.path.splitext(filename)[0] + ".png")

    try:
        with Image.open(input_path) as img:
            resized = img.resize(TARGET_SIZE, Image.LANCZOS)
            resized.save(output_path, format="PNG")
            print(f"✔ Saved: {output_path}")
    except Exception as e:
        print(f"⚠ Error processing {filename}: {e}")
