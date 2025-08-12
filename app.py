import io
import json
import re
import tempfile
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

# Configure Tesseract path for Windows
def setup_tesseract():
    """Set up Tesseract OCR path for Windows."""
    # Check if Tesseract is already configured
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return  # Already working
    except:
        pass
    
    # Windows-specific paths
    possible_tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME', '')),
    ]
    
    for path in possible_tesseract_paths:
        if os.path.exists(path):
            # Set environment variables for img2table
            tesseract_dir = os.path.dirname(path)
            os.environ["PATH"] = tesseract_dir + os.pathsep + os.environ.get("PATH", "")
            os.environ["TESSERACT_PATH"] = path
            
            # Also set for pytesseract
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = path
            except:
                pass
            
            print(f"✅ Added Tesseract to PATH: {tesseract_dir}")
            break

# Set up Tesseract on import
setup_tesseract()

# Format detection helpers
def first_page_text(pdf_bytes: bytes) -> str:
    """Best-effort text of page 1: pdf text -> OCR image."""
    # Try pdfplumber text first
    if HAVE_PDFPLUMBER:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                t = pdf.pages[0].extract_text() or ""
                if t.strip():
                    return t
        except Exception:
            pass
    # Fallback to OCR
    if HAVE_PYMUPDF and HAVE_OCR:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pix = doc[0].get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        try:
            import pytesseract
            return pytesseract.image_to_string(img)
        except Exception:
            return ""
    return ""

def detect_WIS_S_v1(text_first_page: str) -> bool:
    """Identify WIS/SANAS S1–S2 format by robust anchors."""
    t = re.sub(r"\s+", " ", text_first_page).lower()
    anchors = [
        "weighing instrument services",     # lab header
        "calibration certificate no",       # big title
        "uncertainty of calibration",       # col header phrase
        "results",                          # section marker
    ]
    return all(a in t for a in anchors)

# Monkey patch img2table to use our Tesseract path
def patch_img2table_tesseract():
    """Patch img2table to use our configured Tesseract path."""
    try:
        import img2table.ocr.tesseract
        original_init = img2table.ocr.tesseract.TesseractOCR.__init__
        
        def patched_init(self, n_threads=1, lang='eng', psm=11, tessdata_dir=None):
            # Create custom environment with our PATH
            env = os.environ.copy()
            if tessdata_dir:
                env["TESSDATA_PREFIX"] = tessdata_dir
            
            # Override the environment to include our Tesseract path
            self.env = env
            
            # Skip the subprocess check since we know Tesseract exists
            # This is a bit of a hack, but it should work
            self.n_threads = n_threads
            self.lang = lang
            self.psm = psm
        
        # Apply the patch
        img2table.ocr.tesseract.TesseractOCR.__init__ = patched_init
        print("✅ Patched img2table TesseractOCR")
        
    except Exception as e:
        print(f"⚠️ Could not patch img2table: {e}")

# Apply the patch
patch_img2table_tesseract()

# Optional backends; we try/except so the app still runs if some aren't installed
try:
    import camelot  # PDF tables (vector)  — lattice/stream parsers
    HAVE_CAMELOT = True
except Exception:
    HAVE_CAMELOT = False

try:
    import pdfplumber  # PDF text & table extraction
    HAVE_PDFPLUMBER = True
except Exception:
    HAVE_PDFPLUMBER = False

try:
    import fitz  # PyMuPDF — robust PDF rendering to images
    HAVE_PYMUPDF = True
except Exception:
    HAVE_PYMUPDF = False

try:
    from pdf2image import convert_from_bytes  # fallback PDF -> PIL images
    HAVE_PDF2IMAGE = True
except Exception:
    HAVE_PDF2IMAGE = False

try:
    import pytesseract  # OCR
    from img2table.document import Image as I2TImage
    from img2table.ocr import TesseractOCR
    HAVE_OCR = True
except Exception:
    HAVE_OCR = False


# ---------- Domain model (strict rows schema) ----------
@dataclass
class RowOut:
    serialNumber: str
    nominalValueG: str
    actualBeforeG: str
    actualAfterG: str
    uncertaintyG: str
    series: str


# ---------- Normalisation helpers ----------
NBSP = u"\u00A0"

