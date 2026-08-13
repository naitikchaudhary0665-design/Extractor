import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import time
import json
from PIL import Image

# --- Setup ---
st.set_page_config(page_title="Pro Invoice Extractor", layout="wide")
st.title("🚀 Advanced Bulk Invoice Extractor")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Gemini API Key missing! Set it in Streamlit Secrets.")

uploaded_files = st.file_uploader("Upload Invoices (PDF/Images)", type=["jpg", "png", "pdf"], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 Process & Generate Full Excel"):
        # Yahan model name ko update karke stable version de diya hai
        model = genai.GenerativeModel("gemini-1.5-flash-002")
        all_data = []
        
        progress_bar = st.progress(0)
        total_files = len(uploaded_files)
        
        for index, file in enumerate(uploaded_files):
            st.write(f"Processing ({index+1}/{total_files}): {file.name}")
            try:
                file_bytes = file.read()
                
                prompt = """
                Extract details from this invoice. Return ONLY a valid JSON object. 
                Structure:
                {
                  "invoice_metadata": {"party_name": "string", "invoice_date": "string", "invoice_number": "string"},
                  "line_items": [
                    {"item_name": "string", "quantity": 0, "rate": 0, "total_amount": 0, "cgst_amount": 0, "sgst_amount": 0, "igst_amount": 0}
                  ]
                }
                If value is missing, use null or 0. Do not use markdown backticks in output.
                """
                
                response = model.generate_content([
                    {"mime_type": "application/pdf" if file.type == "application/pdf" else "image/jpeg", "data": file_bytes},
                    prompt
                ])
                
                res_text = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(res_text)
                
                meta = data.get("invoice_metadata", {})
                items = data.get("line_items", [])
                
                for item in items:
                    all_data.append({
                        "File Name": file.name,
                        "Party Name": meta.get("party_name", "N/A"),
                        "Invoice Date": meta.get("invoice_date", "N/A"),
                        "Invoice Number": meta.get("invoice_number", "N/A"),
                        "Item Name": item.get("item_name", "N/A"),
                        "Quantity": item.get("quantity", 0),
                        "Rate": item.get("rate", 0),
                        "Total Amount": item.get("total_amount", 0),
                        "CGST Amount": item.get("cgst_amount", 0),
                        "SGST Amount": item.get("sgst_amount", 0),
                        "IGST Amount": item.get("igst_amount", 0)
                    })
                    
            except Exception as e:
                st.error(f"Error in {file.name}: {str(e)}")
            
            time.sleep(2)
            progress_bar.progress((index + 1) / total_files)

        if all_data:
            df = pd.DataFrame(all_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Data')
            
            st.success("Extraction Complete!")
            st.download_button(
                label="📥 Download Detailed Excel",
                data=output.getvalue(),
                file_name="Invoice_Data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("No data extracted. Check your files!")
