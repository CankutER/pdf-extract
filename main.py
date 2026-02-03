import pymupdf
import json
import re
import pymupdf4llm
from pprint import PrettyPrinter
from utils import scan_image_labels
from utils import scan_table_labels
from utils import is_capitalized_or_uppercase
from extract_images_to_md import save_images_to_md, ensure_dir
import pymupdf
import os

pprint = PrettyPrinter(width=200).pprint


def extract_pdf(pdf_path: str):

    pages_dict = pymupdf4llm.to_markdown(
        pdf_path,
        page_chunks=True,
        image_format="png",
        embed_images=True,
    )

    sections = []
    current_header = "Document Start"
    current_section = {"header": current_header,
                       "content": [], "images": [], "tables": [], "pages": []}

    for page_index, page in enumerate(pages_dict, start=1):
        md = page["text"]
        md = re.sub(r'\n\s*\n+', '\n\n', md)
        md = re.sub(r'(data:image/[a-zA-Z]+;base64,[A-Za-z0-9+/=\n]+)',
                    lambda m: m.group(1).replace("\n", ""),
                    md)
        lines = md.splitlines()
        cleaned_lines = []

        # Collapse consecutive blank lines
        for line in lines:
            if line.strip():
                cleaned_lines.append(line)
            elif cleaned_lines and cleaned_lines[-1].strip():
                cleaned_lines.append("")

        lines = cleaned_lines
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # HEADER EXTRACTION
            header_match = (
                # md headers
                re.match(r'^(#{1,6})\s+(.*)', line)
                # bold lines
                or re.match(r'^\*\*(.+?)\*\*$', line.strip())
                # enumerated headers (bold or not)
                or re.match(r'^\**\s*\d+(\.\d+)*\.*\s+(.+)', line.strip())
            )

            if header_match:
                header_text = header_match.group(0)
                header_text = re.sub(r'^(#{1,6})\s+', '', header_text)
                header_text = re.sub(r'^\**|\**$', '', header_text).strip()

                # Word number and casing filter
                if not is_capitalized_or_uppercase(header_text):
                    i += 1
                    continue

                # Merge headers if word wrap failed while exporting to md
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if (
                        re.match(r'^(#{1,6})\s+', next_line)
                        or re.match(r'^\*\*(.+?)\*\*$', next_line)
                        or re.match(r'^\**\s*\d+(\.\d+)*\.*\s+(.+)', next_line)
                        or not next_line
                    ):
                        break
                    header_text += " " + next_line
                    j += 1

                header_text = re.sub(r'\*+', '', header_text).strip()

                # Save previous section
                content_merged = "\n".join(current_section["content"])
                if content_merged or len(current_section["images"]) > 0 or len(current_section["tables"]) > 0:
                    current_section["content"] = content_merged
                    sections.append(current_section)

                current_section = {
                    "header": header_text,
                    "content": [],
                    "images": [],
                    "tables": [],
                    "pages": [page_index],
                }

                i = j
                continue

            # IMAGE EXTRACTION
            image_match = re.match(
                r'!\[(.*?)\]\(data:image\/[a-zA-Z]+;base64,([^)]+)\)', line)
            if image_match:
                alt_text = image_match.group(1).strip()
                image_b64 = image_match.group(2)

                label_text = scan_image_labels(lines, i)
                current_section["images"].append({
                    "alt": alt_text or label_text or "Untitled",
                    "label": label_text or "",
                    "data": image_b64,
                    "page": page_index,
                })
                i += 1
                continue

            # TABLE EXTRACTION
            if re.match(r'^\|.+\|$', line):
                table_lines = [line]
                j = i + 1
                continued = False
                while j < len(lines) and re.match(r'^\|.+\|$', lines[j]):
                    continued = True
                    table_lines.append(lines[j])
                    j += 1
                table_markdown = "\n".join(table_lines)
                if continued:
                    table_label = scan_table_labels(lines, i, j)
                    current_section["tables"].append({
                        "table_markdown": table_markdown,
                        "page": page_index,
                        "label": table_label or ""
                    })

                i = j
                continue

            # TEXT EXTRACTION
            current_section["content"].append(line)
            if page_index not in current_section["pages"]:
                current_section["pages"].append(page_index)
            i += 1

    # Save last section
    content_merged = "\n".join(current_section["content"])
    if content_merged or len(current_section["images"]) > 0 or len(current_section["tables"]) > 0:
        current_section["content"] = content_merged
        sections.append(current_section)

    return sections


# sections=extract_pdf("sample-report")

# save_images_to_md(sections=sections)

# with open("output.json", "w") as f:
#    f.write(json.dumps(sections))
# for section in sections:
#     pprint(section)


def extract_images(pdf_path, output_dir):
    ensure_dir(output_dir)
    doc = pymupdf.open(pdf_path)
    pages_dict = pymupdf4llm.to_markdown(
        doc,
        page_chunks=True,
        image_format="jpg",
        write_images=True,
        image_path=output_dir,
        image_size_limit=0.1,
        dpi=300
    )
    for page_index, page in enumerate(pages_dict):
        tables = page.get("tables")
        for table_index, table in enumerate(tables):
            table_bbox = table.get("bbox")
            docPage = doc[page_index]
            docPage.get_pixmap(clip=table_bbox, dpi=300).save(
                f"{output_dir}/{os.path.basename(pdf_path)}_table_{page_index}_{table_index}.jpg")