def clean_num_str(s: str) -> str:
    if s is None:
        return "-"
    s = str(s).strip()
    if s in {"", "-", "–", "—"}:
        return "-"
    # normalise thousand separators & decimal comma
    s = s.replace(NBSP, " ")
    s = re.sub(r"[ ,\u00A0](?=\d{3}(?:\D|$))", "", s)  # kill spaced thousands
    s = s.replace(",", ".")
    # remove stray units or symbols (keep pure number + dot)
    s = re.sub(r"[^0-9.\-]", "", s)
    # collapse multiple dots
    parts = s.split(".")
    if len(parts) > 2:
        s = parts[0] + "." + "".join(parts[1:])
    return s

def to_grams_str(val_str: str, header_hint: Optional[str]) -> str:
    """Return a *string* number in grams; keep printed precision."""
    if val_str == "-" or val_str is None:
        return "-"
    s = clean_num_str(val_str)
    if s == "-":
        return "-"
    # Decide units: prefer header hint
    hint = (header_hint or "").lower()
    is_kg = " kg" in " " + hint or "(kg" in hint or "in kg" in hint
    is_g = " g" in " " + hint or "(g" in hint or "value g" in hint
    # If the original text includes unit inline, detect that too (lightweight)
    # We already stripped non-numerics above, so rely on header.
    try:
        if is_kg and s not in {"-", ""}:
            # multiply by 1000 but keep original decimal length
            f = float(s)
            g = f * 1000.0
            # keep as non-scientific, trim trailing zeros sensibly
            out = f"{g:.6f}".rstrip("0").rstrip(".")
            return out
        else:
            # assume grams by default
            return s
    except Exception:
        return s

def series_from_serial(serial: str) -> Optional[str]:
    if not serial or serial == "-":
        return None
    s = str(serial).strip()
    # Examples: "WFS 151" -> WFS; "WOW 2" -> WOW; "W1.3" -> W1; "W-3.5" -> W-3
    m = re.match(r"^([A-Za-z]+)", s)
    if m:
        return m.group(1).upper()
    m = re.match(r"^(W[\- ]?\d+)", s, flags=re.I)
    if m:
        return m.group(1).upper().replace(" ", "")
    # Fall back: token before first digit
    m = re.match(r"^([^\d]+)", s)
    if m:
        return m.group(1).strip().upper()
    return None

def detect_set_series_in_page_text(page_text: str) -> Optional[str]:
    """
    Detect set headers like:
      - 'Set No. W 3'  -> 'W-3'
      - 'SET WOW S1'   -> 'WOW-S1'
    """
    if not page_text:
        return None
    t = re.sub(r"\s+", " ", page_text)

    # Existing W-<n> patterns
    m = re.search(r"Set(?:\s+No\.)?\s+W\s*-?\s*(\d+)", t, flags=re.I)
    if m:
        return f"W-{m.group(1)}"

    # New WIS S1/S2 pattern
    m2 = re.search(r"\bSET\s+WOW\s*S\s*0*([0-9]+)\b", t, flags=re.I)
    if m2:
        return f"WOW-S{m2.group(1)}"

    return None


# ---------- PHASE A: Parse 'Calibration of:' expected counts ----------
def parse_expected_counts(doc_text: str) -> Dict[str, Any]:
    """
    expected = {
        "singlePieces": [{"nominalG": "20000", "count": 25}, ...],
        "sets": [{"setId": "W-1", "count": 1}, ...]
    }
    """
    expected = {"singlePieces": [], "sets": []}
    if not doc_text:
        return expected
    text = re.sub(r"[ \t\u00A0]+", " ", doc_text)
    # Cut to the "Calibration of:" block if present
    calo = re.split(r"Calibration of\s*[:：]", text, flags=re.I)
    if len(calo) > 1:
        # Limit until next obvious section
        blk = re.split(r"(Results\s*:|Table\s*:|Validity|Uncertainty|Traceability|Date\s+of\s+calibration|Date\s+issued)", calo[1], flags=re.I)[0]
    else:
        blk = text

    # A1) single pieces like "7 × 1 kg", "9 x 500 g"
    singles = re.findall(r"(\d+)\s*[x×]\s*([0-9]+(?:[.,][0-9]+)?)\s*(kg|g)\b", blk, flags=re.I)
    for count, nominal, unit in singles:
        nominal_clean = clean_num_str(nominal)
        if unit.lower() == "kg":
            g = float(nominal_clean) * 1000.0
        else:
            g = float(nominal_clean)
        expected["singlePieces"].append({"nominalG": str(int(g)) if g.is_integer() else f"{g}", "count": int(count)})

    # A2) sets like "1 × Set Masspieces W1 ... W9" or "Set No. W 3"
    # First, explicit "x Set ... Wn"
    for m in re.finditer(r"(\d+)\s*[x×]\s*Set.*?W\s*-?\s*(\d+)", blk, flags=re.I):
        expected["sets"].append({"setId": f"W-{m.group(2)}", "count": int(m.group(1))})

    # Also capture plain mentions like "Set No. W 1 ... Set No. W 9" within block
    set_ids = set(re.findall(r"Set(?:\s+No\.)?\s+W\s*-?\s*(\d+)", blk, flags=re.I))
    for sid in sorted(set_ids, key=lambda x: int(x)):
        # default count 1 if not specified with 'x'
        if not any(s["setId"] == f"W-{sid}" for s in expected["sets"]):
            expected["sets"].append({"setId": f"W-{sid}", "count": 1})

    return expected


