import json
import os
import time
import fitz  # PyMuPDF
import pandas as pd
import pdfplumber
import pytesseract
from PIL import Image, ImageEnhance, ImageOps
import streamlit as st
from groq import Groq

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(
    page_title="Universal Invoice Extractor", page_icon="📄", layout="wide"
)

st.markdown("""
    <style>
    .main-title { font-size: 28px; font-weight: 700; color: #1E3A8A; margin-bottom: 0px; }
    .sub-text { font-size: 15px; color: #4B5563; margin-bottom: 20px; }
    .stButton>button { background-color: #2563EB; color: white; font-weight: 600; border-radius: 6px; padding: 0.5rem 1rem; border: none; }
    .stButton>button:hover { background-color: #1D4ED8; }
    </style>
""", unsafe_allow_html=True)

# --- TESSERACT PATH CONFIGURATION ---
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Groq API Key Setup
api_key = st.secrets["GROQ_API_KEY"] if "GROQ_API_KEY" in st.secrets else "Yahan_Apni_Groq_Key_Dalein"
client = Groq(api_key=api_key)

# --- 2. HEADER SECTION ---
st.markdown(
    '<p class="main-title">📄 Universal Invoice to Excel Extractor</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-text">Select invoice type, upload 20-25+ images or PDFs, and extract all data accurately into a single Excel sheet.</p>',
    unsafe_allow_html=True,
)

st.divider()

# --- 3. INVOICE TYPE SELECTION ---
invoice_type = st.radio(
    "📌 Select Bill Type (Aap kis tarah ka bill upload kar rahe hain?):",
    ("Sale Invoice", "Purchase Bill"),
    horizontal=True,
)

st.write("")

