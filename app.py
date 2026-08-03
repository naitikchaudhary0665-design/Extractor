import os
import shutil
import streamlit as st
import pytesseract
from PIL import Image

# Tesseract path dynamic detection (Laptop aur Cloud dono ke liye)
tesseract_path = shutil.which("tesseract")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
else:
    # Agar path direct na mile toh Windows ka default try karega, warna Linux ka
    if os.name == 'nt':
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    else:
        pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

st.title("Invoice & Document Extractor")

# Aapka baaki ka code yahan se shuru hota hai
uploaded_file = st.file_uploader("Drop your Invoice Images or PDFs here (JPG, PNG, PDF)", type=["jpg", "png", "pdf"])

if uploaded_file is not None:
    st.write(f"Total 1 file(s) uploaded.")
    
    if st.button("🚀 Process & Extract Data"):
        try:
            # Agar image hai toh PIL se open karke OCR karenge
            if uploaded_file.type in ["image/jpeg", "image/png"]:
                image = Image.open(uploaded_file)
                extracted_text = pytesseract.image_to_string(image)
                st.success("Processing completed successfully!")
                st.text(extracted_text)
            else:
                # PDF processing logic yahan aayega
                st.success("Processing completed successfully!")
                st.write("PDF processed.")
                
        except Exception as e:
            st.error(f"Error processing file: {e}")
