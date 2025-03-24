import streamlit as st
import json
from generation import upload_to_gcs, process_multiple_pdfs, init_google_cloud


def main():
    st.set_page_config(
        page_title="Employee Tax Forms Assistant", page_icon="🗂", layout="wide"
    )

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

    # Add credentials input
    with st.expander(
        "Google Cloud and Vertex AI Credentials",
        expanded=not st.session_state.get("credentials_provided", False),
    ):
        credentials_text = st.text_area(
            "Paste your Google Cloud and Vertex AI credentials (JSON) here",
            height=200,
            help="This should be a JSON file containing your Google Cloud and Vertex AI credentials",
        )

        # Add Load Credentials button
        if st.button("Load Credentials", key="load_credentials"):
            if credentials_text:
                try:
                    credentials_json = json.loads(credentials_text)
                    st.success("Credentials loaded successfully")
                    st.session_state.credentials = credentials_json
                    st.session_state.credentials_provided = True
                except json.JSONDecodeError:
                    st.error("Invalid JSON format. Please check your credentials.")
                    st.session_state.credentials_provided = False
            else:
                st.warning("Please paste your credentials before loading.")

    if not st.session_state.get("credentials_provided"):
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
        col1, col2 = st.columns([1, 2])

        with col1:
            st.info(f"{len(uploaded_files)} file(s) selected")

        if st.button("Process Form", type="primary", use_container_width=True):
            with st.spinner("Processing the form..."):
                try:
                    # Initialize Google Cloud services with provided credentials
                    storage_client, model = init_google_cloud(
                        st.session_state.credentials
                    )

                    # Upload files to GCS and get URLs
                    progress_bar = st.progress(0)
                    gcs_urls = []

                    for i, pdf_file in enumerate(uploaded_files):
                        with st.status(
                            f"Uploading {pdf_file.name}...", expanded=False
                        ) as status:
                            gcs_url = upload_to_gcs(pdf_file, storage_client)
                            gcs_urls.append(gcs_url)
                            progress = (i + 1) / len(uploaded_files)
                            progress_bar.progress(progress)
                            status.update(
                                label=f"Uploaded {pdf_file.name}", state="complete"
                            )

                    # Process PDFs with Gemini
                    results = process_multiple_pdfs(gcs_urls, model)

                    # Display results
                    st.subheader("Analysis")
                    st.markdown(results)

                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.error("Please check your credentials and try again.")


if __name__ == "__main__":
    main()