# ---------- PHASE B: table extraction (page-by-page) ----------
HEADER_SYNONYMS = {
    "serial": ["serial number", "serial no", "s/no", "identification number", "id number", "identification"],
    "nominal": ["nominal value g", "nominal value", "nominal value in g", "nominal value in kg", "nominal value (g)", "nominal value (kg)", "nominal"],
    "actual": ["actual value g", "actual value", "actual value in g", "actual value in kg", "actual value left at", "actual value (g)", "actual value (kg)"],
    "actual_before": ["actual value g before adjustment", "before adjustment", "actual value in kg before adj", "actual value before adj", "actual value before adjustment", "before adj."],
    "actual_after": ["actual value g after adjustment", "after adjustment", "actual value in kg after adj", "actual value after adj", "actual value left at", "left at"],
    "uncertainty": ["uncertainty of measurement ± g", "uncertainty of calibration ± g", "uncertainty of calibration (g) ±", "uncertainty ± g", "uncertainty ± kg", "uncertainty of calibration", "uncertainty"]
}

def normalise_headers(cols: List[str]) -> Dict[str, str]:
    lower = [c.lower().strip() for c in cols]
    mapping = {}
    for k, keys in HEADER_SYNONYMS.items():
        for i, c in enumerate(lower):
            if any(kw in c for kw in keys):
                mapping[k] = cols[i]
                break
    # Fallbacks
    if "actual_before" not in mapping and "actual" in mapping:
        mapping["actual_before"] = None
    if "actual_after" not in mapping and "actual" in mapping:
        mapping["actual_after"] = mapping["actual"]
    return mapping

def extract_tables_with_camelot(tmp_pdf_path: str) -> List[Tuple[int, pd.DataFrame]]:
    if not HAVE_CAMELOT:
        return []
    results = []
    try:
        # Try lattice first (works when lines/borders exist)
        tables = camelot.read_pdf(tmp_pdf_path, flavor="lattice", pages="all")
    except Exception:
        tables = []
    # If lattice found nothing, try stream
    if not tables or len(tables) == 0:
        try:
            tables = camelot.read_pdf(tmp_pdf_path, flavor="stream", pages="all")
        except Exception:
            tables = []
    for t in tables:
        try:
            df = t.df
            # drop empty rows
            if df is not None and df.shape[1] >= 3:
                results.append((t.page, df))
        except Exception:
            continue
    return results

def extract_tables_with_pdfplumber(pdf_bytes: bytes) -> List[Tuple[int, pd.DataFrame, str]]:
    if not HAVE_PDFPLUMBER:
        return []
    out = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pg_idx, page in enumerate(pdf.pages, start=1):
            header_hint = " ".join([x for x in [page.extract_text()] if x]) or ""
            try:
                tables = page.extract_tables()
            except Exception:
                tables = []
            for tbl in tables or []:
                df = pd.DataFrame(tbl)
                if df.shape[1] >= 3:
                    out.append((pg_idx, df, header_hint))
    return out

