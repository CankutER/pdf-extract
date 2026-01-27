from fastapi.testclient import TestClient
from api import app
import os
import shutil
import zipfile

client = TestClient(app)

def test_extract_images():
    training_id = "test_run_123"
    pdf_path = "sample-report.pdf"
    
    # Ensure clean state
    output_dir = f"./training/{training_id}/images"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
        
    assert os.path.exists(pdf_path), f"{pdf_path} not found"

    print("Sending request...")
    with open(pdf_path, "rb") as f:
        files = [
            ("files", (os.path.basename(pdf_path), f, "application/pdf")),
            # Send duplicate to test unique handling or multiple files? 
            # Request says "Api resource will accept ... multiple binary files". 
            # Let's send the same file twice to verify list handling and naming.
            ("files", ("copy_" + os.path.basename(pdf_path), open(pdf_path, "rb"), "application/pdf"))
        ]
        
        response = client.post(
            "/extract-images",
            data={"training_id": training_id},
            files=files
        )

    print(f"Response status: {response.status_code}")
    if response.status_code != 200:
        print(response.text)
        
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    
    # Save zip
    zip_filename = f"images_{training_id}.zip"
    with open(zip_filename, "wb") as f:
        f.write(response.content)
        
    print(f"Saved {zip_filename}")
    
    # Verify zip content
    with zipfile.ZipFile(zip_filename, 'r') as z:
        file_list = z.namelist()
        print(f"Files in zip: {file_list}")
        assert len(file_list) > 0
        
        # Verify naming (prefix) in ZIP
        # We sent "sample-report.pdf" and "copy_sample-report.pdf"
        
        has_original_prefix = any(f.startswith("sample-report.pdf_") for f in file_list)
        has_copy_prefix = any(f.startswith("copy_sample-report.pdf_") for f in file_list)
        
        assert has_original_prefix, f"Mising prefix 'sample-report.pdf_' in {file_list}"
        assert has_copy_prefix, f"Missing prefix 'copy_sample-report.pdf_' in {file_list}"

    # Verify cleanup
    assert not os.path.exists(output_dir), f"Directory {output_dir} should have been cleaned up"

    print("Test passed!")

if __name__ == "__main__":
    test_extract_images()
