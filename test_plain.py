import pymupdf4llm
from pprint import PrettyPrinter

pprint = PrettyPrinter(width=200).pprint


pages_dict = pymupdf4llm.to_markdown(
    "sample-report.pdf",
    # pages=[i for i in range(20) if i > 10],
    # page_chunks=True,
    image_format="jpg",
    embed_images=True,
    # write_images=True,
    # image_path="./images",
)

with open("output.md", "w") as f:
    f.write(pages_dict)
