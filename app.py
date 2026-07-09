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

st.set_page_config(page_title="Monitoring Klaim - Hasil Split", layout="wide")


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
st.title("📊 Monitoring Klaim - Hasil Split per Principal")

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

    header = st.columns([1, 2, 3, 2, 2, 2])
    header[0].markdown("**Tahun**")
    header[1].markdown("**Principal**")
    header[2].markdown("**Tipe (sheet)**")
    header[3].markdown("**Jumlah Baris**")
    header[4].markdown("**Jumlah SALAH**")
    header[5].markdown("**File**")

    for row in filtered:
        c = st.columns([1, 2, 3, 2, 2, 2])
        c[0].write(row["tahun"])
        c[1].write(row["principal"])
        c[2].write(row["tipe"])
        c[3].write(f"{row['jumlah_baris']:,}")
        c[4].write(f"{row['jumlah_salah']:,}")
        url = get_download_url(row["file_path"])
        c[5].markdown(f"[⬇ {row['file_name']}]({url})")

st.caption("Data otomatis diperbarui setiap kali JALANKAN_SPLIT.bat dijalankan di sisi lokal.")