# --- 4. FILE UPLOADER (Supports 25+ files) ---
uploaded_files = st.file_uploader(
    "📁 Drop your Invoice Images or PDFs here (You can select 20-25+ files at once)",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

if uploaded_files:
  st.info(
      f"📁 Total **{len(uploaded_files)}** file(s) selected as **{invoice_type}**."
  )

  if st.button("🚀 Process & Extract Data"):
    extracted_data = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_files = len(uploaded_files)

    if invoice_type == "Sale Invoice":
      party_instruction = (
          "Since this is a Sale Invoice, look for the 'Billed To' / 'Buyer' /"
          " 'Consignee' section and extract that customer's/buyer's name and"
          " their GSTIN as 'Party Name' and 'Party GST No'. Do NOT pick the top"
          " issuer company name."
      )
    else:
      party_instruction = (
          "Since this is a Purchase Bill, look at the very top header"
          " (issuer/supplier company) and extract that company's name and"
          " their GSTIN as 'Party Name' and 'Party GST No'."
      )

    for i, uploaded_file in enumerate(uploaded_files):
      file_name = uploaded_file.name
      file_extension = file_name.split(".")[-1].lower()
      status_text.text(
          f"⏳ Processing file {i+1} of {total_files}: '{file_name}'..."
      )
      text = ""

      try:
        if file_extension in ["png", "jpg", "jpeg"]:
          img = Image.open(uploaded_file)
          if img.mode == "RGBA":
            img = img.convert("RGB")
          img = img.resize(
              (img.width * 2, img.height * 2), Image.Resampling.LANCZOS
          )
          img = ImageOps.grayscale(img)
          enhancer = ImageEnhance.Contrast(img)
          img = enhancer.enhance(2.0)
          text = pytesseract.image_to_string(img, config=r"--oem 3 --psm 6")

        elif file_extension == "pdf":
          uploaded_file.seek(0)
          with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
              t = page.extract_text(layout=True)
              if t:
                text += t + "\n"

          if not text.strip():
            uploaded_file.seek(0)
            pdf_document = fitz.open(
                stream=uploaded_file.read(), filetype="pdf"
            )
            for page_num in range(len(pdf_document)):
              page = pdf_document[page_num]
              pix = page.get_pixmap(dpi=300)
              img_path = f"temp_page_{page_num}.png"
              pix.save(img_path)

              img = Image.open(img_path)
              img = ImageOps.grayscale(img)
              enhancer = ImageEnhance.Contrast(img)
              img = enhancer.enhance(2.0)
              ocr_text = pytesseract.image_to_string(img, config=r"--oem 3 --psm 6")
              text += ocr_text + "\n"
              if os.path.exists(img_path):
                os.remove(img_path)

        if not text or len(text.strip()) < 3:
          st.warning(
              f"⚠️ Could not read text from '{file_name}'. Please ensure the"
              " file is clear."
          )
          continue

        status_text.text(f"🤖 AI analyzing details & taxes for '{file_name}'...")

        prompt = f"""
                You are an expert Chartered Accountant and Tally ERP/Prime data extraction specialist.
                Analyze the invoice text below very carefully to extract item-wise details, rates, quantities, taxes, and amounts.

                PARTY EXTRACTION RULE:
                - {party_instruction}

                CRITICAL EXTRACTION GUIDELINES:
                1. "Rate": Price per single unit of the item.
                2. "GST Rate": Percentage value of GST (e.g., 5, 12, 18, 28). If split like 2.5% CGST + 2.5% SGST, the total GST Rate is 5.
                3. "Quantity": Exact quantity for each item row.
                4. "Amount": Taxable value for that specific item row.
                5. "CGST", "SGST", "IGST": Extract exact tax amounts for the item row. If taxes are shown in a summary table at the bottom, distribute them proportionally to each item row based on their taxable amounts. Do not leave them as "0" if tax values are visible.

                MANDATORY JSON KEYS FOR EVERY ITEM ROW:
                - "Invoice No" (Find the exact bill/invoice number)
                - "Date" (Invoice date strictly in DD-MM-YYYY format)
                - "Party GST No" (15-digit GSTIN, or "Not Found")
                - "Party Name" (Name of the correct party)
                - "Item Name" (Exact product description)
                - "HSN/SAC" (HSN code if present, else "Not Found")
                - "Quantity" (Item quantity)
                - "Rate" (Unit rate)
                - "GST Rate" (GST percentage like 5, 12, 18)
                - "Amount" (Taxable amount)
                - "CGST" (CGST amount, else "0")
                - "SGST" (SGST amount, else "0")
                - "IGST" (IGST amount, else "0")

                Invoice Text:
                {text}
                
                Return ONLY a valid JSON list starting with '[' and ending with ']'. No markdown ticks, no extra text.
                """

        # --- RATE LIMIT HANDLING & RETRY LOGIC ---
        completion = None
        for attempt in range(4):
          try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            break
          except Exception as rate_err:
            if "rate_limit" in str(rate_err).lower() or "429" in str(rate_err):
              if attempt < 3:
                status_text.text(f"⏳ Rate limit hit. Waiting 8 seconds before retry ({attempt+1}/3) for '{file_name}'...")
                time.sleep(8)
              else:
                raise rate_err
            else:
              raise rate_err

        response_text = completion.choices[0].message.content.strip()

        if "```json" in response_text:
          response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
          response_text = response_text.split("```")[1].split("```")[0]

        cleaned_text = response_text.strip()
        start_idx = cleaned_text.find("[")
        end_idx = cleaned_text.rfind("]")

        if start_idx != -1 and end_idx != -1:
          json_str = cleaned_text[start_idx : end_idx + 1]
          items = json.loads(json_str)
          for item in items:
            item["Bill Type"] = invoice_type
            item["Source File"] = file_name
            extracted_data.append(item)
        else:
          st.error(
              f"⚠️ Failed to parse AI response for '{file_name}'. Please try"
              " again."
          )

      except Exception as e:
        st.error(f"❌ Error processing {file_name}: {e}")

      # Safe delay between files to support 25+ bulk requests smoothly
      time.sleep(3.5)
      progress_bar.progress((i + 1) / total_files)

    status_text.text("✨ Processing completed successfully!")
    progress_bar.empty()

    if extracted_data:
      df = pd.DataFrame(extracted_data)
      st.markdown("### 📋 Extracted Data Preview")
      df.drop_duplicates(inplace=True)
      st.dataframe(df, use_container_width=True)

      output_file = "Invoice_Data_Export.xlsx"
      df.to_excel(output_file, index=False)

      with open(output_file, "rb") as f:
        st.download_button(
            label="📥 Download Excel Sheet",
            data=f,
            file_name="Invoice_Data_Export.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
