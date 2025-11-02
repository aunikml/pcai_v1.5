# utils.py
import streamlit as st
import docx
import PyPDF2
import pandas as pd
import io

def parse_document(uploaded_file):
    """Reads the content of an uploaded file (pdf, docx, csv) and returns it as a string."""
    if uploaded_file is None:
        return ""
    
    try:
        filename = uploaded_file.name
        if filename.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue()))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        elif filename.endswith(".docx"):
            doc = docx.Document(io.BytesIO(uploaded_file.getvalue()))
            return "\n".join([para.text for para in doc.paragraphs])
        elif filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(uploaded_file.getvalue()))
            return df.to_string()
        else:
            return "Unsupported file type."
    except Exception as e:
        st.error(f"Error parsing document: {e}")
        return ""