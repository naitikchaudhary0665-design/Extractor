import os
import shutil
import time
import json
import streamlit as st
import pytesseract
from PIL import Image
import google.generativeai as genai

# --- Tesseract Dynamic Path Configuration ---
tesseract_path = shutil.which("tesseract")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
else:
    if os.name == 'nt':
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    else:
        pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# --- Streamlit Page Setup ---
st.set_page_config(page_title="Invoice & Document Extractor", layout="wide")
st.title("🚀 Bulk Invoice & Document Extractor")

# --- Secure Gemini API Configuration ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Gemini API Key missing! Please add it in Streamlit Cloud Settings -> Secrets.")

# Bill Type Selection
bill_type = st.radio("Select Bill Type (Aap kis tarah ka bill upload kar rahe hain?):", ["Sale Invoice", "Purchase Bill"])

# Multiple File Uploader
uploaded_files = st.file_uploader(
    "Drop your Invoice Images or PDFs here (JPG, PNG, PDF)", 
    type=["jpg", "png", "pdf"], 
    accept_multiple_files=True
)

if uploaded_files:
    st.info(f"Total {len(uploaded_files)} file(s) uploaded as {bill_type}.")
    
    if st.button("🚀 Process & Extract Data"):
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("Kripya pehle Streamlit secrets mein API key set karein.")
        else:
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            progress_bar = st.progress(0)
            total_files = len(uploaded_files)
            
            results = []
            
            for index, uploaded_file in enumerate(uploaded_files):
                st.write(f"Processing ({index+1}/{total_files}): {uploaded_file.name}...")
                
                try:
                    file_text = ""
                    
                    if uploaded_file.type in ["image/jpeg", "image/png"]:
                        image = Image.open(uploaded_file)
                        file_text = pytesseract.image_to_string(image)
                    else:
                        file_bytes = uploaded_file.read()
                        response_pdf = model.generate_content([
                            {"mime_type": "application/pdf", "data": file_bytes},
                            "Extract all invoice items, quantities, rates, and total amounts accurately in a structured format."
                        ])
                        file_text = response_pdf.text
                    
                    if uploaded_file.type in ["image/jpeg", "image/png"] and file_text:
                        prompt = f"Extract all items, quantities, rates, and total amounts from this invoice text:\n{file_text}"
                        response_gemini = model.generate_content(prompt)
                        extracted_data = response_gemini.text
                    else:
                        extracted_data = file_text
                        
                    results.append({"file_name": uploaded_file.name, "data": extracted_data})
                    st.success(f"Successfully processed: {uploaded_file.name}")
                    
                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {e}")
                
                time.sleep(2)
                progress_bar.progress((index + 1) / total_files)
                
            st.balloons()
            st.success("Processing completed successfully for all files!")
            
            st.subheader("Extracted Results Summary")
            for res in results:
                with st.expander(res["file_name"]):
                    st.write(res["data"])
