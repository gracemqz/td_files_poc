import os
from google.cloud import storage
from vertexai.generative_models import GenerativeModel, Part
import vertexai
from datetime import datetime
import tempfile
import json
from google.oauth2 import service_account

# Google Cloud configuration
GOOGLE_CLOUD_PROJECT_ID = "semantic-intelligent-sap"
GOOGLE_CLOUD_BUCKET_NAME = "source_to_jira_bucket"
GOOGLE_CLOUD_LOCATION = "us-central1"


DEFAULT_PROMPT = """You are a payroll administrator. Step 1:Parse the pdf file(s) and list all the fields in the form with the values input by the employee for that field. Double check and make sure the values are parsed correctly, and are matched with the correct field, don't miss any value and do not mismatch any value with the incorrect field. Output in a table format. Note: Also include all fields and checkboxes (even if they are blank) with the values in the checkboxes (if there's a tick or not).
        Step 2: Check if the amounts entered from line 1 to the last line before the "total claim amount" line sum up to the "total claim amount".
        Step 3: List whether this a federal or provincial form, if it's a federal form, list for which country it is applicable for; if it's a provincial form, list for which province or state that it is applicable for. Also, list the year it is for."""


def init_google_cloud(credentials_json):
    """Initialize Google Cloud services with provided credentials."""
    try:
        # Create credentials object
        credentials = service_account.Credentials.from_service_account_info(
            credentials_json, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )

        # Initialize Vertex AI with credentials
        vertexai.init(
            project=GOOGLE_CLOUD_PROJECT_ID,
            location=GOOGLE_CLOUD_LOCATION,
            credentials=credentials,
        )

        # Initialize storage client with credentials
        storage_client = storage.Client(
            project=GOOGLE_CLOUD_PROJECT_ID, credentials=credentials
        )

        # Initialize Gemini model
        model = GenerativeModel("gemini-2.0-flash-001")

        return storage_client, model
    except Exception as e:
        raise Exception(f"Failed to initialize Google Cloud services: {str(e)}")


def upload_to_gcs(file_content, storage_client, bucket_name=GOOGLE_CLOUD_BUCKET_NAME):
    """Upload a file to Google Cloud Storage and return the public URL."""
    try:
        bucket = storage_client.bucket(bucket_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        blob_name = f"form_{timestamp}.pdf"
        blob = bucket.blob(blob_name)

        # Create a temporary file to store the content
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file_content.read())
            temp_file.seek(0)

            # Upload the file to GCS
            blob.upload_from_filename(temp_file.name)

        # Clean up the temporary file
        os.unlink(temp_file.name)

        # Get the public URL
        return f"gs://{bucket_name}/{blob_name}"
    except Exception as e:
        raise Exception(f"Error uploading to GCS: {str(e)}")


def process_pdf_with_gemini(file_url, model, prompt=DEFAULT_PROMPT):
    """Process a single PDF with Gemini model."""
    try:
        # Create a PDF part from the GCS URL
        pdf_part = Part.from_uri(file_url, mime_type="application/pdf")

        # Generate content with safety settings
        response = model.generate_content(
            [prompt, pdf_part],
            generation_config={
                "temperature": 0.0,
                "top_p": 1.0,
                "top_k": 1,
                "max_output_tokens": 2048,
            },
        )

        return response.text
    except Exception as e:
        raise Exception(f"Error processing PDF with Gemini: {str(e)}")


def process_multiple_pdfs(gcs_urls, model, prompt=DEFAULT_PROMPT):
    """Process multiple PDFs and combine their results."""
    results = []
    for url in gcs_urls:
        try:
            result = process_pdf_with_gemini(url, model, prompt)
            results.append(result)
        except Exception as e:
            results.append(f"Error processing file {url}: {str(e)}")

    return "\n\n---\n\n".join(results)
