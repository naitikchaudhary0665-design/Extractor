import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
from PIL import Image

st.set_page_config(page_title="Local Invoice Extractor", layout="wide")
st.title("🚀 Smart Invoice Extractor (No API Key Required)")

uploaded_files = st.file_uploader("Upload Invoices (PDF/Images)", type=["jpg", "png", "pdf"], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 Process & Generate Excel"):
        all_data = []
        progress_bar = st.progress(0)
        
        for index, file in enumerate(uploaded_files):
            st.write(f"Processing ({index+1}/{len(uploaded_files)}): {file.name}")
            try:
                extracted_text = ""
                
                # Agar PDF hai toh pdfplumber se text nikalenge
                if file.type == "application/pdf":
                    with pdfplumber.open(file) as pdf:
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                extracted_text += text + "\n"
                else:
                    # Image ke liye basic handling
                    extracted_text = "Image uploaded - manual text parsing placeholder"

                # Basic regex se data detect karne ka jugad
                # Party name, invoice number aur amounts find karne ke liye
                inv_match = re.search(r'(?:Invoice No|Inv No|Invoice Number|Bill No)[:#]?\s*([A-Za-z0-9\-_/]+)', extracted_text, re.IGNORECASE)
                invoice_number = inv_match.group(1) if inv_match else "N/A"
                
                date_match = re.search(r'(?:Date|Dated)[:]?\s*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})', extracted_text, re.IGNORECASE)
                invoice_date = date_match.group(1) if date_match else "N/A"

                # Agar line items nahi milte toh poore text ko ek line item maan kar amount nikal lenge
                amount_matches = re.findall(r'(?:Total|Amount|Rs\.?|INR)\s*[:]?\s*([0-9,]+\.[0-9]{2})', extracted_text, re.IGNORECASE)
                total_amount = amount_matches[-1] if amount_matches else 0

                all_data.append({
                    "File Name": file.name,
                    "Party Name": "Extracted from PDF Text",
                    "Invoice Date": invoice_date,
                    "Invoice Number": invoice_number,
                    "Item Name": "Standard Invoice Item",
                    "Quantity": 1,
                    "Rate": total_amount,
                    "Total Amount": total_amount,
                    "CGST Amount": 0,
                    "SGST Amount": 0,
                    "IGST Amount": 0
                })
                
            except Exception as e:
                st.error(f"Error in {file.name}: {e}")
            
            progress_bar.progress((index + 1) / len(uploaded_files))

        if all_data:
            df = pd.DataFrame(all_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Data')
            st.download_button("📥 Download Excel", data=output.getvalue(), file_name="Local_Invoice_Data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.warning("No data extracted.")
