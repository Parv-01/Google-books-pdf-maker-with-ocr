import re
import subprocess
import os
from pathlib import Path
from PIL import Image, UnidentifiedImageError
import img2pdf

#config

IMAGE_FOLDER = Path("images")
TEMP_PDF = Path("temp_merged.pdf")
FINAL_PDF = Path("book name.pdf")

LANGUAGE = "eng"             # e.g. "eng+deu"
OUTPUT_TYPE = "pdfa"         # "pdf" or "pdfa"
OCR_JOBS = str(max(1, os.cpu_count() // 2))

def natural_sort_key(path):
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r'([0-9]+)', path.name)
    ]

def extract_page_number(filename):
    match = re.search(r'(\d+)', filename)
    return int(match.group(1)) if match else None

def get_valid_images(folder):
    images = []
    page_numbers = []

    for file in folder.iterdir():
        if file.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            try:
                Image.open(file).verify()
                images.append(file)

                num = extract_page_number(file.name)
                if num is not None:
                    page_numbers.append(num)

            except UnidentifiedImageError:
                print(f"Skipping corrupted image: {file.name}")

    if not images:
        return []

    images_sorted = sorted(images, key=natural_sort_key)

    # detect missing numeric gaps
    if page_numbers:
        page_numbers = sorted(page_numbers)
        missing = [
            i for i in range(page_numbers[0], page_numbers[-1] + 1)
            if i not in page_numbers
        ]
        if missing:
            print("Missing page numbers detected:", missing)

    return images_sorted


def merge_images_lossless(images):
    print("Merging images (lossless)...")

    image_paths = [str(img) for img in images]

    with TEMP_PDF.open("wb") as f:
        img2pdf.convert(image_paths, outputstream=f)

    print("Images merged successfully.")


def run_ocr():
    print("Running OCR...")

    command = [
        "ocrmypdf",
        "--force-ocr",
        "--optimize", "3",
        "--deskew",
        "--clean",
        "--clean-final",
        "--rotate-pages",
        "--rotate-pages-threshold", "5",
        "--language", LANGUAGE,
        "--output-type", OUTPUT_TYPE,
        "--jobs", OCR_JOBS,
        str(TEMP_PDF),
        str(FINAL_PDF)
    ]

    try:
        subprocess.run(command, check=True)
        print("OCR complete.")
        return True
    except subprocess.CalledProcessError as e:
        print("OCR failed:", e)
        return False


def main():

    if not IMAGE_FOLDER.exists():
        print("Image folder not found.")
        return

    images = get_valid_images(IMAGE_FOLDER)

    if not images:
        print("No valid images found.")
        return

    print(f"Found {len(images)} valid images.")
    print(f"Using {OCR_JOBS} parallel OCR jobs.")

    merge_images_lossless(images)
    
    success = run_ocr()
    
    if success:
        if TEMP_PDF.exists():
            TEMP_PDF.unlink()
        print(f"\nFinal PDF created:\n{FINAL_PDF}")
    else:
        print("\nOCR failed. Temporary merged PDF kept for inspection.")

if __name__ == "__main__":
    main()