def ocr_tables_from_page_images(pdf_bytes: bytes) -> List[Tuple[int, List[pd.DataFrame], str]]:
    if not HAVE_OCR:
        return []
    images = []
    header_texts = {}

    if HAVE_PYMUPDF:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for i, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=300)
            images.append((i, pix.tobytes("png")))
            header_texts[i] = page.get_text()
    elif HAVE_PDF2IMAGE:
        for i, im in enumerate(convert_from_bytes(pdf_bytes, dpi=300), start=1):
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            images.append((i, buf.getvalue()))
            header_texts[i] = ""
    else:
        return []

    # Use a more table-friendly PSM
    ocr = TesseractOCR(lang="eng", psm=6)

    out = []
    for page_no, img in images:
        try:
            i2t_img = I2TImage(img=img)
            tables = i2t_img.extract_tables(ocr=ocr)
            dfs = []
            for t in tables or []:
                df = getattr(t, "df", None)
                if df is None:
                    # fallback if library version exposes 'content' only
                    content = getattr(t, "content", None)
                    if isinstance(content, list) and content and isinstance(content[0], list):
                        df = pd.DataFrame(content)
                if isinstance(df, pd.DataFrame) and df.shape[1] >= 3:
                    dfs.append(df)
            if dfs:
                out.append((page_no, dfs, header_texts.get(page_no, "")))
        except Exception:
            continue
    return out


# ---------- Table row parsing ----------
def rows_from_dataframe(df: pd.DataFrame, page_text: str, row_index_offset: int = 0) -> List[RowOut]:
    # Treat first row as header if it looks like header; otherwise infer
    # Heuristic: if any cell in row 0 contains "serial" or "nominal" etc, treat as header
    header_row = 0
    joined = " ".join(str(x).lower() for x in df.iloc[0].tolist())
    looks_header = any(k in joined for k in ["serial", "nominal", "actual", "uncertainty", "identification"])
    if looks_header:
        df2 = df.iloc[1:].reset_index(drop=True)
        cols = [str(c) for c in df.iloc[0].tolist()]
    else:
        df2 = df.copy()
        cols = [f"col_{i}" for i in range(len(df.columns))]
    df2.columns = cols
    mapping = normalise_headers(df2.columns.tolist())

    set_series = detect_set_series_in_page_text(page_text)

    rows: List[RowOut] = []
    for ridx, row in df2.iterrows():
        def get(col_key: str) -> Optional[str]:
            colname = mapping.get(col_key)
            if colname is None:
                return None
            try:
                return str(row[colname])
            except Exception:
                return None

        serial_raw = get("serial")
        # Skip obvious header repeats or empty lines
        if serial_raw and re.search(r"(serial|identification)", str(serial_raw), flags=re.I):
            continue

        nominal_hint = None
        # header units hint: combine mapped headers for nominal & actual columns
        nominal_header = mapping.get("nominal")
        actual_header = mapping.get("actual") or mapping.get("actual_after") or mapping.get("actual_before")
        header_hint = " ".join([str(nominal_header or ""), str(actual_header or "")])

        nominal = to_grams_str(get("nominal") or "-", header_hint)
        actual_before = to_grams_str(get("actual_before") or "-", header_hint)
        actual_after = to_grams_str(get("actual_after") or get("actual") or "-", header_hint)

        uncert_header = mapping.get("uncertainty") or ""
        uncertainty = get("uncertainty")
        # Detect ± kg → convert to grams if the header says kg
        if uncertainty is not None:
            if "kg" in str(uncert_header).lower():
                uncertainty = to_grams_str(uncertainty, "kg")
            else:
                uncertainty = clean_num_str(uncertainty)
        else:
            uncertainty = "-"

        serial_clean = (serial_raw or "").strip()
        if serial_clean in {"", "-", "–", "—", "None"}:
            # If this page is a set page, generate serial as W-<n>.<k>
            if set_series:
                serial_clean = f"{set_series}.{ridx + 1 + row_index_offset}"
            else:
                # leave blank rows out
                continue

        series = series_from_serial(serial_clean) or (set_series or "")

        rows.append(RowOut(
            serialNumber=serial_clean,
            nominalValueG=nominal if nominal else "-",
            actualBeforeG=actual_before if actual_before else "-",
            actualAfterG=actual_after if actual_after else "-",
            uncertaintyG=uncertainty if uncertainty else "-",
            series=series
        ))
    return rows


