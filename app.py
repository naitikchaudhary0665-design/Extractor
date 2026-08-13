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
        
        # --- DYNAMIC MODEL FINDER (Yahi asli jugad hai) ---
        def get_model():
            # Sirf 'flash' wale models dhundo jo 'generateContent' support karte hain
            for m in genai.list_models():
                if 'flash' in m.name and 'generateContent' in m.supported_generation_methods:
                    return genai.GenerativeModel(m.name)
            return None # Agar koi nahi mila toh None

        model = get_model()
        if not model:
            st.error("No compatible Flash model found for your API key. Check AI Studio permissions.")
            st.stop()

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
                        "Total Amount": item.get("total_amount", 0),
                        "CGST": item.get("cgst_amount", 0)
                    })
            except Exception as e:
                st.error(f"Error in {file.name}: {e}")
            
            progress_bar.progress((index + 1) / len(uploaded_files))

        if all_data:
            df = pd.DataFrame(all_data)
            output = io.BytesIO()
            df.to_excel(output, index=False)
            st.download_button("📥 Download Excel", data=output.getvalue(), file_name="Invoice_Data.xlsx")
