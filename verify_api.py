import requests
import os
import json


def verify_api():
    url = "http://localhost:8000/extract-images"

    # Using list of tuples for multiple files with different keys
    files = [
        ("asset_1", ("sample-report.pdf",
         open("sample-report.pdf", "rb"), "application/pdf"))
    ]

    try:
        response = requests.post(url, files=files)

        if response.status_code == 200:
            print("Response Status: 200 OK")

            content_type = response.headers.get("Content-Type", "")
            print(f"Content-Type: {content_type}")

            # Basic check for multipart boundary
            if "boundary=" in content_type:
                print("Multipart boundary found.")

            # Print a snippet to verify binary (non-printable chars shouldn't crash it, but printing bytes is safe)
            print("Response content first 300 bytes (raw):",
                  response.content)

            # Check if we can find Content-Transfer-Encoding: binary
            if b"Content-Transfer-Encoding: binary" in response.content:
                print("SUCCESS: Found 'Content-Transfer-Encoding: binary'")
            else:
                print(
                    "WARNING: Did not find 'Content-Transfer-Encoding: binary' header in body")

        else:
            print(f"Failed: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists("dummy1.pdf"):
            os.remove("dummy1.pdf")
        if os.path.exists("dummy2.pdf"):
            os.remove("dummy2.pdf")


if __name__ == "__main__":
    verify_api()
