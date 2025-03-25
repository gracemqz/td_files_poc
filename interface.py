import json

import streamlit as st

from generation import (
    DEFAULT_PROMPT,
    init_google_cloud,
    process_multiple_pdfs,
    upload_to_gcs,
)


@st.dialog("Google Cloud and Vertex AI Credentials")
def show_credentials_dialog():
    credentials_text = st.text_area(
        "Paste your Google Cloud and Vertex AI credentials (JSON) here",
        height=200,
        help="This should be a JSON file containing your Google Cloud and Vertex AI credentials",
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Load Credentials", use_container_width=True, type="primary"):
            if credentials_text:
                try:
                    credentials_json = json.loads(credentials_text)
                    st.session_state.credentials = credentials_json
                    st.session_state.credentials_provided = True
                    st.rerun()
                except json.JSONDecodeError:
                    st.error("Invalid JSON format. Please check your credentials.")
                    st.session_state.credentials_provided = False
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("Modify Analysis Prompt")
def show_prompt_dialog():
    if "custom_prompt" not in st.session_state:
        st.session_state.custom_prompt = DEFAULT_PROMPT

    modified_prompt = st.text_area(
        "Customize the analysis prompt",
        value=st.session_state.custom_prompt,
        height=200,
        help="Modify the prompt that will be used to analyze the PDF files",
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Update Prompt", use_container_width=True, type="primary"):
            st.session_state.custom_prompt = modified_prompt
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


def main():
    st.set_page_config(page_title="Employee Tax Forms Assistant", page_icon="🗂")

    # Custom CSS for buttons
    st.markdown(
        """
        <style>
        .stButton button {
            background-color: #006BB8 !important;
            border-color: #006BB8 !important;
            color: white !important;
        }
        .stButton button:hover {
            background-color: #005a9e !important;
            border-color: #005a9e !important;
            color: white !important;
        }
        .stButton button:active, .stButton button:focus {
            background-color: #006BB8 !important;
            border-color: #006BB8 !important;
            color: white !important;
            box-shadow: none !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    st.title("🗂 Employee Tax Forms Assistant")

    # Dialog toggle buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Configure Credentials", use_container_width=True):
            show_credentials_dialog()
    with col2:
        if st.button("Modify Analysis Prompt", use_container_width=True):
            show_prompt_dialog()

    # Show credentials dialog automatically if not provided
    if not st.session_state.get("credentials_provided", False):
        show_credentials_dialog()
        st.warning(
            "Please provide your Google Cloud and Vertex AI credentials to continue."
        )
        return

    uploaded_files = st.file_uploader(
        "Upload PDF files",
        type="pdf",
        accept_multiple_files=True,
    )

    if uploaded_files:
        if st.button("Process Form", type="primary", use_container_width=True):
            with st.spinner("Processing the form..."):
                try:
                    # Initialize Google Cloud services with provided credentials
                    storage_client, model = init_google_cloud(
                        st.session_state.credentials
                    )

                    # Upload files to GCS and get URLs
                    gcs_urls = []
                    for pdf_file in uploaded_files:
                        gcs_url = upload_to_gcs(pdf_file, storage_client)
                        gcs_urls.append(gcs_url)

                    # Process PDFs with Gemini
                    results = process_multiple_pdfs(
                        gcs_urls, model, st.session_state.custom_prompt
                    )

                    # Display results
                    st.subheader("Analysis")
                    st.markdown(results)

                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.error("Please check your credentials and try again.")


if __name__ == "__main__":
    main()