# extract_images("sample-report.pdf", "./training/1/images")


def extract_assets_with_metadata(pdf_path, output_dir):
    file_name = os.path.basename(pdf_path)
    ensure_dir(output_dir)
    doc = pymupdf.open(pdf_path)
    pages_dict = pymupdf4llm.to_markdown(
        doc,
        page_chunks=True,
        image_format="jpg",
        write_images=True,
        image_path=output_dir,
        image_size_limit=0.05,
        dpi=300,
        graphics_limit=0
    )
    # We trust table index here will match table detection order found while parsing lines
    table_counter = 0
    table_paths = []
    for page_index, page in enumerate(pages_dict):
        tables = page.get("tables")
        for table_index, table in enumerate(tables):
            table_bbox = table.get("bbox")
            docPage = doc[page_index]
            docPage.get_pixmap(clip=table_bbox, dpi=300).save(
                f"{output_dir}/{os.path.basename(pdf_path)}_table_{page_index}_{table_index}.jpg")
            table_paths.append(
                f"{output_dir}/{os.path.basename(pdf_path)}_table_{page_index}_{table_index}.jpg")

    images_lib = []
    for page_index, page in enumerate(pages_dict, start=1):
        md = page["text"]
        # print("------------PRINTING TEXT------------")
        # print(md)
        lines = clear_md(md)
        # print("------------PRINTING LINES------------")
        # print(lines)
        i = 0
        line_accumulator = []
        while i < len(lines):

            line = lines[i].rstrip()
            # print("------------PRINTING SINGLE LINE------------")
            # print(line)
            # print(line_accumulator)

            # Detect if line refers to image reference, like ![](./images/sample-report.pdf-3-0.jpg)
            pattern = re.compile(
                rf'!\[[^\]]*\]\(\s*'
                rf'(?P<path>{re.escape(output_dir)}/'
                rf'{re.escape(file_name)}-\d+-\d+\.(?:png|jpg|jpeg|webp))'
            )

            match = pattern.search(line)

            if match:
                full_path = match.group("path")
                label_text = scan_image_labels(lines, i)
                text_before = "\n".join(line_accumulator)
                images_lib.append({
                    "label": label_text or "",
                    "path": full_path,
                    "page": page_index,
                    "text_before": text_before or "\n".join(lines),
                    "type": "visual"
                })
                # print("Image path:", full_path)
                line_accumulator = []
                i += 1
                continue

           # Detect if line starts a table, leap over it if exists
            table_row_pattern = re.compile(r'^\s*\|.*\|\s*$')

            if re.match(table_row_pattern, line):
                table_lines = [line]
                j = i + 1
                while j < len(lines) and re.match(table_row_pattern, lines[j]):
                    table_lines.append(lines[j])
                    j += 1

                # More than 1 line verifies table
                if len(table_lines) > 1:
                    table_label = scan_table_labels(lines, i, j)
                    table_path = table_paths[table_counter]
                    table_counter += 1
                    images_lib.append({
                        "label": table_label or "",
                        "path": table_path,
                        "page": page_index,
                        "text_before": "\n".join(line_accumulator) or "\n".join(lines),
                        "type": "table"
                    })
                    line_accumulator = []
                i = j
                continue

            line_accumulator.append(line)
            i += 1

    return process_visual_context(images_lib)


def clear_md(md):
    md = re.sub(r'\n\s*\n+', '\n\n', md)
    lines = md.splitlines()
    cleaned_lines = []

    # Collapse consecutive blank lines
    for line in lines:
        if line.strip():
            cleaned_lines.append(line)
        elif cleaned_lines and cleaned_lines[-1].strip():
            cleaned_lines.append("")
    return cleaned_lines


def process_visual_context(items, max_chars=750):
    """
    - Backfills empty text_before from previous item on same page
    - Truncates long text into start...middle...end form
    """

    def smart_truncate(text, max_chars):
        text = text.strip()
        if len(text) <= max_chars:
            return text

        part = max_chars // 3
        start = text[:part].strip()
        middle_start = len(text)//2 - part//2
        middle = text[middle_start: middle_start + part].strip()
        end = text[-part:].strip()

        return f"{start} ...truncated... {middle} ...truncated... {end}"

    last_text_by_page = {}

    for item in items:
        page = item.get("page")
        text = (item.get("text_before") or "").strip()

        #  TRUNCATE
        if text:
            truncated_text = smart_truncate(text, max_chars)
            item["text_before"] = truncated_text
            last_text_by_page[page] = truncated_text

        #  BACKFILL
        if not text:
            if page in last_text_by_page:
                text = last_text_by_page[page]
                item["text_before"] = text

    return items


# images_lib = extract_assets_with_metadata(
 #   "sample-report.pdf", "./training/2/images")
# with open("output.json", "w") as f:
 #   f.write(json.dumps(images_lib, default=str))
