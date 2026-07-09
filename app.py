"""
app.py - Web viewer hasil SPLIT (merge_excel + split_by_principal) yang
disimpan di Supabase.

Filter berjenjang: TAHUN -> PRINCIPAL -> TIPE
Menampilkan tabel ringkasan (jumlah baris, jumlah salah) + tombol download
file .xlsx langsung dari Supabase Storage.

Cara jalanin lokal:
    pip install streamlit supabase
    streamlit run app.py

Di Streamlit Cloud, isi Settings -> Secrets dengan:
    SUPABASE_URL = "https://xxxx.supabase.co"
    SUPABASE_ANON_KEY = "xxxxx"
"""

import streamlit as st
from supabase import create_client

TABLE_NAME = "split_results"

st.set_page_config(page_title="Monitoring Klaim - Hasil Split", layout="wide", page_icon="📊")

# ─────────────────────────────────────────────
# Custom styling - tema merah
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #E30613 0%, #B00410 100%);
        padding: 24px 32px;
        border-radius: 10px;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(227, 6, 19, 0.25);
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 28px;
    }
    .main-header p {
        color: #FFE5E5;
        margin: 4px 0 0 0;
        font-size: 14px;
    }
    div[data-testid="stMetric"] {
        background-color: #FFF1F1;
        border: 1px solid #F5B5B8;
        border-left: 5px solid #E30613;
        border-radius: 8px;
        padding: 14px 16px;
    }
    div[data-testid="stMetricValue"] {
        color: #B00410;
    }
    .styled-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    .styled-table thead tr {
        background-color: #E30613;
        color: white;
        text-align: left;
    }
    .styled-table th, .styled-table td {
        padding: 10px 14px;
        border: 1px solid #F0D0D0;
    }
    .styled-table tbody tr:nth-child(even) {
        background-color: #FFF6F6;
    }
    .styled-table tbody tr:hover {
        background-color: #FFE0E0;
    }
    .styled-table a {
        color: #B00410;
        font-weight: 600;
        text-decoration: none;
    }
    .styled-table a:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

LOGO_URL = "https://cdn.jsdelivr.net/gh/otcarklaim/monitoring-claim@main/logo.png"

st.markdown(f"""
<div class="main-header">
    <h1><img src="{LOGO_URL}" style="height:70px; vertical-align:middle; margin-right:14px;">Monitoring Klaim - Hasil Split per Principal</h1>
    <p>Data diperbarui otomatis setiap proses split dijalankan</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Koneksi ke Supabase (pakai ANON key -> read-only)
# ─────────────────────────────────────────────
@st.cache_resource
def get_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)


@st.cache_data(ttl=60)
def load_data():
    """Ambil semua data dari tabel split_results."""
    supabase = get_client()
    resp = supabase.table(TABLE_NAME).select("*").execute()
    return resp.data or []


def get_download_url(file_path: str) -> str:
    supabase = get_client()
    return supabase.storage.from_("split-files").get_public_url(file_path)


# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
data = load_data()

if not data:
    st.warning("Belum ada data. Jalankan JALANKAN_SPLIT.bat di sisi lokal dulu.")
    st.stop()

col1, col2, col3 = st.columns(3)

# --- Filter 1: TAHUN ---
tahun_list = sorted({row["tahun"] for row in data}, reverse=True)
with col1:
    tahun_pilihan = st.selectbox("Tahun", ["(Semua)"] + tahun_list)

filtered = data if tahun_pilihan == "(Semua)" else [
    row for row in data if row["tahun"] == tahun_pilihan
]

# --- Filter 2: PRINCIPAL (tergantung tahun yang dipilih) ---
principal_list = sorted({row["principal"] for row in filtered})
with col2:
    principal_pilihan = st.selectbox("Principal", ["(Semua)"] + principal_list)

filtered = filtered if principal_pilihan == "(Semua)" else [
    row for row in filtered if row["principal"] == principal_pilihan
]

# --- Filter 3: TIPE (tergantung tahun + principal yang dipilih) ---
tipe_list = sorted({row["tipe"] for row in filtered})
with col3:
    tipe_pilihan = st.selectbox("Tipe", ["(Semua)"] + tipe_list)

filtered = filtered if tipe_pilihan == "(Semua)" else [
    row for row in filtered if row["tipe"] == tipe_pilihan
]

st.divider()

# --- Ringkasan angka ---
total_baris = sum(row["jumlah_baris"] for row in filtered)
total_salah = sum(row["jumlah_salah"] for row in filtered)

m1, m2, m3 = st.columns(3)
m1.metric("Jumlah Sheet", len(filtered))
m2.metric("Total Baris", f"{total_baris:,}")
m3.metric("Total SALAH", f"{total_salah:,}")

st.divider()

# --- Tabel + tombol download ---
if not filtered:
    st.info("Tidak ada data yang cocok dengan filter ini.")
else:
    # Urutkan biar rapi: tahun desc, principal, tipe
    filtered.sort(key=lambda r: (r["tahun"], r["principal"], r["tipe"]), reverse=True)

    rows_html = ""
    for row in filtered:
        url = get_download_url(row["file_path"])
        rows_html += (
            "<tr>"
            f"<td>{row['tahun']}</td>"
            f"<td>{row['principal']}</td>"
            f"<td>{row['tipe']}</td>"
            f"<td>{row['jumlah_baris']:,}</td>"
            f"<td>{row['jumlah_salah']:,}</td>"
            f'<td><a href="{url}" target="_blank">⬇ {row["file_name"]}</a></td>'
            "</tr>"
        )

    table_html = (
        '<table class="styled-table">'
        "<thead><tr>"
        "<th>Tahun</th><th>Principal</th><th>Tipe (sheet)</th>"
        "<th>Jumlah Baris</th><th>Jumlah SALAH</th><th>File</th>"
        "</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table>"
    )
    st.markdown(table_html, unsafe_allow_html=True)

st.caption("Data otomatis diperbarui setiap kali JALANKAN_SPLIT.bat dijalankan di sisi lokal.")