# ---------- PHASE C: counts & validation ----------
def observed_counts(rows: List[RowOut]) -> Dict[str, Any]:
    singles: Dict[str, int] = {}
    set_ids: set = set()
    for r in rows:
        # set rows are those whose series matches ^W[- ]?\d+$ or ^WOW-S\d+$
        if re.match(r"^W[- ]?\d+$", r.series or "", flags=re.I) or re.match(r"^WOW-S\d+$", r.series or "", flags=re.I):
            set_ids.add(r.series.upper().replace(" ", ""))
        else:
            if r.nominalValueG != "-" and r.nominalValueG != "":
                singles[r.nominalValueG] = singles.get(r.nominalValueG, 0) + 1
    return {"singlePieces": singles, "sets": sorted(list(set_ids))}

def compare_expected_observed(expected: Dict[str, Any], observed: Dict[str, Any]) -> List[str]:
    problems = []
    exp_single = {e["nominalG"]: e["count"] for e in expected.get("singlePieces", [])}
    for g, cnt in exp_single.items():
        if observed["singlePieces"].get(g, 0) != cnt:
            problems.append(f"Single pieces {g} g: expected {cnt}, observed {observed['singlePieces'].get(g, 0)}")
    exp_sets = {e["setId"]: e["count"] for e in expected.get("sets", [])}
    # Usually 1 each; we just check presence
    for sid in exp_sets.keys():
        if sid not in observed["sets"]:
            problems.append(f"Set {sid}: expected present, but not observed")
    return problems


# ---------- Header metadata extraction ----------
def extract_certificate_header(text: str) -> Dict[str, str]:
    out = {"certificateNo": "", "weightSet": "", "issuingLab": "", "issueDate": "", "expiryDate": ""}
    t = re.sub(r"\s+", " ", text or "")
    m = re.search(r"(Calibration certificate number|Certificate No\.?)[:\s]*([A-Za-z0-9./\- ]+)", t, flags=re.I)
    if m:
        out["certificateNo"] = m.group(2).strip()
    # Weight set: try to capture "Calibration of: A set of weights" or first set id on page
    m2 = re.search(r"Calibration of[:\s]*(.+?)(?: Calibrated| Environmental| Procedure| Traceability| Results)", t, flags=re.I)
    if m2:
        out["weightSet"] = m2.group(1).strip()
    # Issuing lab: look for SANAS logo lines or company header
    m3 = re.search(r"(WOW Calibration|Weighing Instrument Services|CM LAB|NRCS|National Regulator).*?(PTY|Ltd|LAB|Services|Laboratory)?", t, flags=re.I)
    if m3:
        out["issuingLab"] = m3.group(0).strip()
    # Issue Date
    m4 = re.search(r"(Date of issue|Date issued)[:\s]*([0-9]{1,2}[ /-][A-Za-z]{3,9}[ /-][0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})", t, flags=re.I)
    if m4:
        out["issueDate"] = m4.group(2).strip()
    # Expiry (if explicitly present)
    m5 = re.search(r"(Expiry|Valid until|Expiry date)[:\s]*([0-9]{1,2}[ /-][A-Za-z]{3,9}[ /-][0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})", t, flags=re.I)
    if m5:
        out["expiryDate"] = m5.group(2).strip()
    
    # WIS S1/S2: pull set id from 'SET WOW S#' if present
    m2b = re.search(r"\bSET\s+WOW\s*(S\s*0*\d+)\b", t, flags=re.I)
    if m2b and not out.get("weightSet"):
        out["weightSet"] = f"WOW-{m2b.group(1).replace(' ', '')}"
    
    return out


