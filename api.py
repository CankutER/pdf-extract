import shutil
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List
import zipfile
import io
import shutil
import tempfile
import os
import uuid
import traceback
from main import extract_pdf, extract_images

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        logger.error(f"Error while parsing PDF:\n{traceback.format_exc()}")
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

@app.post("/extract-images")
async def extract_images_endpoint(
    training_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    logger.info(f"Received extract-images request. Training ID: {training_id}, Files: {len(files)}")
    
    # Define base output directory
    base_output_dir = f"./training/{training_id}/images"
    os.makedirs(base_output_dir, exist_ok=True)

    # List to track all extracted image paths for zipping
    extracted_images_paths = []

    try:
        # Temporary directory for processing this request
        with tempfile.TemporaryDirectory() as temp_extract_root:
            for file in files:
                logger.info(f"Processing file: {file.filename}")
                if not file.filename.lower().endswith(".pdf"):
                    logger.warning(f"Skipping non-PDF file: {file.filename}")
                    continue 

                # Save uploaded file to temp
                temp_pdf_path = os.path.join(temp_extract_root, f"temp_{uuid.uuid4()}.pdf")
                try:
                    with open(temp_pdf_path, "wb") as f:
                        f.write(await file.read())
                    
                    pdf_temp_output_dir = os.path.join(temp_extract_root, f"out_{uuid.uuid4()}")
                    os.makedirs(pdf_temp_output_dir, exist_ok=True)
                    
                    extract_images(temp_pdf_path, pdf_temp_output_dir)
                    
                    # Move and rename images
                    safe_filename = os.path.basename(file.filename)
                    
                    files_in_output = os.listdir(pdf_temp_output_dir)
                    logger.info(f"Extracted {len(files_in_output)} images/tables from {file.filename}")

                    for img_name in files_in_output:
                        src_path = os.path.join(pdf_temp_output_dir, img_name)
                        if os.path.isfile(src_path):
                            # Check if main.py already prefixed the filename (it does for tables now)
                            # If img_name starts with safe_filename, assume it's already prefixed.
                            if img_name.startswith(safe_filename):
                                new_name = img_name
                            else:
                                new_name = f"{safe_filename}_{img_name}"
                            
                            dest_path = os.path.join(base_output_dir, new_name)
                            shutil.copy2(src_path, dest_path) 
                            extracted_images_paths.append(dest_path)

                except Exception as e:
                    logger.error(f"Error processing file {file.filename}: {e}\n{traceback.format_exc()}")

        # Create ZIP file
        logger.info(f"Creating ZIP file with {len(extracted_images_paths)} images...")
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in extracted_images_paths:
                zip_file.write(file_path, arcname=os.path.basename(file_path))
        
        zip_buffer.seek(0)
        logger.info("ZIP file created successfully.")
        
        return StreamingResponse(
            zip_buffer, 
            media_type="application/zip", 
            headers={"Content-Disposition": f"attachment; filename=images_{training_id}.zip"}
        )

    except Exception as e:
        logger.critical(f"Critical error in extract-images endpoint: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Cleanup base output directory
        if os.path.exists(base_output_dir):
            logger.info(f"Cleaning up output directory: {base_output_dir}")
            try:
                shutil.rmtree(base_output_dir.split("/images")[0])            
            except Exception as e:
                logger.error(f"Error cleaning up output directory: {e}")
