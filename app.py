import streamlit as st
import pandas as pd
import pdfplumber
import io

st.set_page_config(page_title="Local Table Invoice Extractor", layout="wide")
st.title("🚀 Smart Invoice Table Extractor (No API Required)")

uploaded_files = st.file_uploader("Upload Invoices (PDF)", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 Process & Extract Tables"):
        all_data = []
        progress_bar = st.progress(0)
        
        for index, file in enumerate(uploaded_files):
            st.write(f"Processing ({index+1}/{len(uploaded_files)}): {file.name}")
            try:
                with pdfplumber.open(file) as pdf:
                    file_has_table = False
                    for page in pdf.pages:
                        # PDF ke andar ki tables ko auto-detect karke extract karega
                        tables = page.extract_tables()
                        for table in tables:
                            if table and len(table) > 1:
                                file_has_table = True
                                # Table ki rows ko data mein add karein
                                for row in table[1:]: # Pehli row header maankar skip kar sakte hain
                                    if any(row): # Agar row khaali nahi hai
                                        all_data.append({
                                            "File Name": file.name,
                                            "Raw Data / Columns": " | ".join([str(cell) for cell in row if cell])
                                        })
                    
                    # Agar table detect nahi hui toh poora text extract karke dikhayega taaki 0 na aaye
                    if not file_has_table:
                        full_text = ""
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                full_text += text + "\n"
                        
                        for line in full_text.split("\n"):
                            if line.strip():
                                all_data.append({
                                "File Name": file.name,
                                "Raw Data / Columns": line.strip()
                            })
                            
            except Exception as e:
                st.error(f"Error in {file.name}: {e}")
            
            progress_bar.progress((index + 1) / len(uploaded_files))

        if all_data:
            df = pd.DataFrame(all_data)
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Extracted_Data')
            st.download_button("📥 Download Excel", data=output.getvalue(), file_name="Invoice_Tables.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.warning("Koi data nahi mil paya. Kripya doosri PDF try karein.")
