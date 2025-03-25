import json

import streamlit as st

from generation import (
    DEFAULT_PROMPT,
    init_google_cloud,
    process_multiple_pdfs,
    upload_to_gcs,
)


@st.dialog("Modify Prompt")
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

    # Initialize credentials from secrets
    if "credentials" not in st.session_state:
        try:
            credentials_json = json.loads(st.secrets["google_credentials"])
            st.session_state.credentials = credentials_json
            st.session_state.credentials_provided = True
        except Exception as e:
            st.error(f"Error loading credentials from secrets: {str(e)}")
            st.session_state.credentials_provided = False
            return

    # Dialog toggle button for prompt
    if st.button("Modify Prompt", use_container_width=True):
        show_prompt_dialog()

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
