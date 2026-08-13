import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
import io
import time
import json
from PIL import Image

st.set_page_config(page_title="Pro Invoice Extractor", layout="wide")
st.title("🚀 Advanced Bulk Invoice Extractor")

if "GEMINI_API_KEY" in st.secrets:
    try:
        # New Google GenAI Client Initialization
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception as e:
        st.error(f"API Config Error: {e}")
else:
    st.error("Gemini API Key missing in Secrets!")

uploaded_files = st.file_uploader("Upload Invoices", type=["jpg", "png", "pdf"], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 Process & Generate Excel"):
        all_data = []
        progress_bar = st.progress(0)
        
        for index, file in enumerate(uploaded_files):
            st.write(f"Processing ({index+1}/{len(uploaded_files)}): {file.name}")
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
                
                # Using the latest recommended model with new client
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        types.Part.from_bytes(
                            data=file_bytes,
                            mime_type="application/pdf" if file.type == "application/pdf" else "image/jpeg",
                        ),
                        prompt
                    ]
                )
                
                res_text = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(res_text)
                
                meta = data.get("invoice_metadata", {})
                for item in data.get("line_items", []):
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
                st.error(f"Error in {file.name}: {e}")
            
            time.sleep(1)
            progress_bar.progress((index + 1) / len(uploaded_files))

        if all_data:
            df = pd.DataFrame(all_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Data')
            st.download_button("📥 Download Excel", data=output.getvalue(), file_name="Invoice_Data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.warning("No data extracted. Please check your file content.")
