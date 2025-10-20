import pymupdf4llm
from pprint import PrettyPrinter

pprint= PrettyPrinter(width=200).pprint


pages_dict = pymupdf4llm.to_markdown(
        "sample-report.pdf",
        pages=[i for i in range(20) if i > 10],
        page_chunks=True,
        image_format="png",
        embed_images=True,
        # write_images=True,
    )

pprint(pages_dict)