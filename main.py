import re
import pymupdf4llm
from pprint import PrettyPrinter
from utils import scan_image_labels
from utils import scan_table_labels
from utils import is_capitalized_or_uppercase

pprint= PrettyPrinter(width=200).pprint

def extract_pdf(pdf_path: str):

    pages_dict = pymupdf4llm.to_markdown(
        pdf_path,
        page_chunks=True,
        image_format="png",
        embed_images=True,
    )

    sections = []
    current_header = "Document Start"
    current_section = {"header": current_header, "content": [], "images": [], "tables": [], "pages": []}

    for page_index, page in enumerate(pages_dict, start=1):
        md=page["text"]
        md=re.sub(r'\n\s*\n+', '\n\n', md)
        md = re.sub( r'(data:image/[a-zA-Z]+;base64,[A-Za-z0-9+/=\n]+)',
                    lambda m: m.group(1).replace("\n", ""),
                     md)
        lines = md.splitlines()
        cleaned_lines = []
        
        #Collapse consecutive blank lines
        for line in lines:
            if line.strip():
                cleaned_lines.append(line)
            elif cleaned_lines and cleaned_lines[-1].strip():
                cleaned_lines.append("") 

        lines=cleaned_lines
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # HEADER EXTRACTION
            header_match = (
                #md headers
                re.match(r'^(#{1,6})\s+(.*)', line)   
                #bold lines             
                or re.match(r'^\*\*(.+?)\*\*$', line.strip())      
                #enumerated headers (bold or not)      
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
                content_merged="\n".join(current_section["content"])
                if content_merged or len(current_section["images"])>0 or len(current_section["tables"])>0:
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
            image_match = re.match(r'!\[(.*?)\]\(data:image\/[a-zA-Z]+;base64,([^)]+)\)', line)
            if image_match:
                alt_text = image_match.group(1).strip()
                image_b64 = image_match.group(2)

                label_text=scan_image_labels(lines,i)
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
                continued=False
                while j < len(lines) and re.match(r'^\|.+\|$', lines[j]):
                    continued=True
                    table_lines.append(lines[j])
                    j += 1
                table_markdown = "\n".join(table_lines)
                if continued:
                    table_label=scan_table_labels(lines,i,j)
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
    content_merged="\n".join(current_section["content"])
    if content_merged or len(current_section["images"])>0 or len(current_section["tables"])>0:
        current_section["content"] = content_merged
        sections.append(current_section)

    return sections


# sections=extract_pdf("multi-column.pdf")

# for section in sections:
#     pprint(section)