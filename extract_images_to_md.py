import base64
import os

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def save_images_to_md(sections,images_path=None,md_path=None):
    OUTPUT_FOLDER = images_path or "extracted_images" 
    OUTPUT_MD = md_path or "all_images.md"
    md_lines = ["# Extracted Images (Base64 Embedded)\n"]

    ensure_dir(OUTPUT_FOLDER)
    image_counter = 1

    for section in sections:
        images = section.get("images", [])
        for img in images:
            b64 = img.get("data")
            alt = img.get("alt", "")
            label = img.get("label", "")
            page = img.get("page", "")

            # Save image file
            filename = f"image_{image_counter}.png"
            filepath = os.path.join(OUTPUT_FOLDER, filename)

            with open(filepath, "wb") as out:
                out.write(base64.b64decode(b64))

            # Add to markdown
            md_lines.append(f"## Image {image_counter}")
            if label:
                md_lines.append(f"**Label:** {label}")
            if page:
                md_lines.append(f"**Page:** {page}")
            md_lines.append(f"![{alt}]({filepath})\n")

            image_counter += 1

    # Write markdown
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
