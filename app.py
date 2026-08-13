import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
import time
import json
from PIL import Image

st.set_page_config(page_title="Pro Invoice Extractor", layout="wide")
st.title("🚀 Advanced Bulk Invoice Extractor")

if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception as e:
        st.error(f"API Config Error: {e}")
else:
    st.error("Gemini API Key missing in Secrets!")

uploaded_files = st.file_uploader("Upload Invoices", type=["jpg", "png", "pdf"], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 Process & Generate Excel"):
        all_data = []
        progress_bar = st.progress(0)
        
        # --- SAFE MODEL FINDER (Blacklisting 2.5) ---
        def get_safe_model():
            try:
                for m in genai.list_models():
                    model_name = m.name.replace("models/", "")
                    # 2.5 ya purane models ko skip karein, sirf 1.5 ya stable flash uthayein
                    if 'generateContent' in m.supported_generation_methods:
                        if 'flash' in model_name and '2.5' not in model_name:
                            return genai.GenerativeModel(model_name)
            except Exception:
                pass
            
            # Fallback agar list_models fail ho jaye
            return genai.GenerativeModel("gemini-1.5-flash")

        model = get_safe_model()

        for index, file in enumerate(uploaded_files):
            try:
                file_bytes = file.read()
                prompt = "Extract party_name, invoice_date, invoice_number, and list items (item_name, quantity, rate, total_amount, cgst_amount, sgst_amount, igst_amount). Return ONLY JSON."
                
                response = model.generate_content([
                    {"mime_type": "application/pdf" if file.type == "application/pdf" else "image/jpeg", "data": file_bytes},
                    prompt
                ])
                
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
            
            progress_bar.progress((index + 1) / len(uploaded_files))

        if all_data:
            df = pd.DataFrame(all_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Data')
            st.download_button("📥 Download Excel", data=output.getvalue(), file_name="Invoice_Data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.warning("No data extracted. Check your files or API permissions.")