# ---------- End-to-end per-file pipeline ----------
def process_pdf(pdf_bytes: bytes) -> Tuple[Dict[str, Any], List[RowOut], List[str]]:
    # Gather full document text for Phase A and header metadata
    full_text = ""
    if HAVE_PDFPLUMBER:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    full_text += (page.extract_text() or "") + "\n"
        except Exception:
            full_text = ""

    expected = parse_expected_counts(full_text)
    all_rows: List[RowOut] = []

    # 1) Camelot
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        for page_no, df in extract_tables_with_camelot(tmp.name):
            # try to get page text for set header detection
            page_text = ""
            if HAVE_PDFPLUMBER:
                try:
                    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                        page_text = (pdf.pages[page_no-1].extract_text() or "")
                except Exception:
                    page_text = ""
            all_rows.extend(rows_from_dataframe(df, page_text))

    # 2) pdfplumber tables (if Camelot missed some)
    for page_no, df, page_text in extract_tables_with_pdfplumber(pdf_bytes):
        all_rows.extend(rows_from_dataframe(df, page_text))

    # 3) OCR fallback for any remaining pages
    for page_no, dfs, page_text in ocr_tables_from_page_images(pdf_bytes):
        for df in dfs:
            all_rows.extend(rows_from_dataframe(df, page_text))

    # De-duplicate exact duplicate rows (can happen when both Camelot & pdfplumber hit same table)
    uniq = []
    seen = set()
    for r in all_rows:
        key = tuple(asdict(r).items())
        if key not in seen:
            seen.add(key)
            uniq.append(r)

    obs = observed_counts(uniq)
    problems = compare_expected_observed(expected, obs)

    # Header metadata
    header_meta = extract_certificate_header(full_text)

    return header_meta, uniq, problems


# ================== STREAMLIT UI ==================
st.set_page_config(page_title="SANAS Cert Extractor", layout="wide")
st.title("SANAS Calibration Certificate — Page-by-Page Extractor")

st.caption("Robust, layout-aware extraction with inventory checks (inspired by OmniDocBench).")

st.sidebar.subheader("How it works")
st.sidebar.markdown(
    "- Tries **Camelot** for vector PDFs → **pdfplumber** for text → **OCR + img2table** if scanned.\n"
    "- Parses 'Calibration of:' to build expected counts (single pieces & sets).\n"
    "- Extracts every table row, normalises units to grams, generates set serials when blank.\n"
    "- Validates expected vs observed; download strict JSON."
)

uploaded = st.file_uploader("Upload one or more PDF certificates", type=["pdf"], accept_multiple_files=True)

if not uploaded:
    st.info("Upload SANAS calibration certificates (PDF) to begin.")
else:
    for uf in uploaded:
        st.header(f"📄 {uf.name}")
        pdf_bytes = uf.read()

        # Detect format
        text_p1 = first_page_text(pdf_bytes)
        format_tag = "WIS_S_v1" if detect_WIS_S_v1(text_p1) else "generic"
        st.caption(f"Format detected: **{format_tag}**")
        
        # Debug: show first page text preview
        if format_tag == "WIS_S_v1":
            st.info(f"WIS format detected! First page text preview: {text_p1[:200]}...")

        with st.spinner("Extracting…"):
            header, rows, problems = process_pdf(pdf_bytes)

        # Debug: show extraction results
        st.info(f"Extraction complete: {len(rows)} rows found, {len(problems)} problems")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Certificate header")
            st.json(header)
        with col2:
            st.subheader("Validation")
            if problems:
                for p in problems:
                    st.error(p)
            else:
                st.success("Expected counts match observed rows (or no expectations were found).")

        # Show rows preview
        st.subheader("Extracted rows")
        if rows:
            df_rows = pd.DataFrame([asdict(r) for r in rows])
            st.dataframe(df_rows, use_container_width=True, hide_index=True)
        else:
            st.warning("No rows extracted. This might indicate an issue with table detection or OCR.")
            # Show debug info for troubleshooting
            st.subheader("Debug: Table extraction attempts")
            st.text(f"PDF size: {len(pdf_bytes)} bytes")
            st.text(f"Format detected: {format_tag}")
            st.text(f"First page text length: {len(text_p1)} characters")

        # JSON download (STRICT schema)
        payload = {"rows": [asdict(r) for r in rows]}
        st.download_button(
            label="⬇️ Download JSON (rows)",
            data=json.dumps(payload, ensure_ascii=False, indent=2),
            file_name=(uf.name.rsplit(".",1)[0] + "_rows.json"),
            mime="application/json"
        )

        # Optional: download header metadata JSON
        st.download_button(
            label="⬇️ Download JSON (certificate header)",
            data=json.dumps(header, ensure_ascii=False, indent=2),
            file_name=(uf.name.rsplit(".",1)[0] + "_header.json"),
            mime="application/json"
        )

st.caption("Tip: If you see mismatches, check that poppler & Tesseract are installed so the OCR fallback can run.")
