from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os
import uuid
import traceback
from main import extract_pdf
app = FastAPI(title="pdf-extract")

@app.post("/extract-pdf")
async def parse_pdf_endpoint(file: UploadFile = File(...)):
 
    if not file.filename.lower().endswith(".pdf") or file.content_type not in ["application/pdf"]:
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    #check actual file magic byte
    header = await file.read(5)
    await file.seek(0)
    if not header.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF (missing %PDF header).")
    
    # save to temp file with unique name
    temp_filename = f"{uuid.uuid4()}.pdf"
    temp_path = os.path.join(tempfile.gettempdir(), temp_filename)

    try:
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        result = extract_pdf(temp_path)

        return JSONResponse(content=result)

    except Exception as e:
        print("Error while parsing PDF:\n", traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Internal error occurred while processing the file: {str(e)}"
        )
    finally:
        # Remove temp file at the end
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass  
