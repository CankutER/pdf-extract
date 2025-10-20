## PDF Extraction Tool

### Features
This tool aims to parse and extract data from pdf files to feed LLMs and potentially RAG applications. Text content, headers, images and tables are extracted and presented in a structured manner. Extracted data is represented as an array of sections, where each section consist of the data in above formats under a header, where headers are attempted to be detected with a naive approach. Such header based chunking approach is utilized in order to semantically ground each section and different data formats inside.

Detection of headers, image and table labels are naively implemented. Quality of the resulting output heavily depends on how the pdf is formatted  and it may not represent the pdf layout fully. Even though regular use cases somewhat gave acceptable results, there will be some edge cases.

### Run the application
Application is served as a Fast API endpoint for convenience, docker compose file is also included.

```bash
cd pdf-extract
docker compose up
```
If you do not wish to use docker;

```bash
cd pdf-extract
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn api:app
```
API should be available at localhost:8000/extract-pdf

A POST request should be made to endpoint as multipart/form-data with key 'file'.

Example curl:
```bash
curl --request POST \
  --url http://localhost:8000/extract-pdf \
  --header 'content-type: multipart/form-data' \
  --form file=@<path-to-file>
```
If you wish to save output of the curl to a file:
```bash
curl --request POST \
  --url http://localhost:8000/extract-pdf \
  --header 'content-type: multipart/form-data' \
  --form file=@<path-to-file> -o output.json
```

Additionally, it is always possible to modify the file path in main py and directly run the code.

```python
sections=extract_pdf("multi-column.pdf")

for section in sections:
    pprint(section)
```

I have included two sample files in the repository for testing, they also have some edge cases where output is negatively affected. 

### Response Structure

```json
[
  {
      "header": "Naively detected header of the section,str",
      "content": "text extracted from section,str",
      "images": [ {
        "alt": "Alternative text to image if exists,str",
        "label": "Naively detected label/annotation of the image,str",
        "data": "base64 encoded string of the image,str",
        "page": "page number of the image,int" 
      }],
      "tables": [{
        "table_markdown": "table text separated by |,str",
        "page": "page number of the table,int" ,
        "label": "Naively detected label/annotation of the image,str"
      }],
      "pages": ["number of","pages this section","covers"]
    }
]
  ```
  