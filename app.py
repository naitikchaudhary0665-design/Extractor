import streamlit as st
import pandas as pd
import pdfplumber
import io
import re

st.set_page_config(page_title="Clean Invoice Extractor", layout="wide")
st.title("🚀 Perfect Invoice Extractor (No API Required)")

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
                
                # Invoice Date dhundne ke liye
                date_match = re.search(r'Date[:]?\s*([0-9/]+)', extracted_text, re.IGNORECASE)
                inv_date = date_match.group(1) if date_match else "N/A"
                
                # Invoice Number dhundne ke liye
                inv_no_match = re.search(r'(?:Invoice|Inv|Bill)\s*(?:No|Number)[:#]?\s*([A-Za-z0-9\-_/]+)', extracted_text, re.IGNORECASE)
                inv_number = inv_no_match.group(1) if inv_no_match else "N/A"

                lines = extracted_text.split("\n")
                for line in lines:
                    # Sirf unhi lines ko uthayenge jisme item description aur price ho (jaise USD ya $)
                    if ("USD" in line or "$" in line) and "Sub Total" not in line and "Total" not in line and "Balance" not in line and "Credit" not in line:
                        
                        # Price extract karein (jaise $37.50 ya 50.00)
                        price_match = re.findall(r'[\$]?([0-9]+\.[0-9]{2})', line)
                        amount = price_match[-1] if price_match else "0"
                        
                        # Item name me se price hata kar clean name rakhein
                        item_name = line
                        for p in price_match:
                            item_name = item_name.replace(p, "").replace("USD", "").replace("$", "").strip()
                        
                        if not item_name:
                            item_name = "Invoice Item"
                            
                        all_data.append({
                            "File Name": file.name,
                            "Invoice Date": inv_date,
                            "Invoice Number": inv_number,
                            "Item Name": item_name,
                            "Quantity": 1,
                            "Rate": amount,
                            "Total Amount": amount,
                            "CGST Amount": 0,
                            "SGST Amount": 0,
                            "IGST Amount": 0
                        })
                        
            except Exception as e:
                # Yeh rahi line jisme 'f5' ki jagah sirf 'f' kar diya gaya hai
                st.error(f"Error in {file.name}: {e}")
            
            progress_bar.progress((index + 1) / len(uploaded_files))

        if all_data:
            df = pd.DataFrame(all_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Clean_Data')
            st.download_button("📥 Download Clean Excel", data=output.getvalue(), file_name="Clean_Invoice_Data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.warning("Koi data match nahi hua.")
