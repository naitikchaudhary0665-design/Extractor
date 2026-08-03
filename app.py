import shutil
import pytesseract
import os

# Dynamic path detection for Tesseract
tesseract_path = shutil.which("tesseract")
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
else:
    if os.name == 'nt':
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    else:
        pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
import json
import os
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


# --- 2. PASSWORD PROTECTION SECURITY ---
def check_password():
  """Returns True if the user enters the correct password."""

  def password_entered():
    # Yahan "Naitik@123" ki jagah aap apna manchaha password rakh sakte hain
    if st.session_state["password"] == "mysecretpassword123":
      st.session_state["password_correct"] = True
      del st.session_state["password"]
    else:
      st.session_state["password_correct"] = False

  if "password_correct" not in st.session_state:
    st.markdown("## 🔒 Secure Invoice Extractor")
    st.text_input(
        "Enter Password to Access App:",
        type="password",
        on_change=password_entered,
        key="password",
    )
    return False
  elif not st.session_state["password_correct"]:
    st.markdown("## 🔒 Secure Invoice Extractor")
    st.text_input(
        "Enter Password to Access App:",
        type="password",
        on_change=password_entered,
        key="password",
    )
    st.error("😕 Galat password. Kripya dobara koshish karein.")
    return False
  else:
    return True


# Agar password theek nahi hai, toh app yahin ruk jayegi
if not check_password():
  st.stop()


# --- TESSERACT PATH CONFIGURATION ---
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract OCR\tesseract.exe"
)

# Groq API Key Setup
client = Groq(api_key="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")

# --- 3. HEADER SECTION ---
st.markdown(
    '<p class="main-title">📄 Universal Invoice to Excel Extractor</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="sub-text">Select invoice type, upload images or PDFs, and'
    ' extract data accurately into an Excel sheet.</p>',
    unsafe_allow_html=True,
)

st.divider()

# --- 4. INVOICE TYPE SELECTION ---
invoice_type = st.radio(
    "📌 Select Bill Type (Aap kis tarah ka bill upload kar rahe hain?):",
    ("Sale Invoice", "Purchase Bill"),
    horizontal=True,
)

st.write("")

# --- 5. FILE UPLOADER ---
uploaded_files = st.file_uploader(
    "📁 Drop your Invoice Images or PDFs here (JPG, PNG, PDF)",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

if uploaded_files:
  st.info(
      f"📁 Total **{len(uploaded_files)}** file(s) uploaded as **{invoice_type}**."
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

        status_text.text(f"🤖 AI analyzing Tally invoice details for '{file_name}'...")

        prompt = f"""
                You are an expert Chartered Accountant specializing in Tally ERP/Prime invoice auditing and data extraction.
                Analyze the invoice text below very carefully.
                
                PARTY EXTRACTION RULE:
                - {party_instruction}

                MANDATORY JSON KEYS FOR EVERY ITEM ROW:
                - "Invoice No" (Find the exact bill/invoice number)
                - "Date" (Invoice date strictly in DD-MM-YYYY format)
                - "Party GST No" (15-digit GSTIN of the correct party)
                - "Party Name" (Name of the correct party)
                - "Item Name" (Exact product description from the items table)
                - "HSN/SAC" (HSN code if present, else "Not Found")
                - "Amount" (Taxable amount for that specific item row)
                - "CGST" (CGST amount for that item row from Tally tax columns or tax summary, or "0")
                - "SGST" (SGST amount for that item row from Tally tax columns or tax summary, or "0")
                - "IGST" (IGST amount for that item row from Tally tax columns or tax summary, or "0")

                TALLY INVOICE GUIDELINES:
                1. Tally invoices often have separate tax columns next to the item row or a tax analysis table at the bottom. Read them carefully and map them to each respective item.
                2. If the tax is given as a combined total at the bottom for all items, distribute it proportionally among the item rows based on their taxable amounts.
                3. Do NOT leave CGST, SGST, or IGST as "0" if tax amounts are clearly visible in the text. Calculate or map them precisely.
                4. If any text/number is missing, write "Not Found" for text or "0" for numbers.

                Invoice Text:
                {text}
                
                Return ONLY a valid JSON list starting with '[' and ending with ']'. No markdown ticks, no extra text.
                """

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )

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
