import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

st.set_page_config(page_title="Smart Invoice Extractor", layout="wide")
st.title("🚀 Clean Invoice Extractor (No API Required)")

uploaded_files = st.file_uploader("Upload Invoices (PDF)", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 Process & Generate Clean Excel"):
        all_data = []
        progress_bar = st.progress(0)
        
        for index, file in enumerate(uploaded_files):
            st.write(f"Processing ({index+1}/{len(uploaded_files)}): {file.name}")
            try:
                extracted_text = ""
                with pdfplumber.open(file) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            extracted_text += text + "\n"
                
                # Invoice fields find karne ke liye
                date_match = re.search(r'Date[:]?\s*([0-9/]+)', extracted_text, re.IGNORECASE)
                inv_date = date_match.group(1) if date_match else "N/A"
                
                # Items aur amounts ko lines se dhundna
                lines = extracted_text.split("\n")
                for line in lines:
                    # Agar line mein item description aur price (USD/Rs) hai
                    if "USD" in line or "$" in line or "Total" in line or "Membership" in line or "Discount" in line:
                        # Price extract karein
                        price_match = re.search(r'([-\$0-9\.]+\b)', line)
                        amount = price_match.group(1) if price_match else "0"
                        
                        # Item name alag karein
                        item_name = line.replace(amount, "").strip()
                        if not item_name:
                            item_name = line
                            
                        all_data.append({
                            "File Name": file.name,
                            "Invoice Date": inv_date,
                            "Item Name": item_name,
                            "Quantity": 1,
                            "Rate": amount,
                            "Total Amount": amount,
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
                df.to_excel(writer, index=False, sheet_name='Parsed_Data')
            st.download_button("📥 Download Clean Excel", data=output.getvalue(), file_name="Clean_Invoice_Data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.warning("Koi data extract nahi ho paya.")
