import shutil
import logging
from fastapi import FastAPI, File, HTTPException, UploadFile, Form, Request, Response
from starlette.datastructures import UploadFile as StarletteUploadFile
from fastapi.responses import JSONResponse
import shutil
import tempfile
import os
import uuid
import traceback
import json
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from main import extract_pdf, extract_assets_with_metadata
import asyncio
from fastapi.concurrency import run_in_threadpool
import re
from utils import safe_filename

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="pdf-extract")


@app.post("/extract-pdf")
async def parse_pdf_endpoint(file: UploadFile = File(...)):

    if not file.filename.lower().endswith(".pdf") or file.content_type not in ["application/pdf"]:
        raise HTTPException(
            status_code=400, detail="Only PDF files are supported.")

    # check actual file magic byte
    header = await file.read(5)
    await file.seek(0)
    if not header.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400, detail="Uploaded file is not a valid PDF (missing %PDF header).")

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
async def extract_images_endpoint(request: Request):
    logger.info("Received extract-images request.")

    # We will collect assets here
    # Structure: { asset_id: { metadata: [...], files: [path1, path2...] } }
    processed_assets = {}

    # To keep track of directories to clean up
    directories_to_clean = []

    try:
        form = await request.form()
        print(json.dumps(form, default=str))

        for asset_id, file_obj in form.items():
            print(f"Processing asset: {asset_id}")
            print(f"File object: {file_obj}")
            if not isinstance(file_obj, StarletteUploadFile):
                print(f"Skipping non-UploadFile: {asset_id}")
                continue

            filename = safe_filename(file_obj.filename)
            logger.info(f"Processing asset: {asset_id}, file: {filename}")

            if not filename.lower().endswith(".pdf"):
                logger.warning(f"Skipping non-PDF file: {filename}")
                continue

            # 1. Create specific output directory for this asset
            safe_asset_id = re.sub(r'[^a-zA-Z0-9_-]', '_', asset_id)
            base_output_dir = f"./images/{safe_asset_id}"
            if os.path.exists(base_output_dir):
                shutil.rmtree(base_output_dir)
            os.makedirs(base_output_dir, exist_ok=True)
            directories_to_clean.append(base_output_dir)

            # 2. Save uploaded PDF to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                shutil.copyfileobj(file_obj.file, tmp_pdf)
                temp_pdf_path = tmp_pdf.name

            try:
                # 3. Extract assets
                # extract_assets_with_metadata returns a list of dicts (metadata)
                pdf_processing_semaphore = asyncio.Semaphore(
                    5)  # only 5 PDFs at same time

                async with pdf_processing_semaphore:
                    metadata_list = await run_in_threadpool(
                        extract_assets_with_metadata,
                        temp_pdf_path,
                        base_output_dir
                    )

                # 4. Prepare metadata with corrected paths for multipart
                # The extracted 'path' in metadata is absolute or relative to cwd.
                # We need to map it to a content-id or relative path for the client.
                # Let's verify what main.py puts in 'path'.
                # main.py puts: f"{output_dir}/{os.path.basename(pdf_path)}_table_{page_index}_{table_index}.jpg"

                asset_files = []
                final_metadata = []

                for item in metadata_list:
                    original_path = item.get("path")
                    if original_path and os.path.exists(original_path):
                        # We'll use the filename as the key in the multipart response for simplicity
                        # format: {assetId}/{filename}
                        file_name = os.path.basename(original_path)
                        cid = f"{asset_id}/{file_name}"

                        # Update metadata path to point to this CID
                        item["path"] = cid
                        asset_files.append((cid, original_path))

                    final_metadata.append(item)

                processed_assets[asset_id] = {
                    "metadata": final_metadata,
                    "files": asset_files
                }

            except Exception as inner_e:
                logger.error(f"Error processing asset {asset_id}: {inner_e}")
                # We continue with other assets? Or fail?
                # Requirements say "Api is responsible for sending image files...".
                # We should probably continue but log error.
                continue
            finally:
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)

        # 5. Construct Multipart Response
        msg = MIMEMultipart('mixed')

        # Part 1: All Metadata Aggregated
        # We need a structure that maps assetId -> Metadata
        all_metadata = {
            aid: data["metadata"] for aid, data in processed_assets.items()
        }

        metadata_part = MIMEBase('application', 'json')
        metadata_part.set_payload(json.dumps(all_metadata))
        metadata_part.add_header(
            'Content-Disposition', 'form-data', name="metadata")
        msg.attach(metadata_part)

        # Part 2+: Files
        for aid, data in processed_assets.items():
            for cid, file_path in data["files"]:
                try:
                    with open(file_path, "rb") as f:
                        file_content = f.read()

                    # Determine mime type (simple guess)
                    mime_type = "application/octet-stream"
                    if file_path.lower().endswith((".jpg", ".jpeg")):
                        mime_type = "image/jpeg"
                    elif file_path.lower().endswith(".png"):
                        mime_type = "image/png"

                    main_type, sub_type = mime_type.split('/', 1)
                    image_part = MIMEBase(main_type, sub_type)
                    image_part.set_payload(file_content)

                    image_part.add_header(
                        'Content-Transfer-Encoding', 'binary')
                    # Content-ID is important for reference
                    image_part.add_header('Content-ID', f"<{cid}>")
                    # Also set filename in disposition
                    image_part.add_header(
                        'Content-Disposition', 'form-data', name=cid, filename=os.path.basename(file_path))

                    msg.attach(image_part)
                except Exception as e:
                    logger.error(f"Failed to attach file {file_path}: {e}")

        # 6. Return response
        return Response(content=msg.as_bytes(), media_type=msg.get_content_type())

    except Exception as e:
        logger.critical(
            f"Critical error in extract-images endpoint: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 7. Clean up output directories
        # We need to wait until response is sent.
        # But this code runs synchronously to generate bytes.
        # So we can clean up here safely after msg.as_bytes() is created.
        for d in directories_to_clean:
            if os.path.exists(d):
                try:
                    # logger.info(f"Cleaning up {d}")
                    shutil.rmtree(d)
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup {d}: {cleanup_error}")
