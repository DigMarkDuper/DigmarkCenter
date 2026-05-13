import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import base64
import datetime
import sys

# =====================================================================
# SYSTEM OPTIMIZATION: BATCH LOADING & GLOBAL CACHING
# =====================================================================

@st.cache_data(ttl=600)
def fetch_all_master_data():
    """Menarik semua tab sekaligus dalam 1 koneksi untuk efisiensi API"""
    client = init_connection()
    if not client: return None
    try:
        master = client.open("MASTER DATA DIGITAL MARKETING 2.0")
        def get_df(idx):
            try:
                data = master.get_worksheet(idx).get_all_records()
                return pd.DataFrame(data) if data else pd.DataFrame()
            except: return pd.DataFrame()
        
        return {
            0: get_df(0), 1: get_df(1), 2: get_df(2), 
            3: get_df(3), 4: get_df(4), 6: get_df(6), 
            7: get_df(7), 8: get_df(8)
        }
    except Exception as e:
        st.error(f"Gagal Sinkronisasi Master: {e}")
        return None

# Override fungsi load lama agar mengambil dari bundle (tanpa merubah nama fungsi)
def get_from_bundle(idx):
    if 'bundle' not in st.session_state or st.session_state.bundle is None:
        st.session_state.bundle = fetch_all_master_data()
    return st.session_state.bundle.get(idx, pd.DataFrame()).copy()

def load_sosmed(): return get_from_bundle(0)
def load_website(): return get_from_bundle(1)
def load_insight(): return get_from_bundle(2)
def load_wa_admin(): 
    df = get_from_bundle(3)
    # Tetap jalankan logika pembersihan data hantu yang spesifik di sini
    kolom_penting = [col for col in ['Tanggal Masuk', 'No Hp', 'Status'] if col in df.columns]
    if kolom_penting: df = df.dropna(subset=kolom_penting, how='all')
    return df
def load_database_nomor(): return get_from_bundle(4)
@st.cache_resource
def init_connection():
    """Membuka kunci akses ke Google Sheets menggunakan Secrets"""
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n").strip()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Koneksi Gagal: {e}")
        return None

def append_sheet_rows(sheet_index, all_data_list):
    """Fungsi untuk mengirim BANYAK baris sekaligus dalam satu kali panggil API"""
    client = init_connection()
    if client:
        try:
            spreadsheet = client.open("MASTER DATA DIGITAL MARKETING 2.0")
            sheet = spreadsheet.get_worksheet(sheet_index)
            # Menggunakan append_rows (dengan 's') untuk batch update
            cleaned_data = [[str(x) if not isinstance(x, (int, float)) else x for x in row] for row in all_data_list]            
            sheet.append_rows(cleaned_data, value_input_option='USER_ENTERED')
        except Exception as e:
            st.error(f"Gagal batch update ke Google Sheets: {e}")

def append_rows_to_crm(bulk_data):
    try:
        # 1. Pastikan ID Spreadsheet benar
        SPREADSHEET_ID = "1v0SLw92qqkgs76qSpjb7xScYpVoJ8Ahc3fFIZ2u9HRs" 
        
        # 2. Buka Spreadsheet
        # Gunakan 'sh' atau variabel client yang sudah Mas set di awal backend
        sh = client.open_by_key(SPREADSHEET_ID)
        
        # 3. Buka Sheet berdasarkan NAMA (Bukan Indeks) agar lebih akurat
        # Pastikan namanya di Google Sheets Mas persis: "DATABASE NOMOR"
        sheet = sh.worksheet("DATABASE NOMOR")
        
        # 4. Kirim Data
        sheet.append_rows(bulk_data, value_input_option='USER_ENTERED')
        return True
    except Exception as e:
        # Cek pesan error ini di terminal VS Code Mas!
        print(f"❌ KENDALA BACKEND: {e}")
        return False
            
def sync_leads_to_crm():
    try:
        df_wa = load_wa_admin()    # Tab 4
        df_crm = load_database_nomor() # Tab 5
        
        if df_wa.empty:
            st.warning("⚠️ Laporan WA Admin kosong.")
            return

        # --- LOGIKA STANDARISASI ---
        def clean_phone(val):
            num = str(val).strip().replace('+', '').replace(' ', '').replace('-', '')
            if num.startswith('0'): return '62' + num[1:]
            if num.startswith('8'): return '62' + num
            return num

        df_wa['No Hp'] = df_wa['No Hp'].apply(clean_phone)
        df_wa = df_wa.drop_duplicates(subset=['No Hp'], keep='last')

        mekari_col = next((c for c in df_wa.columns if 'Mekari' in c), None)
        if not mekari_col:
            st.error("❌ Kolom Mekari Tag tidak ditemukan di WA Admin.")
            return
            
        # 1. FILTER WHITELIST (Tag yang diizinkan)
        valid_tags = ["Hot Lead", "Warm Lead", "Cold Lead", "Pending Form - L1", "Pending Form - L2", "Re-engagement", "Future Prospect", "Form Submitted", "Sales Progress"]
        new_leads = df_wa[df_wa[mekari_col].isin(valid_tags)].copy()
        
        # 2. FILTER BLACKLIST - NOT ELIGIBLE (Lapisan Keamanan Tambahan)
        new_leads = new_leads[~new_leads[mekari_col].astype(str).str.contains("Not Eligible|not eligible", case=False, na=False)]
        
        # 3. FILTER BLACKLIST - STATUS WITHDRAW
        # Mencari apakah ada kolom bernama 'Status' di data WA Admin
        status_col = next((c for c in new_leads.columns if 'Status' in c or 'status' in c), None)
        if status_col:
            new_leads = new_leads[~new_leads[status_col].astype(str).str.contains("Withdraw|withdraw", case=False, na=False)]

        # --- LOGIKA ANTI DUPLIKASI DENGAN CRM ---
        if not df_crm.empty:
            existing_nos = df_crm['No Hp'].astype(str).tolist()
            new_leads = new_leads[~new_leads['No Hp'].isin(existing_nos)]

        if new_leads.empty:
            st.info("ℹ️ Tidak ada data baru untuk ditarik.")
            return

        # --- PROSES BATCHING DENGAN MAPPING ASAL ---
        all_new_rows = [] 
        current_crm_len = len(df_crm)
        
        for idx, row in new_leads.reset_index(drop=True).iterrows():
            # MENGAMBIL 'Asal' UNTUK DIMASUKKAN KE 'Domisili'
            asal_data = row.get('Asal', row.get('Domisili', '')) 
            
            data_to_append = [
                current_crm_len + idx + 1,      # 1. No
                row.get('No Hp', ''),           # 2. No Hp
                row.get('Nama', ''),             # 3. Nama
                asal_data,                       # 4. Domisili (Diambil dari kolom Asal)
                '', '',                          # 5. Tgl Lahir, 6. Usia
                row.get('Kategori', 'Siswa'),    # 7. Kategori
                '',                              # 8. Keterangan Form
                datetime.datetime.now().strftime('%Y-%m-%d'), # 9. Tgl Masuk
                row.get(mekari_col, ''),         # 10. Mekari Tag
                '', '', '', '',                  # 11-14. Treatment
                'PENDING',                       # 15. Status
                '',                              # 16. Updated Status
                ''                               # 17. Catatan
            ]
            all_new_rows.append(data_to_append)

        if all_new_rows:
            append_sheet_rows(4, all_new_rows) 
            st.success(f"✅ Berhasil menarik {len(all_new_rows)} Prospek Unik (Telah melewati filter Not Eligible & Withdraw)!")
            st.cache_data.clear()
            st.rerun()
            
    except Exception as e:
        st.error(f"Gagal Sinkronisasi: {e}")
# =====================================================================
# 1. KONFIGURASI GLOBAL & NAVIGASI
# =====================================================================
st.set_page_config(page_title="Digmark Command Center", layout="wide", page_icon="🚀")

# Inisialisasi Session State Halaman agar navigasi lancar
if 'page' not in st.session_state:
    st.session_state.page = "🏠 HOMEPAGE"

def go_to_page(page_name):
    st.session_state.page = page_name

page = st.session_state.page

LOGO_URL = "https://www.dutapersadajogja.com/assets/img/logo.png" 
BRAND_BLUE = "#005696"
BRAND_YELLOW = "#FDB813"
TEXT_BLACK = "#000000" 
BG_WHITE = "#FFFFFF"

# =====================================================================
# 2. SISTEM KEAMANAN & VISUAL (URUTAN DIPERBAIKI)
# =====================================================================

# A. Letakkan link logo di paling atas agar terbaca semua fungsi
LOGO_URL = "https://www.dutapersadajogja.com/assets/img/logo.png"

# B. Definisi fungsi background HARUS di atas agar tidak NameError
def set_bg_local(main_bg):
    try:
        with open(main_bg, "rb") as f:
            bin_str = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/png;base64,{bin_str}");
                background-size: cover;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except:
        pass

# C. Fungsi Login
def check_password():
    if st.session_state.get("password_correct"):
        return True
    
    # Sekarang set_bg_local sudah dikenal oleh sistem
    set_bg_local('bg.png') 
    
    _, col_mid, _ = st.columns([1, 3, 1])
    with col_mid:
        # Tampilan Logo (Sederhana, tanpa kotak putih/transparan)
        st.markdown(f'''
            <div style="text-align: center; margin-top: 50px;">
                <img src="{LOGO_URL}" width="200" style="mix-blend-mode: multiply;">
            </div>
        ''', unsafe_allow_html=True)
        
        # Judul (Langsung di atas background)
        st.markdown('<h2 style="text-align: center; color: #8B0000; margin-bottom: 0;">DIGITAL MARKETING DASHBOARD</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; color: #333; font-weight: bold;">LPK Duta Persada Yogyakarta</p>', unsafe_allow_html=True)
        
        # Form Login Standar
        with st.form("login_form"):
            u_name = st.text_input("Username").strip().lower()
            u_pass = st.text_input("Password", type="password")
            if st.form_submit_button("MASUK SISTEM", use_container_width=True):
                if "credentials" in st.secrets and u_name in st.secrets["credentials"] and st.secrets["credentials"][u_name] == u_pass:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: 
                    st.error("Username atau Password salah!")
    return False

# D. EKSEKUSI: Panggil fungsi login
if not check_password():
    st.stop()

# E. Pasang kembali background untuk halaman utama
set_bg_local('bg.png')
# =====================================================================
# 3. KONEKSI & LOAD DATA
# =====================================================================
@st.cache_resource
def init_connection():
    try:
        creds_info = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n").strip()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Koneksi Gagal: {e}")
        return None

def get_raw_df(sheet_index):
    client = init_connection()
    if client:
        try:
            spreadsheet = client.open("MASTER DATA DIGITAL MARKETING 2.0")
            sheet = spreadsheet.get_worksheet(sheet_index)
            return pd.DataFrame(sheet.get_all_records())
        except: return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=5)
def load_sosmed():
    df = get_raw_df(0)
    if not df.empty and 'Tanggal Deadline' in df.columns:
        df['Tanggal Deadline'] = pd.to_datetime(df['Tanggal Deadline'], dayfirst=True, errors='coerce')
        df['Bulan-Deadline'] = df['Tanggal Deadline'].dt.strftime('%B %Y')
        for c in ['IG', 'YT', 'TIKTOK']:
            if c in df.columns: df[c] = df[c].apply(lambda x: True if str(x).upper() in ['TRUE', 'V', '1'] else False)
    return df

@st.cache_data(ttl=5)
def load_website():
    df = get_raw_df(1)
    if not df.empty and 'Deadline' in df.columns:
        df['Tanggal Filter'] = pd.to_datetime(df['Deadline'], dayfirst=True, errors='coerce')
        df['Bulan-Deadline'] = df['Tanggal Filter'].dt.strftime('%B %Y')
    return df

@st.cache_data(ttl=5)
def load_insight():
    df = get_raw_df(2)
    cols = ['View', 'Reach', 'Interaction', 'Link Clicks', 'Profile Visit', 'Follow']
    for c in cols:
        if not df.empty and c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    return df

@st.cache_data(ttl=5)
def load_wa_admin():
    df = get_raw_df(3)
    if not df.empty and 'Tanggal Masuk' in df.columns:
        df['Tanggal Filter'] = pd.to_datetime(df['Tanggal Masuk'], dayfirst=True, errors='coerce')
        df['Bulan-Masuk'] = df['Tanggal Filter'].dt.strftime('%B %Y')
    return df

@st.cache_data(ttl=5)
def load_database_nomor():
    df = get_raw_df(4)
    if not df.empty:
        
        if 'No Hp' in df.columns:
            def format_whatsapp(val):
                num = str(val).strip().replace('+', '').replace(' ', '').replace('-', '')
                if num.startswith('0'):
                    return '62' + num[1:]
                elif num.startswith('8'):
                    return '62' + num
                return num
            
            df['No Hp'] = df['No Hp'].apply(format_whatsapp)
            
        for col in ['Tanggal Lahir', 'Tanggal Masuk Database', 'Tanggal Treatment 1', 'Tanggal Treatment 2']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
    return df
def append_sheet_row(sheet_index, data_list):
    """Fungsi untuk menambah baris baru ke Spreadsheet"""
    client = init_connection() # Memanggil 'kunci' koneksi Mas
    if client:
        try:
            spreadsheet = client.open("MASTER DATA DIGITAL MARKETING 2.0")
            sheet = spreadsheet.get_worksheet(sheet_index)
            sheet.append_row(data_list)
        except Exception as e:
            st.error(f"Gagal menambah baris: {e}")

def update_sheet_cell(sheet_index, row_index, column_name, new_value):
    """Fungsi untuk mengupdate satu sel spesifik (untuk fitur edit)"""
    client = init_connection()
    if client:
        try:
            spreadsheet = client.open("MASTER DATA DIGITAL MARKETING 2.0")
            sheet = spreadsheet.get_worksheet(sheet_index)
            # Cari posisi kolom berdasarkan nama header
            header = sheet.row_values(1)
            col_idx = header.index(column_name) + 1
            # Row index di gspread dimulai dari 2 (karena baris 1 header)
            sheet.update_cell(row_index + 2, col_idx, new_value)
        except Exception as e:
            st.error(f"Gagal update data: {e}")

# =====================================================================
# 4. FUNGSI WRITE-BACK (UPDATE & APPEND)
# =====================================================================
def update_sheet_cell(sheet_index, row_index, column_name, new_value):
    client = init_connection()
    if client:
        try:
            ss = client.open("MASTER DATA DIGITAL MARKETING 2.0")
            sheet = ss.get_worksheet(sheet_index)
            headers = sheet.row_values(1)
            if column_name in headers:
                col_idx = headers.index(column_name) + 1
                sheet.update_cell(row_index + 2, col_idx, str(new_value))
                st.cache_data.clear()
                return True
        except: return False
    return False

def batch_append_rows(sheet_index, data_list):
    if not data_list: return False
    client = init_connection()
    if client:
        try:
            ss = client.open("MASTER DATA DIGITAL MARKETING 2.0")
            sheet = ss.get_worksheet(sheet_index)
            sheet.append_rows(data_list)
            st.cache_data.clear()
            return True
        except: return False
    return False

# =====================================================================
# 5. GLOBAL STYLING
# =====================================================================
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Work+Sans:wght@400;600;800&display=swap');
    html, body, [data-testid="stAppViewContainer"], .stMarkdown {{ font-family: 'Work Sans', sans-serif !important; }}
    .feature-header {{
        background-color: {BRAND_BLUE}; color: white; padding: 15px; border-radius: 8px; 
        border-left: 10px solid {BRAND_YELLOW}; font-size: 22px; font-weight: 800; margin-bottom: 20px;
    }}
    [data-testid="stVerticalBlockBorderWrapper"] {{
        box-shadow: 0 12px 28px rgba(0,0,0,0.1) !important; border-radius: 15px !important;
        background-color: white !important; padding: 15px !important;
    }}
    </style>
""", unsafe_allow_html=True)

def create_square_card(icon, title, subtitle, target_page, button_key):
    with st.container(border=True):
        st.markdown(f"""
            <div style="text-align: center; padding: 10px 0px;">
                <div style="font-size: 60px;">{icon}</div>
                <div style="font-weight: 800; color: {BRAND_BLUE};">{title}</div>
                <div style="font-size: 11px; color: #666; min-height:30px;">{subtitle}</div>
            </div>
        """, unsafe_allow_html=True)
        st.button("Masuk ➔", key=button_key, use_container_width=True, on_click=go_to_page, args=(target_page,))
# =====================================================================
# 6. LOGIKA HALAMAN
# =====================================================================

# Tombol Kembali Global
if page != "🏠 HOMEPAGE":
    if st.button("⬅️ KEMBALI KE HOMEPAGE"):
        go_to_page("🏠 HOMEPAGE")
        st.rerun()

# --- HALAMAN 0: HOMEPAGE ---
if page == "🏠 HOMEPAGE":
    # 1. CSS CUSTOM (Tetap rapi dan modern)
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Work+Sans:wght@300;400;600;800&display=swap');
        
        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Work Sans', sans-serif !important;
        }

        .kpi-card {
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            border: 1px solid #F0F2F6;
            display: flex;
            align-items: center;
            gap: 15px;
            transition: all 0.3s ease;
        }
        .kpi-card:hover { 
            transform: translateY(-5px); 
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        }
        
        [data-testid="stVerticalBlockBorderWrapper"] {
            box-shadow: 0 10px 30px rgba(0,0,0,0.08) !important;
            border-radius: 15px !important;
            background-color: white !important;
            padding: 20px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # 2. HEADER & NAVIGASI (DIBAGI 2 BARIS)
    st.markdown('<div class="feature-header" style="text-align: center; margin-bottom:20px;">🚀 DIGITAL MARKETING COMMAND CENTER</div>', unsafe_allow_html=True)
    
    def create_square_card(icon, title, subtitle, target_page, button_key):
        with st.container(border=True):
            st.markdown(f"""
                <div style="text-align: center; padding: 10px 0px;">
                    <div style="font-size: 45px; margin-bottom: 10px;">{icon}</div>
                    <div style="font-size: 14px; font-weight: 800; color: #1E3A8A; text-transform: uppercase;">{title}</div>
                    <div style="font-size: 11px; color: #666; margin-top: 5px; min-height: 35px;">{subtitle}</div>
                </div>
            """, unsafe_allow_html=True)
            st.button("Masuk ➔", key=button_key, use_container_width=True, on_click=go_to_page, args=(target_page,))

    # Data 7 Menu Navigasi (termasuk Ads Analytics)
    nav_data = [
        ("📱", "Sosmed", "Jadwal PIC", "📱 SOSIAL MEDIA", "btn_sos"),
        ("🌐", "Website", "SEO Audit", "🌐 WEBSITE AUDIT", "btn_web"),
        ("📈", "Insight", "Analytics", "📈 INSIGHTS & ANALYTICS", "btn_in"),
        ("💬", "WA Admin", "Closing Funnel", "💬 WA ADMIN REPORT", "btn_wa"),
        ("📂", "Database", "CRM Kontak", "📂 DATABASE NOMOR", "btn_db"),
        ("📥", "DM Sosmed", "Tracker Inbox", "📱 DM SOSMED", "btn_dm"),
        ("🎯", "Ads Report", "ROI & CPL", "📈 ADS ANALYTICS", "btn_ads") # Menu baru Halaman 7
    ]

    # BARIS 1: 4 Menu Pertama
    cols1 = st.columns(4)
    for col, data in zip(cols1, nav_data[:4]):
        with col: 
            create_square_card(*data)

    st.markdown("<br>", unsafe_allow_html=True) # Jarak antara baris atas dan bawah

    # BARIS 2: 3 Menu Sisa (Kolom ke-4 akan otomatis kosong)
    cols2 = st.columns(4)
    for col, data in zip(cols2, nav_data[4:]):
        with col: 
            create_square_card(*data)

    st.markdown("---")

    # 3. EXECUTIVE SUMMARY (MENGGUNAKAN NAMA VARIABEL ASLI MAS)
    try:
        # Load Data dengan nama variabel asli Mas
        df_wa_home = load_wa_admin()
        df_in_home = load_insight()
        df_sos_home = load_sosmed()
        df_web_home = load_website()

        # Konfigurasi Waktu
        sekarang = datetime.datetime.now()
        bulan_ini, tahun_ini = sekarang.month, sekarang.year
        
        last_month_date = sekarang.replace(day=1) - datetime.timedelta(days=1)
        bulan_lalu, tahun_bulan_lalu = last_month_date.month, last_month_date.year

        # Helper Filter Waktu (Support variabel _home)
        def filter_waktu_ketat(df, m, y):
            if df is None or df.empty: return pd.DataFrame()
            col_tgl = next((c for c in df.columns if any(k in str(c).lower() for k in ['tanggal', 'deadline', 'date'])), None)
            if col_tgl:
                df_t = df.copy()
                df_t['tgl_p'] = pd.to_datetime(df_t[col_tgl], errors='coerce', dayfirst=True)
                return df_t[(df_t['tgl_p'].dt.month == m) & (df_t['tgl_p'].dt.year == y)]
            return pd.DataFrame()

         # --- A. Perhitungan Leads & Closing (DIPERKETAT) ---
        total_leads, total_closing = 0, 0
        
        if not df_wa_home.empty:
            # 1. Bersihkan baris hantu (baris kosong dari Google Sheets)
            kolom_penting = [col for col in ['Tanggal Masuk', 'No Hp', 'Status'] if col in df_wa_home.columns]
            if kolom_penting:
                df_clean = df_wa_home.dropna(subset=kolom_penting, how='all').copy()
            else:
                df_clean = df_wa_home.copy()
                
            # Filter tambahan: Pastikan No Hp benar-benar ada (tidak hanya spasi atau nan)
            if 'No Hp' in df_clean.columns:
                df_clean = df_clean[df_clean['No Hp'].astype(str).str.strip() != ""]
                df_clean = df_clean[df_clean['No Hp'].astype(str).str.lower() != "nan"]
        
            # 2. Filter hanya untuk BULAN INI (Agar sinkron dengan dashboard bulanan)
            sekarang = datetime.datetime.now()
            df_bulan_ini = df_clean[
                (pd.to_datetime(df_clean['Tanggal Masuk'], dayfirst=True, errors='coerce').dt.month == sekarang.month) & 
                (pd.to_datetime(df_clean['Tanggal Masuk'], dayfirst=True, errors='coerce').dt.year == sekarang.year)
            ]
        
            # 3. Cari kolom Mekari & Status
            mekari_col = next((c for c in df_bulan_ini.columns if 'Mekari' in str(c)), None)
            status_col = next((c for c in df_bulan_ini.columns if 'Status' in str(c)), None)
        
            # 4. Hitung Leads Murni (Sesuai Logika Terbaru: Buang 3 Kategori Sampah)
            if mekari_col:
                tag_dibuang = ['Double Chat', 'Closed - Not Interested', 'Partnership']
                pola_hapus = '|'.join(tag_dibuang)
                df_leads_only = df_bulan_ini[~df_bulan_ini[mekari_col].astype(str).str.contains(pola_hapus, case=False, na=False)]
            else:
                df_leads_only = df_bulan_ini
        
            total_leads = len(df_leads_only)
        
            # 5. Hitung Closing dari Leads Murni tersebut
            if status_col:
                total_closing = len(df_leads_only[df_leads_only[status_col].astype(str).str.contains('Closing', case=False, na=False)])
        
                # --- B. Hutang Sosmed & Web ---
                df_sos_debt = filter_waktu_ketat(df_sos_home, bulan_lalu, tahun_bulan_lalu)
                sos_pending = len(df_sos_debt[df_sos_debt['PROSES'].astype(str).str.upper() != 'DONE']) if not df_sos_debt.empty else 0
                
                df_web_now = filter_waktu_ketat(df_web_home, bulan_ini, tahun_ini)
                web_pending = 0
                if not df_web_now.empty:
                    done_kw = ['DONE', 'TRUE', 'V', '1', 'POSTED', 'SELESAI', 'UPLOADED']
                    web_pending = len(df_web_now[~df_web_now['Status Post'].astype(str).str.upper().isin(done_kw)])

        # --- C. Performa Views & Reach ---
        total_view = df_in_home['View'].sum() if not df_in_home.empty else 0
        total_reach = df_in_home['Reach'].sum() if not df_in_home.empty else 0

        # --- D. Render KPI ---
        def render_kpi(icon, title, value):
            st.markdown(f"""
                <div class="kpi-card">
                    <div style="font-size: 24px;">{icon}</div>
                    <div>
                        <div style="font-size: 11px; color: #6B7280; font-weight: 600;">{title}</div>
                        <div style="font-size: 18px; font-weight: 800; color: #111827;">{value}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown('<div style="font-weight: 800; margin-bottom: 15px;">📊 RINGKASAN PERFORMA</div>', unsafe_allow_html=True)
        k1, k2, k3, k4 = st.columns(4)
        
        with k1: render_kpi("🎯", "Closing / Leads (Bulan Ini)", f"{total_closing} / {total_leads}")
        with k2: render_kpi("👀", "Views / Reach", f"{total_view:,.0f} / {total_reach:,.0f}")
        with k3: render_kpi("📱", f"Utang Sosmed ({bulan_lalu})", f"{sos_pending} Task")
        with k4: render_kpi("🌐", f"Utang Web ({bulan_ini})", f"{web_pending} Page")

    except Exception as e:
        st.error(f"⚠️ Gagal memuat metrik: {e}")

    st.markdown("---")
    # ==========================================================
    # 4. PETA PERSEBARAN & GRAFIK (FULL WIDTH & SHADOW)
    # ==========================================================
    st.markdown(f"<h3 style='color:{BRAND_BLUE}; font-size: 18px; margin-bottom: 10px; margin-top: 15px;'>🗺️ Peta Persebaran & Top Asal Prospek</h3>", unsafe_allow_html=True)
    
    try:
        # --- PERBAIKAN 1: Filter data mentah agar peta hanya menampilkan Leads Murni ---
        df_maps = df_wa_home.copy()
        
        # Bersihkan baris hantu
        kolom_penting = [col for col in ['Tanggal Masuk', 'No Hp', 'Status'] if col in df_maps.columns]
        if kolom_penting:
            df_maps = df_maps.dropna(subset=kolom_penting, how='all')
            
        # Buang tag sampah (Double Chat, Partnership, dll)
        mekari_col = next((c for c in df_maps.columns if 'Mekari' in str(c)), None)
        if mekari_col:
            tag_dibuang = ['Double Chat', 'Closed - Not Interested', 'Partnership']
            pola_hapus = '|'.join(tag_dibuang)
            df_maps = df_maps[~df_maps[mekari_col].astype(str).str.contains(pola_hapus, case=False, na=False)]

        # --- PERBAIKAN 2: Penyeragaman dan Perhitungan Lokasi ---
        asal_col = next((col for col in df_maps.columns if 'Asal' in str(col)), None)
        
        if asal_col and not df_maps.empty:
            # Seragamkan huruf besar di awal kata agar "jogja" dan "JOGJA" tergabung jadi satu
            df_maps[asal_col] = df_maps[asal_col].astype(str).str.strip().str.title()
            
            asal_counts = df_maps[asal_col].value_counts().reset_index()
            asal_counts.columns = ['Lokasi', 'Jumlah'] 
            
            # Pembersihan data "-" dan teks kosong (Ditambahkan 'Nan', 'None' dalam format Title Case)
            invalid_vals = ['', '-', 'Nan', 'None', 'Undefined', '#N/A']
            asal_counts = asal_counts[~asal_counts['Lokasi'].isin(invalid_vals)]
            
            indo_coords = {
                # DKI & BANTEN
                'jakarta': [-6.2088, 106.8456], 'jkt': [-6.2088, 106.8456], 'jabodetabek': [-6.2088, 106.8456],
                'tangerang': [-6.1702, 106.6403], 'serang': [-6.1200, 106.1503], 'cilegon': [-6.0174, 106.0201], 'pandeglang': [-6.3084, 106.1062], 'lebak': [-6.6346, 106.2238],
                # JAWA BARAT
                'bandung': [-6.9147, 107.6098], 'jabar': [-6.9147, 107.6098], 'bogor': [-6.5971, 106.8060], 'bekasi': [-6.2383, 106.9756], 'depok': [-6.4025, 106.7942],
                'cirebon': [-6.7320, 108.5523], 'tasikmalaya': [-7.3195, 108.2040], 'garut': [-7.2279, 107.9087], 'sukabumi': [-6.9275, 106.9426], 'cianjur': [-6.8168, 107.1425],
                'karawang': [-6.3227, 107.3113], 'purwakarta': [-6.5387, 107.4485], 'subang': [-6.5714, 107.7592], 'indramayu': [-6.3275, 108.3228],
                # JAWA TENGAH
                'semarang': [-6.9666, 110.4166], 'jateng': [-7.1509, 110.1402], 'solo': [-7.5666, 110.8166], 'surakarta': [-7.5666, 110.8166], 'magelang': [-7.4705, 110.2177], 
                'klaten': [-7.7056, 110.6031], 'purworejo': [-7.7126, 110.0091], 'kebumen': [-7.6672, 109.6515], 'boyolali': [-7.5172, 110.5950], 'sragen': [-7.4267, 111.0222],
                'wonogiri': [-7.8159, 110.9264], 'karanganyar': [-7.5959, 111.0049], 'sukoharjo': [-7.6766, 110.8351], 'temanggung': [-7.3134, 110.1718], 'wonosobo': [-7.3621, 109.9001],
                'purwokerto': [-7.4243, 109.2302], 'banyumas': [-7.5146, 109.2950], 'cilacap': [-7.7300, 109.0160], 'banjarnegara': [-7.3970, 109.6976], 'purbalingga': [-7.3879, 109.3622],
                'brebes': [-6.8690, 109.0435], 'tegal': [-6.8797, 109.1256], 'pemalang': [-6.8893, 109.3807], 'pekalongan': [-6.8887, 109.6753], 'batang': [-6.9142, 109.7314],
                'kendal': [-6.9197, 110.2017], 'demak': [-6.8948, 110.6385], 'jepara': [-6.5861, 110.6674], 'kudus': [-6.8048, 110.8405], 'pati': [-6.7559, 111.0370], 
                'rembang': [-6.7065, 111.3414], 'blora': [-7.1322, 111.4328], 'grobogan': [-7.0264, 110.9168], 'purwodadi': [-7.0868, 110.9158],
                # DIY
                'jogja': [-7.7955, 110.3694], 'yogyakarta': [-7.7955, 110.3694], 'diy': [-7.7955, 110.3694], 'yk': [-7.7955, 110.3694],
                'sleman': [-7.7306, 110.3481], 'bantul': [-7.8887, 110.3289], 'gunungkidul': [-7.9656, 110.5988], 'kulon': [-7.8282, 110.1243], 'kulonprogo': [-7.8282, 110.1243],
                # JAWA TIMUR
                'surabaya': [-7.2504, 112.7688], 'jatim': [-7.2504, 112.7688], 'malang': [-7.9797, 112.6304], 'madiun': [-7.6298, 111.5239],
                'banyuwangi': [-8.2192, 114.3692], 'jember': [-8.1721, 113.6995], 'lumajang': [-8.1332, 113.2226], 'probolinggo': [-7.7554, 113.2159], 'pasuruan': [-7.6449, 112.9033],
                'sidoarjo': [-7.4478, 112.7183], 'mojokerto': [-7.4726, 112.4338], 'jombang': [-7.5459, 112.2329], 'kediri': [-7.8228, 112.0119], 'blitar': [-8.0983, 112.1609],
                'tulungagung': [-8.0664, 111.9019], 'trenggalek': [-8.0494, 111.7107], 'ponorogo': [-7.8687, 111.4646], 'pacitan': [-8.1965, 111.1099], 'magetan': [-7.6534, 111.3304],
                'ngawi': [-7.4042, 111.4429], 'bojonegoro': [-7.1502, 111.8818], 'tuban': [-6.8966, 112.0632], 'lamongan': [-7.1185, 112.3150], 'gresik': [-7.1561, 112.6555],
                'bangkalan': [-7.0347, 112.7425], 'sampang': [-7.1866, 113.2435], 'pamekasan': [-7.1633, 113.4795], 'sumenep': [-7.0090, 113.8641], 'batu': [-7.8671, 112.5239],
                # LUAR JAWA
                'bali': [-8.4095, 115.1889], 'denpasar': [-8.6500, 115.2167], 'medan': [3.5951, 98.6722], 'padang': [-0.9470, 100.4171], 'palembang': [-2.9909, 104.7565], 'pekanbaru': [0.5070, 101.4477], 'lampung': [-5.4500, 105.2666],
                'balikpapan': [-1.2379, 116.8528], 'samarinda': [-0.5022, 117.1536], 'pontianak': [-0.0226, 109.3301], 'banjarmasin': [-3.3166, 114.5901],
                'makassar': [-5.1476, 119.4327], 'manado': [1.4748, 124.8420], 'palu': [-0.8917, 119.8707], 'kendari': [-3.9985, 122.5126],
                'mataram': [-8.5833, 116.1166], 'kupang': [-10.1771, 123.6070], 'jayapura': [-2.5337, 140.7186], 'ambon': [-3.6954, 128.1814]
            }

            lats, lons = [], []
            for loc in asal_counts['Lokasi']:
                loc_lower = str(loc).lower().replace('kabupaten', '').replace('kab.', '').replace('kota', '').replace('provinsi', '').replace('prov.', '').strip()
                matched = False
                for key, coords in indo_coords.items():
                    if key == loc_lower or f" {key} " in f" {loc_lower} " or loc_lower.startswith(f"{key} ") or loc_lower.endswith(f" {key}"):
                        lats.append(coords[0]); lons.append(coords[1])
                        matched = True; break
                if not matched:
                    for key, coords in indo_coords.items():
                        if key in loc_lower or loc_lower in key:
                            lats.append(coords[0]); lons.append(coords[1])
                            matched = True; break
                if not matched:
                    lats.append(None); lons.append(None)
            
            asal_counts['Lat'], asal_counts['Lon'] = lats, lons
            map_data = asal_counts.dropna(subset=['Lat', 'Lon'])
            
            # --- PETA FULL INDONESIA ---
            with st.container(border=True):
                st.markdown("<div style='font-size:14px; color:gray; font-weight:bold; margin-bottom:10px;'>Titik Persebaran (Heatmap) - Seluruh Indonesia</div>", unsafe_allow_html=True)
                if not map_data.empty:
                    fig_map = px.scatter_mapbox(
                        map_data, lat="Lat", lon="Lon", size="Jumlah", color="Jumlah", 
                        color_continuous_scale=["#FF8C00", "#FF0000", "#8B0000"], 
                        size_max=40, zoom=3.8, center=dict(lat=-2.5, lon=118.0), 
                        mapbox_style="carto-positron", hover_name="Lokasi", hover_data={"Lat":False, "Lon":False, "Jumlah":True}
                    )
                    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600, coloraxis_showscale=False)
                    st.plotly_chart(fig_map, use_container_width=True)
                else:
                    st.warning("⚠️ Belum ada koordinat peta yang terdeteksi dari data Asal.")
            
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            
            # --- GRAFIK TREEMAP (Menggantikan Bar Chart) ---
            with st.container(border=True):
                st.markdown("<div style='font-size:14px; color:gray; font-weight:bold; margin-bottom:10px;'>📍 Sebaran Domisili Prospek (TreeMap)</div>", unsafe_allow_html=True)
                if not asal_counts.empty:
                    # Menggunakan asal_counts dan kolom 'Lokasi' agar datanya bersih dan seragam
                    fig_asal = px.treemap(
                        asal_counts, 
                        path=[px.Constant("Seluruh Wilayah"), 'Lokasi'], 
                        values='Jumlah',
                        color='Jumlah', 
                        color_continuous_scale='GnBu'
                    )
                    fig_asal.update_traces(textinfo="label+value", texttemplate="<b>%{label}</b><br>%{value} Leads")
                    fig_asal.update_layout(height=500, margin=dict(t=10, l=10, r=10, b=10), coloraxis_showscale=False)
                    st.plotly_chart(fig_asal, use_container_width=True)
                else:
                    st.info("Data Asal belum tersedia untuk dibuatkan TreeMap.")
        else:
            st.info("Data Asal belum tersedia untuk dipetakan.")
    except Exception as e:
        st.error(f"Gagal memuat Peta/TreeMap: {e}")

    st.markdown("<br>", unsafe_allow_html=True)
        
# --- HALAMAN 1: SOSIAL MEDIA ---
if page == "📱 SOSIAL MEDIA":
    st.title("🚀 SOSMED COMMAND CENTER")
    st.markdown("---")
    try:
        df = load_sosmed()
        st.sidebar.markdown(f"<h2 style='color:{BRAND_BLUE};'>Manager Controls</h2>", unsafe_allow_html=True)
        
        # --- SIDEBAR FILTERS ---
        months = df['Bulan-Deadline'].dropna().unique().tolist() if 'Bulan-Deadline' in df.columns else []
        selected_months = st.sidebar.multiselect("Bulan Deadline:", options=months, default=months, key="sos_bulan")
        
        list_pic = ["Ejak", "Hana", "Abi", "Hanif"] 
        selected_pic = st.sidebar.multiselect("Pantau PIC:", options=list_pic, default=list_pic, key="sos_pic")

        mask = (df['PIC'].isin(selected_pic)) & (df['Bulan-Deadline'].isin(selected_months))
        filtered_df = df[mask].copy()

        if not filtered_df.empty:
            # --- LOGIKA PERHITUNGAN (TETAP UTUH) ---
            v_mask = filtered_df['Output'].str.contains('Video', case=False, na=False)
            v_total, v_done = len(filtered_df[v_mask]), len(filtered_df[v_mask & (filtered_df['PROSES'] == 'DONE')])
            d_total, d_done = len(filtered_df[~v_mask]), len(filtered_df[~v_mask & (filtered_df['PROSES'] == 'DONE')])

            ig_p = len(filtered_df[(filtered_df['PROSES'] == 'DONE') & (filtered_df['IG'] == False)])
            tt_p = len(filtered_df[(filtered_df['PROSES'] == 'DONE') & (filtered_df['TIKTOK'] == False)])
            yt_p = len(filtered_df[(filtered_df['PROSES'] == 'DONE') & (v_mask) & (filtered_df['YT'] == False)])

            # --- BARIS 1: METRIK (Sesuai image_a5d7ba.png) ---
            st.markdown('<div class="feature-header">📊 Produksi & Realisasi</div>', unsafe_allow_html=True)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Rencana", len(filtered_df))
            m2.metric("Total DONE ✅", v_done + d_done)
            m3.metric("Video Selesai 🎬", f"{v_done}/{v_total}")
            m4.metric("Design Selesai 🎨", f"{d_done}/{d_total}")

            st.markdown('<div class="feature-header">📲 Status Penjadwalan (Scheduling)</div>', unsafe_allow_html=True)
            s1, s2, s3 = st.columns(3)
            s1.metric("Hutang Post IG 📸", ig_p)
            s2.metric("Hutang Post YT 🎥", yt_p)
            s3.metric("Hutang Post TikTok 💃", tt_p)

            st.markdown("---")

            # --- BARIS 2: TATA LETAK KANAN-KIRI ---
            col_visual, col_audit = st.columns([1.2, 1])

            with col_visual:
                # GRAFIK 1: PIE CHART
                st.markdown('<div class="feature-header">🏛️ Sebaran Pilar Konten</div>', unsafe_allow_html=True)
                p_counts = filtered_df['Konten Pillar'].value_counts().reset_index()
                fig_p = px.pie(p_counts, names='Konten Pillar', values='count', hole=0.3, color_discrete_sequence=[BRAND_BLUE, BRAND_YELLOW, "#003A66", "#FFD700"])
                fig_p.update_layout(margin=dict(t=20, b=20, l=10, r=10), height=300)
                st.plotly_chart(fig_p, use_container_width=True)

                # GRAFIK 2: BAR HUTANG PIC
                st.markdown('<div class="feature-header">⚠️ Hutang Produksi per PIC</div>', unsafe_allow_html=True)
                debt = filtered_df[filtered_df['PROSES'] != 'DONE'].groupby('PIC').size().reset_index(name='Hutang')
                fig_d = px.bar(pd.merge(pd.DataFrame({'PIC': list_pic}), debt, on='PIC', how='left').fillna(0), x='PIC', y='Hutang', color_discrete_sequence=[BRAND_BLUE], text_auto=True)
                fig_d.update_layout(margin=dict(t=20, b=20, l=10, r=10), height=300, plot_bgcolor='white')
                st.plotly_chart(fig_d, use_container_width=True)

                # GRAFIK 3: KOMPARASI VIDEO VS DESIGN
                st.markdown('<div class="feature-header">🕵️ Komparasi Video vs Design</div>', unsafe_allow_html=True)
                breakdown = []
                for n in selected_pic:
                    for ot in ["Video", "Design"]:
                        sub = filtered_df[(filtered_df['PIC'] == n) & (filtered_df['Output'].str.contains(ot, case=False, na=False))]
                        if not sub.empty:
                            d = len(sub[sub['PROSES'] == 'DONE'])
                            breakdown.append({'PIC': n, 'Output': ot, 'Status': 'DONE', 'Jumlah': d})
                            breakdown.append({'PIC': n, 'Output': ot, 'Status': 'BELUM', 'Jumlah': len(sub)-d})
                if breakdown:
                    fig_br = px.bar(pd.DataFrame(breakdown), x='PIC', y='Jumlah', color='Status', facet_col='Output', color_discrete_map={'DONE': BRAND_YELLOW, 'BELUM': BRAND_BLUE}, barmode='group', text_auto=True)
                    fig_br.update_layout(margin=dict(t=40, b=20, l=10, r=10), height=350, plot_bgcolor='white')
                    st.plotly_chart(fig_br, use_container_width=True)

            with col_audit:
                st.markdown('<div class="feature-header">📝 Detail Audit Pipeline</div>', unsafe_allow_html=True)
                for name in selected_pic:
                    pic_prod = filtered_df[(filtered_df['PIC'] == name) & (filtered_df['PROSES'] != 'DONE')]
                    pic_sched = filtered_df[(filtered_df['PIC'] == name) & (filtered_df['PROSES'] == 'DONE') & 
                                            ((filtered_df['IG'] == False) | ((v_mask) & (filtered_df['YT'] == False)) | (filtered_df['TIKTOK'] == False))]
                    
                    # Status indikator di judul expander
                    status_emoji = "🔴" if (not pic_prod.empty or not pic_sched.empty) else "🟢"
                    with st.expander(f"{status_emoji} {name} - Status Detail"):
                        if not pic_prod.empty:
                            st.markdown("**Hutang Produksi:**")
                            for _, r in pic_prod.iterrows():
                                st.write(f"🔹 {r['Output']}: {r['Judul Konten']}")
                        if not pic_sched.empty:
                            st.markdown("**Hutang Post:**")
                            for _, r in pic_sched.iterrows():
                                plts = [p for p in ['IG', 'TIKTOK'] if not r[p]]
                                if "Video" in r['Output'] and not r['YT']: plts.append("YT")
                                st.warning(f"⚠️ {r['Kode Konten']} ({', '.join(plts)})")
                        if pic_prod.empty and pic_sched.empty:
                            st.success("Tugas selesai semua! ✨")

            st.markdown("---")

            # --- BARIS 3: LIVE EDITOR (FULL WIDTH) ---
            st.markdown('<div class="feature-header">📋 Master Production Pipeline (Live Editor)</div>', unsafe_allow_html=True)
            
            # Map visual (TETAP ADA)
            pic_map = {"Ejak": "🔵 Ejak", "Hana": "🟢 Hana", "Abi": "🟡 Abi", "Hanif": "🟣 Hanif"}
            out_map = {"Video": "🎬 Video", "Design": "🎨 Design"}
            stat_map = {"DONE": "✅ DONE", "PENDING": "⏳ PENDING", "ON PROGRESS": "🏗️ ON PROGRESS"}

            df_display = filtered_df[['Kode Konten', 'Tanggal Deadline', 'Output', 'PIC', 'Judul Konten', 'PROSES', 'IG', 'YT', 'TIKTOK']].copy()
            df_display['PIC'] = df_display['PIC'].map(pic_map).fillna(df_display['PIC'])
            df_display['Output'] = df_display['Output'].map(out_map).fillna(df_display['Output'])
            df_display['PROSES'] = df_display['PROSES'].map(stat_map).fillna(df_display['PROSES'])

            edited_df = st.data_editor(
                df_display,
                column_config={
                    "PIC": st.column_config.SelectboxColumn("PIC", options=list(pic_map.values())),
                    "Output": st.column_config.SelectboxColumn("Output", options=list(out_map.values())),
                    "PROSES": st.column_config.SelectboxColumn("Status", options=list(stat_map.values())),
                    "IG": st.column_config.CheckboxColumn("IG"),
                    "YT": st.column_config.CheckboxColumn("YT"),
                    "TIKTOK": st.column_config.CheckboxColumn("TikTok")
                },
                disabled=['Kode Konten', 'Tanggal Deadline', 'Judul Konten'],
                use_container_width=True,
                hide_index=False,
                key="editor_sosmed"
            )

            # LOGIKA SIMPAN (TETAP AMAN)
            if st.button("💾 Simpan Semua Perubahan", use_container_width=True):
                with st.spinner("Sinkronisasi database..."):
                    updates = 0
                    for idx in edited_df.index:
                        for col in ["PIC", "Output", "PROSES", "IG", "YT", "TIKTOK"]:
                            old_val = str(filtered_df.at[idx, col]).strip()
                            new_val_raw = edited_df.at[idx, col]
                            
                            # Bersihkan Emoji
                            if isinstance(new_val_raw, str) and " " in new_val_raw:
                                new_val = new_val_raw.split(" ", 1)[-1].strip()
                            else:
                                new_val = new_val_raw

                            if old_val != str(new_val).strip():
                                val_to_send = "V" if (isinstance(new_val, bool) and new_val) else ("" if isinstance(new_val, bool) else str(new_val))
                                update_sheet_cell(0, idx, col, val_to_send)
                                updates += 1
                    
                    if updates > 0:
                        st.success(f"Berhasil memperbarui {updates} data!")
                        st.cache_data.clear()
                        st.rerun()

    except Exception as e:
        st.error(f"Kesalahan Teknis: {e}")
# --- HALAMAN 2: WEBSITE AUDIT ---
elif page == "🌐 WEBSITE AUDIT":
    st.title("🌐 WEBSITE MANAGEMENT")
    st.markdown("---")
    try:
        df_web = load_website()
        st.sidebar.markdown(f"<h2 style='color:{BRAND_BLUE};'>Website Controls</h2>", unsafe_allow_html=True)
        
        if 'Bulan-Deadline' in df_web.columns:
            months_web = df_web['Bulan-Deadline'].dropna().unique().tolist()
            selected_months_web = st.sidebar.multiselect("Bulan Deadline:", options=months_web, default=months_web, key="web_bulan")
            mask_web = df_web['Bulan-Deadline'].isin(selected_months_web)
            filtered_web = df_web[mask_web].copy()
        else:
            filtered_web = df_web.copy()

        target_columns = ['Kode Konten', 'Deadline', 'Tanggal Posting', 'Content Pillar', 'SEO Rekomendasi', 'Judul', 'Bahan Upload', 'Link', 'Folder Design', 'Designer', 'Status Writting', 'Status Design', 'Status Post', 'Link Live']
        available_columns = [col for col in target_columns if col in filtered_web.columns]
        
        if not filtered_web.empty:
            done_keywords = ['DONE', 'TRUE', 'V', '1', 'POSTED', 'SELESAI', 'UPLOAD', 'UPLOADED', 'SUDAH UPLOAD']
            if 'Status Post' in filtered_web.columns: filtered_web['Is_Done'] = filtered_web['Status Post'].astype(str).str.upper().str.strip().isin(done_keywords)
            else: filtered_web['Is_Done'] = False
                
            filtered_web['Status_Label'] = filtered_web['Is_Done'].apply(lambda x: 'DONE / LIVE' if x else 'PENDING')
            done_web = filtered_web['Is_Done'].sum()

            st.markdown('<div class="feature-header">🛠️ Progress Website Keseluruhan</div>', unsafe_allow_html=True)
            w1, w2, w3 = st.columns(3)
            w1.metric("Total Task Website", len(filtered_web))
            w2.metric("Artikel / Page Live ✅", done_web)
            w3.metric("Dalam Proses (Pending) ⚠️", len(filtered_web) - done_web)

            st.markdown('<div class="feature-header">🎯 Sisa Tugas Berdasarkan Pilar Utama</div>', unsafe_allow_html=True)
            def get_pillar_metrics(df, pillar_regex):
                if 'Content Pillar' in df.columns:
                    mask = df['Content Pillar'].astype(str).str.contains(pillar_regex, case=False, na=False)
                    tot = len(df[mask])
                    d = len(df[mask & df['Is_Done']])
                    return tot, d, tot - d
                return 0, 0, 0

            a_tot, a_done, a_sisa = get_pillar_metrics(filtered_web, 'Artikel')
            n_tot, n_done, n_sisa = get_pillar_metrics(filtered_web, 'News')
            g_tot, g_done, g_sisa = get_pillar_metrics(filtered_web, 'Galery|Gallery')
            l_tot, l_done, l_sisa = get_pillar_metrics(filtered_web, 'Linkedin|LinkedIn')

            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Sisa Artikel 📝", f"{a_sisa} Task", f"{a_done} dari {a_tot} Selesai", delta_color="off")
            p2.metric("Sisa News 📰", f"{n_sisa} Task", f"{n_done} dari {n_tot} Selesai", delta_color="off")
            p3.metric("Sisa Gallery 📸", f"{g_sisa} Task", f"{g_done} dari {g_tot} Selesai", delta_color="off")
            p4.metric("Sisa LinkedIn 💼", f"{l_sisa} Task", f"{l_done} dari {l_tot} Selesai", delta_color="off")

            st.markdown('<div class="feature-header">📝 Detail Audit Task Website</div>', unsafe_allow_html=True)
            pending_web = filtered_web[filtered_web['Is_Done'] == False]
            if not pending_web.empty:
                pillars = pending_web['Content Pillar'].fillna('Uncategorized').unique()
                for p in pillars:
                    sub_pending = pending_web[pending_web['Content Pillar'].fillna('Uncategorized') == p]
                    with st.expander(f"📋 Audit {p} ({len(sub_pending)} Task Pending)"):
                        for _, r in sub_pending.iterrows():
                            kode = r.get('Kode Konten', 'NO-CODE')
                            judul = r.get('Judul', 'Tanpa Judul')
                            designer = r.get('Designer', 'N/A')
                            st.write(f"🔹 **[{kode}]** | PIC: {designer} | {judul}")
            else:
                st.success("✅ Semua tugas Website di periode ini sudah Clear/Live!")

            st.markdown('<div class="feature-header">📋 Master Website Pipeline</div>', unsafe_allow_html=True)
            st.dataframe(filtered_web[available_columns] if available_columns else filtered_web, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Kesalahan Teknis Website: {e}")

# =====================================================================
# 4. PAGE LOGIC (PASTIKAN INISIALISASI INI ADA DI ATAS)
# =====================================================================

# Baris kunci: Mengambil data dari session state agar bisa digunakan di semua halaman
bundle_data = st.session_state.get('bundle', {})

# --- HALAMAN 3: INSIGHTS & ANALYTICS ---
if page == "📈 INSIGHTS & ANALYTICS":
    import io
    from datetime import datetime
    st.title("📈 ANALITIK KONTEN")

    # 1. SETUP VARIABLE & SESSION STATE
    header_names = ["Date", "Platform", "View", "Reach", "Interaction", "Profile Visit", "Link Clicks", "Follow"]
    numeric_cols = ["View", "Reach", "Interaction", "Profile Visit", "Link Clicks", "Follow"]
    
    if 'preview_data' not in st.session_state:
        st.session_state.preview_data = None
    if 'uploader_key' not in st.session_state:
        st.session_state.uploader_key = 0

    # Ambil data database
    if 'bundle' not in st.session_state or st.session_state.bundle is None:
        st.session_state.bundle = fetch_all_master_data()
    df_db_main = st.session_state.get('bundle', {}).get(2, pd.DataFrame())

    # =====================================================
    # 2. GLOBAL SUMMARIES (DASHBOARD ATAS)
    # =====================================================
    st.markdown("### 📊 Ringkasan Performa Konten (Database)")
    if not df_db_main.empty:
        # Bersihkan Header & Data
        if len(df_db_main.columns) == len(header_names):
            df_db_main.columns = header_names
        
        for col in numeric_cols:
            df_db_main[col] = pd.to_numeric(df_db_main[col], errors='coerce').fillna(0)
        
        # Pisahkan Data per Platform
        df_tk_db = df_db_main[df_db_main['Platform'] == 'TikTok']
        df_ig_db = df_db_main[df_db_main['Platform'] == 'Instagram']

        # Tampilan Tab/Kolom untuk Summary
        tab_tk, tab_ig, tab_total = st.tabs(["🎵 TikTok", "📸 Instagram", "🌐 Total Gabungan"])
        
        with tab_tk:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Views", f"{int(df_tk_db['View'].sum()):,}")
            c2.metric("Reach", f"{int(df_tk_db['Reach'].sum()):,}")
            c3.metric("Interaksi", f"{int(df_tk_db['Interaction'].sum()):,}")
            c4.metric("Follows", f"{int(df_tk_db['Follow'].sum()):,}")
            
        with tab_ig:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Views", f"{int(df_ig_db['View'].sum()):,}")
            c2.metric("Reach", f"{int(df_ig_db['Reach'].sum()):,}")
            c3.metric("Interaksi", f"{int(df_ig_db['Interaction'].sum()):,}")
            c4.metric("Follows", f"{int(df_ig_db['Follow'].sum()):,}")

        with tab_total:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Grand Views", f"{int(df_db_main['View'].sum()):,}", delta="TikTok + IG")
            c2.metric("Grand Reach", f"{int(df_db_main['Reach'].sum()):,}")
            c3.metric("Grand Interaksi", f"{int(df_db_main['Interaction'].sum()):,}")
            c4.metric("Grand Follows", f"{int(df_db_main['Follow'].sum()):,}")
    else:
        st.info("Database masih kosong.")

    st.markdown("---")

    # =====================================================
    # 3. IMPORTER SECTION
    # =====================================================
    with st.expander("🚀 Ultra-Smart Importer (TikTok & Instagram)", expanded=True):
        files = st.file_uploader(
            "Upload CSV Insight", 
            type=["csv"], 
            accept_multiple_files=True, 
            key=f"ins_v4_{st.session_state.uploader_key}"
        )
        
        if files:
            all_processed = []
            ig_frames = []
            logs = []
            current_year = datetime.now().year

            for f in files:
                try:
                    raw_bytes = f.getvalue()
                    # Deteksi Encoding
                    content = []
                    for enc in ["utf-8", "utf-8-sig", "utf-16", "latin-1"]:
                        try:
                            content = raw_bytes.decode(enc).splitlines()
                            break
                        except: continue
                    
                    sample = "\n".join(content[:10]).lower().replace('"', '').replace('\x00', '').replace(' ', '')
                    
                    # --- LOGIKA TIKTOK (Overview.csv / FollowerHistory.csv) ---
                    if "videoviews" in sample or "followerhistory" in f.name.lower() or "activefollowers" in sample:
                        df_tk = pd.read_csv(io.StringIO("\n".join(content)))
                        res_tk = pd.DataFrame()
                        
                        # Fix Tanggal TikTok (Handling "Month Day" format)
                        def parse_tk_date(d_str):
                            try:
                                # Coba parse "January 1" -> Jadi "01-01-2024" (current year)
                                dt_obj = pd.to_datetime(d_str, format='%B %d', errors='coerce')
                                if pd.isna(dt_obj): # Jika gagal, coba format YYYY-MM-DD
                                    dt_obj = pd.to_datetime(d_str, errors='coerce')
                                return dt_obj.replace(year=current_year).strftime('%d-%m-%Y')
                            except: return d_str

                        res_tk['Date'] = df_tk['Date'].apply(parse_tk_date)
                        res_tk['Platform'] = 'TikTok'
                        res_tk['View'] = df_tk.get('Video Views', 0)
                        res_tk['Reach'] = df_tk.get('Video Views', 0)
                        res_tk['Interaction'] = df_tk.get('Likes', 0) + df_tk.get('Comments', 0) + df_tk.get('Shares', 0)
                        res_tk['Profile Visit'] = df_tk.get('Profile Views', 0)
                        res_tk['Link Clicks'] = 0; res_tk['Follow'] = 0
                        all_processed.append(res_tk)
                        logs.append(f"✅ TikTok ({f.name})")

                    # --- LOGIKA INSTAGRAM ---
                    else:
                        target = ""
                        if "follows" in sample: target = "Follow"
                        elif "interactions" in sample: target = "Interaction"
                        elif "profilevisits" in sample: target = "Profile Visit"
                        elif "reach" in sample: target = "Reach"
                        elif "views" in sample: target = "View"
                        elif "linkclicks" in sample: target = "Link Clicks"
                        
                        if target:
                            skip = 0
                            for i, line in enumerate(content):
                                if "date" in line.lower() and "primary" in line.lower():
                                    skip = i; break
                            df_ig = pd.read_csv(io.StringIO("\n".join(content[skip:])))
                            df_ig['Date'] = pd.to_datetime(df_ig['Date'].astype(str).str.split('T').str[0]).dt.strftime('%d-%m-%Y')
                            ig_frames.append(df_ig[['Date', 'Primary']].rename(columns={'Primary': target}))
                            logs.append(f"✅ Instagram {target} ({f.name})")
                except Exception as e:
                    logs.append(f"❌ Error {f.name}: {e}")

            if ig_frames:
                m_ig = ig_frames[0]
                for d in ig_frames[1:]: m_ig = pd.merge(m_ig, d, on='Date', how='outer')
                m_ig['Platform'] = 'Instagram'
                for c in numeric_cols:
                    if c not in m_ig.columns: m_ig[c] = 0
                all_processed.append(m_ig.fillna(0))

            if all_processed:
                st.session_state.preview_data = pd.concat(all_processed, ignore_index=True)
            for l in logs: st.caption(l)

    # =====================================================
    # 4. PREVIEW & SAVE SECTION
    # =====================================================
    if st.session_state.preview_data is not None:
        df_p = st.session_state.preview_data
        st.markdown("### 🔍 Preview Data Baru")
        
        # Ringkasan Preview (TikTok vs IG vs Total)
        p_tk = df_p[df_p['Platform'] == 'TikTok']
        p_ig = df_p[df_p['Platform'] == 'Instagram']
        
        c1, c2, c3 = st.columns(3)
        c1.metric("TikTok Views", f"{int(p_tk['View'].sum()):,}")
        c2.metric("IG Views", f"{int(p_ig['View'].sum()):,}")
        c3.metric("Total Views", f"{int(df_p['View'].sum()):,}")

        st.dataframe(df_p, use_container_width=True, hide_index=True)
        
        if st.button("🚀 KONFIRMASI SIMPAN KE GOOGLE SHEETS", use_container_width=True):
            final_list = df_p[header_names].values.tolist()
            if append_sheet_rows(2, final_list):
                st.success("🔥 Data Berhasil Dicatat!")
                # RESET TOTAL
                st.session_state.preview_data = None 
                st.session_state.uploader_key += 1 
                st.cache_data.clear()
                st.session_state.bundle = fetch_all_master_data()
                st.rerun()

    # =====================================================
    # 5. DATABASE TABLE & REFRESH
    # =====================================================
    st.markdown("---")
    st.markdown("### 🗄️ Riwayat Database")
    
    df_show = st.session_state.get('bundle', {}).get(2, pd.DataFrame())
    if not df_show.empty:
        df_show = df_show.dropna(how='all')
        if len(df_show.columns) == len(header_names):
            df_show.columns = header_names
        try:
            df_show['Date'] = pd.to_datetime(df_show['Date'], dayfirst=True, errors='coerce')
            df_show = df_show.sort_values(by='Date', ascending=False)
            df_show['Date'] = df_show['Date'].dt.strftime('%d-%m-%Y')
        except: pass
        st.dataframe(df_show, use_container_width=True, hide_index=True)

    if st.button("🔄 Segarkan Data", use_container_width=True):
        st.cache_data.clear()
        st.session_state.bundle = fetch_all_master_data()
        st.rerun()

# --- HALAMAN 4: WA ADMIN REPORT ---
elif page == "💬 WA ADMIN REPORT":
    st.title("💬 KINERJA WA ADMIN & CLOSING LPK")
    st.markdown("---")
    
    try:
        df_wa = load_wa_admin()
        
        # --- [PERBAIKAN LOGIKA] PEMBERSIHAN BARIS HANTU ---
        # Buang baris HANYA JIKA kolom penting ini kosong semua (menghindari hilangnya data admin yang belum lengkap)
        kolom_penting = [col for col in ['Tanggal Masuk', 'No Hp', 'Status'] if col in df_wa.columns]
        if kolom_penting:
            df_wa = df_wa.dropna(subset=kolom_penting, how='all')

        # 1. IDENTIFIKASI & PEMBERSIHAN KOLOM STATUS
        status_col = next((col for col in df_wa.columns if 'Status' in str(col)), None)
        if status_col:
            df_wa.rename(columns={status_col: 'Status'}, inplace=True)
            df_wa['Status'] = df_wa['Status'].astype(str).str.strip()
            df_wa['Status'] = df_wa['Status'].replace(['', 'nan', 'None', 'NaN'], 'Belum Terupdate')
        else:
            df_wa['Status'] = "Belum Terupdate"
            
        df_full_tags = df_wa.copy()
                
        if 'Mekari Tag' in df_wa.columns:
            # Filter membuang data sampah dari metrik utama
            tag_dibuang = ['Double Chat', 'Closed - Not Interested', 'Partnership']
            pola_hapus = '|'.join(tag_dibuang)
            df_wa = df_wa[~df_wa['Mekari Tag'].astype(str).str.contains(pola_hapus, case=False, na=False)]
        
        # 2. FILTER DATA DI HALAMAN UTAMA
        st.markdown('<div class="feature-header">🔍 Filter Data Laporan</div>', unsafe_allow_html=True)
        
        col_filter1, col_filter2 = st.columns(2)
        
        with col_filter1:
            if 'Bulan-Masuk' in df_wa.columns:
                # PERBAIKAN: Jika bulan kosong, jangan dihapus, tapi ubah jadi "Belum Diisi" agar tetap terbaca
                df_wa['Bulan-Masuk'] = df_wa['Bulan-Masuk'].astype(str).str.strip().replace(['', 'nan', 'None', 'NaN'], 'Belum Diisi')
                df_full_tags['Bulan-Masuk'] = df_full_tags['Bulan-Masuk'].astype(str).str.strip().replace(['', 'nan', 'None', 'NaN'], 'Belum Diisi')
                
                months_wa = df_wa['Bulan-Masuk'].unique().tolist()
                selected_months_wa = st.multiselect("📅 Pilih Bulan Masuk:", options=months_wa, default=months_wa, key="wa_bulan")
                
                df_wa = df_wa[df_wa['Bulan-Masuk'].isin(selected_months_wa)]
                df_full_tags = df_full_tags[df_full_tags['Bulan-Masuk'].isin(selected_months_wa)]
                
        with col_filter2:
            search_city = st.text_input("📍 Cari Asal Kota/Provinsi:", "", key="wa_search").strip()
            if search_city:
                df_wa = df_wa[df_wa['Asal'].astype(str).str.contains(search_city, case=False, na=False)]
                df_full_tags = df_full_tags[df_full_tags['Asal'].astype(str).str.contains(search_city, case=False, na=False)]

        st.markdown("---")
        
        # PERBAIKAN: Baris ini sebelumnya terhapus, wajib ada agar kode tidak error!
        if not df_wa.empty:
            
            # 3. METRIK UTAMA
            total_leads = len(df_wa)
            total_closing = len(df_wa[df_wa['Status'].str.contains('Closing', case=False, na=False)])
            conversion_rate = (total_closing / total_leads * 100) if total_leads > 0 else 0
            
            st.markdown('<div class="feature-header">🎯 Real-Time Lead Health Check</div>', unsafe_allow_html=True)
            a1, a2, a3, a4 = st.columns(4)
            a1.metric("Total Leads Terdeteksi 📲", f"{total_leads}")
            a2.metric("Total Sukses Closing 🎓", f"{total_closing} / 45")
            a3.metric("Conversion Rate ⚡", f"{conversion_rate:.1f}%")
            
            unique_locations = df_wa['Asal'].replace(['', 'nan', 'NaN'], pd.NA).dropna().nunique()
            a4.metric("Unique Locations 📍", f"{unique_locations}")

            st.markdown("---")

            # 4. MEKARI TAG STATUS BREAKDOWN (PIE CHART)
            st.markdown('<div class="feature-header">🏷️ Mekari Tag Status Breakdown</div>', unsafe_allow_html=True)
            if 'Mekari Tag' in df_full_tags.columns:
                df_full_tags['Mekari Tag'] = df_full_tags['Mekari Tag'].astype(str).str.strip()
                mekari_summary = df_full_tags['Mekari Tag'].value_counts().reset_index()
                mekari_summary.columns = ['Tag', 'Jumlah']
                fig_mekari = px.pie(
                    mekari_summary, names='Tag', values='Jumlah', hole=0.4, 
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig_mekari.update_traces(textinfo='label+value+percent', textposition='outside', textfont_size=12)
                fig_mekari.update_layout(height=600, showlegend=True, legend=dict(orientation="h", y=-0.2, x=0.5), paper_bgcolor='white')
                st.plotly_chart(fig_mekari, use_container_width=True)

            # 5. KATEGORI PESAN MASUK
            st.markdown('<div class="feature-header">🗂️ Kategori Intensi Pesan</div>', unsafe_allow_html=True)
            if 'Kategori (Persyaratan/Biaya/Pendaftaran/Loker/dll)' in df_full_tags.columns:
                kolom_kat = 'Kategori (Persyaratan/Biaya/Pendaftaran/Loker/dll)'
                df_full_tags[kolom_kat] = df_full_tags[kolom_kat].astype(str).str.strip()
                df_full_tags[kolom_kat] = df_full_tags[kolom_kat].replace(['', 'nan', 'None', 'NaN'], 'Lainnya')
                
                kat_counts = df_full_tags[kolom_kat].value_counts().reset_index()
                
                kat_color_map = {
                    "Persyaratan": "#BBF7D0",
                    "Biaya": "#FECACA",
                    "Pendaftaran": "#BFDBFE",
                    "Loker": "#E9D5FF",
                    "Partnership": "#E9D5FF",
                    "Lainnya": "#E5E7EB"
                }
                
                kat_order = ["Persyaratan", "Biaya", "Pendaftaran", "Loker", "Partnership", "Lainnya"]
                
                fig_kat = px.bar(
                    kat_counts, x=kolom_kat, y='count', text_auto=True, 
                    color=kolom_kat, color_discrete_map=kat_color_map,
                    category_orders={kolom_kat: kat_order}
                )
                fig_kat.update_layout(paper_bgcolor='white', plot_bgcolor='white', font=dict(color="#000000"), xaxis_title="", yaxis_title="Jumlah", showlegend=False)
                st.plotly_chart(fig_kat, use_container_width=True)

            # 6. DISTRIBUSI STATUS INTERNAL
            st.markdown('<div class="feature-header">📊 Distribusi Status Prospek (Internal Status)</div>', unsafe_allow_html=True)
            
            status_order = [
                "Belum Terupdate", "No Response", "Follow Up", "Daftar", "Interview", 
                "Closing", "Sales Progress", "Withdraw", "Lainnya",
                "Not Eligible", "Double Chat", "Closed - Not Interested", "Partnership"
            ]
            
            color_map = {
                "Belum Terupdate": "#F3F4F6", "No Response": "#FDE68A", "Follow Up": "#BFDBFE",
                "Daftar": "#BBF7D0", "Interview": "#E9D5FF", "Closing": "#BBF7D0",
                "Lainnya": "#D1D5DB", "Sales Progress": "#1D4ED8", "Withdraw": "#B91C1C",
                "Not Eligible": "#9CA3AF", "Double Chat": "#6B7280", "Closed - Not Interested": "#4B5563", "Partnership": "#E9D5FF"
            }
            
            if 'Status' in df_full_tags.columns:
                df_full_tags['Status'] = df_full_tags['Status'].astype(str).str.strip()
                status_summary = df_full_tags['Status'].value_counts().reset_index()
                status_summary.columns = ['Status', 'Jumlah']
                
                fig_status = px.bar(
                    status_summary, x='Jumlah', y='Status', orientation='h',
                    category_orders={"Status": status_order}, color='Status',
                    color_discrete_map=color_map, text_auto=True
                )
                
                fig_status.update_layout(showlegend=False, height=550, paper_bgcolor='white', plot_bgcolor='white', yaxis_title="")
                st.plotly_chart(fig_status, use_container_width=True)
            
            # 7. FUNNEL & SUMBER
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<div class="feature-header">📊 Funnel Konversi Prospek</div>', unsafe_allow_html=True)
                funnel_order = ["Follow Up", "Daftar", "Interview", "Closing"]
                funnel_data = [dict(Tahap="Total Leads", Jumlah=total_leads)]
                for tahap in funnel_order:
                    count = len(df_wa[df_wa['Status'].str.contains(tahap, case=False, na=False)])
                    funnel_data.append(dict(Tahap=tahap, Jumlah=count))
                df_f = pd.DataFrame(funnel_data)
                df_f['Pct'] = (df_f['Jumlah'] / total_leads * 100).round(1)
                fig_funnel = px.bar(
                    df_f, x='Jumlah', y='Tahap', orientation='h',
                    text=df_f.apply(lambda r: f"{r['Jumlah']} ({r['Pct']}%)", axis=1),
                    color='Tahap', color_discrete_sequence=[BRAND_BLUE, "#006bbd", "#0080e0", BRAND_YELLOW, "#32CD32"]
                )
                fig_funnel.update_layout(paper_bgcolor='white', plot_bgcolor='white', showlegend=False, yaxis={'categoryorder':'total descending'})
                st.plotly_chart(fig_funnel, use_container_width=True)

            with c2:
                st.markdown('<div class="feature-header">🌐 Sumber Prospek</div>', unsafe_allow_html=True)
                if 'Sumber (Ads/Organik/Sales)' in df_wa.columns:
                    sumber_counts = df_wa['Sumber (Ads/Organik/Sales)'].value_counts().reset_index()
                    sumber_counts.columns = ['Sumber', 'Jumlah']
                    fig_sumber = px.pie(sumber_counts, names='Sumber', values='Jumlah', hole=0.4, color_discrete_sequence=[BRAND_BLUE, BRAND_YELLOW, "#003A66"])
                    fig_sumber.update_traces(textinfo='label+percent')
                    st.plotly_chart(fig_sumber, use_container_width=True)

            # 8. MAPPING ASAL (TREEMAP)
            st.markdown('<div class="feature-header">📍 Sebaran Domisili Prospek (TreeMap)</div>', unsafe_allow_html=True)
            if 'Asal' in df_wa.columns:
                asal_counts = df_wa['Asal'].value_counts().reset_index()
                asal_counts.columns = ['Asal', 'Jumlah']
                df_asal_filtered = asal_counts[asal_counts['Asal'].str.strip() != '']
                if not df_asal_filtered.empty:
                    fig_asal = px.treemap(
                        df_asal_filtered, path=[px.Constant("Seluruh Wilayah"), 'Asal'], values='Jumlah',
                        color='Jumlah', color_continuous_scale='GnBu'
                    )
                    fig_asal.update_traces(textinfo="label+value", texttemplate="<b>%{label}</b><br>%{value} Leads")
                    fig_asal.update_layout(height=500, margin=dict(t=10, l=10, r=10, b=10), coloraxis_showscale=False)
                    st.plotly_chart(fig_asal, use_container_width=True)
                else:
                    st.info("Data Asal belum diisi oleh Admin.")
            
            # 9. DATA DETAIL SUKSES CLOSING & SALES PROGRESS
            col_closing, col_sales = st.columns(2)
            
            # --- KOLOM KIRI: DATA CLOSING ---
            with col_closing:
                st.markdown('<div class="feature-header">🎉 Detail Sukses Closing</div>', unsafe_allow_html=True)
                df_closing = df_wa[df_wa['Status'].str.contains('Closing', case=False, na=False)].copy()
                if not df_closing.empty:
                    kolom_target = {
                        'Tanggal Masuk': 'Tanggal', 'Nama': 'Nama', 'No Hp': 'Nomor Telfon',
                        'Asal': 'Asal Wilayah', 'Sumber (Ads/Organik/Sales)': 'Sumber'
                    }
                    kolom_tersedia = [col for col in kolom_target.keys() if col in df_closing.columns]
                    df_closing_display = df_closing[kolom_tersedia].rename(columns=kolom_target)
                    df_closing_display.reset_index(drop=True, inplace=True)
                    df_closing_display.index = df_closing_display.index + 1
                    st.dataframe(df_closing_display, use_container_width=True)
                else:
                    st.info("Belum ada data siswa yang berstatus Closing.")
                    
            # --- KOLOM KANAN: DATA SALES PROGRESS ---
            with col_sales:
                st.markdown('<div class="feature-header">⏳ Detail Sales Progress</div>', unsafe_allow_html=True)
                df_sales = df_wa[df_wa['Status'].str.contains('Sales Progress', case=False, na=False)].copy()
                if not df_sales.empty:
                    kolom_target = {
                        'Tanggal Masuk': 'Tanggal', 'Nama': 'Nama', 'No Hp': 'Nomor Telfon',
                        'Asal': 'Asal Wilayah', 'Sumber (Ads/Organik/Sales)': 'Sumber'
                    }
                    kolom_tersedia = [col for col in kolom_target.keys() if col in df_sales.columns]
                    df_sales_display = df_sales[kolom_tersedia].rename(columns=kolom_target)
                    df_sales_display.reset_index(drop=True, inplace=True)
                    df_sales_display.index = df_sales_display.index + 1
                    st.dataframe(df_sales_display, use_container_width=True)
                else:
                    st.info("Belum ada prospek yang sedang dalam Sales Progress.")

            # 10. MASTER DATABASE
            st.markdown('<div class="feature-header">📋 Master Database WA Admin</div>', unsafe_allow_html=True)
            col_refresh, _ = st.columns([1, 2])
            
            with col_refresh:
                if st.button("🔄 Refresh & Tarik Data Terbaru", use_container_width=True, key="refresh_wa_admin"):
                    # Bersihkan Data Cache Utama
                    st.cache_data.clear()
                    
                    # Bersihkan Resource Cache jika ada
                    if hasattr(st, 'cache_resource'):
                        st.cache_resource.clear()
                        
                    # Hapus Memori Filter agar reset ke awal dan menangkap data baru
                    if 'wa_bulan' in st.session_state:
                        del st.session_state['wa_bulan']
                    if 'wa_search' in st.session_state:
                        del st.session_state['wa_search']
                        
                    # Rerun Halaman
                    st.rerun()
                    
            st.dataframe(df_wa, use_container_width=True, hide_index=True)
            
        else:
            st.warning("⚠️ Data tidak ditemukan.")
            
    except Exception as e:
        st.error(f"Kesalahan Teknis: {e}")
# --- HALAMAN 7: ADS ANALYTICS ---
elif page == "📈 ADS ANALYTICS":
    st.title("📈 Ads & Budget Analytics (ROI Engine)")
    st.markdown("Pantau **Cost Per Lead (CPL)**, **Customer Acquisition Cost (CAC)**, dan **ROAS** secara real-time.")
    
    import io
    import pandas as pd
    
    # Asumsi Nilai 1 Closing
    BIAYA_PELATIHAN = 15000000 
    
    # =====================================================================
    # 1. LOAD DATA (CRM, WA ADMIN, DAN ADS)
    # =====================================================================
    df_crm = pd.DataFrame()
    df_wa = pd.DataFrame()
    
    total_spend_tiktok, total_clicks_tiktok, total_leads_tiktok, closing_tiktok = 0, 0, 0, 0
    total_spend_meta, total_clicks_meta, total_leads_meta, closing_meta = 0, 0, 0, 0
    total_spend_mekari, total_pesan_mekari = 0, 0
    global_closing = 0
    
    df_ads_tiktok_db, df_ads_meta_db, df_ads_mekari_db = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    # --- A. LOAD CRM (HITUNG LEADS & UNTUK CROSS-CHECK) ---
    try:
        df_crm = load_database_nomor()
        if not df_crm.empty:
            kolom_sumber_crm = next((c for c in df_crm.columns if c.lower() in ['platform', 'sumber', 'source']), None)
            if kolom_sumber_crm:
                total_leads_tiktok = len(df_crm[df_crm[kolom_sumber_crm].astype(str).str.contains('Tiktok', case=False, na=False)])
                total_leads_meta = len(df_crm[df_crm[kolom_sumber_crm].astype(str).str.contains(r'Instagram|Facebook|IG|FB|Meta', case=False, regex=True, na=False)])
    except:
        pass

    # --- B. LOAD WA ADMIN (AMBIL LANGSUNG DARI FUNGSI HALAMAN 4) ---
    try:
        df_wa = load_wa_admin()
        if not df_wa.empty:
            status_col = next((col for col in df_wa.columns if 'Status' in str(col)), None)
            if status_col:
                df_closing = df_wa[df_wa[status_col].astype(str).str.contains('Closing', case=False, na=False)].copy()
                global_closing = len(df_closing)
                
                kolom_sumber_wa = next((c for c in df_closing.columns if c.lower() in ['platform', 'sumber', 'source']), None)
                if kolom_sumber_wa:
                    closing_tiktok = len(df_closing[df_closing[kolom_sumber_wa].astype(str).str.contains('Tiktok', case=False, na=False)])
                    closing_meta = len(df_closing[df_closing[kolom_sumber_wa].astype(str).str.contains(r'Instagram|Facebook|IG|FB|Meta', case=False, regex=True, na=False)])
                else:
                    hp_wa = next((c for c in df_closing.columns if 'hp' in c.lower() or 'phone' in c.lower()), None)
                    hp_crm = next((c for c in df_crm.columns if 'hp' in c.lower() or 'phone' in c.lower()), None)
                    sumber_crm = next((c for c in df_crm.columns if c.lower() in ['platform', 'sumber', 'source']), None)
                    if hp_wa and hp_crm and sumber_crm and not df_crm.empty:
                        df_closing['clean_hp'] = df_closing[hp_wa].astype(str).str.replace(r'\D', '', regex=True)
                        df_crm_clean = df_crm.copy()
                        df_crm_clean['clean_hp'] = df_crm_clean[hp_crm].astype(str).str.replace(r'\D', '', regex=True)
                        df_merged = pd.merge(df_closing, df_crm_clean[['clean_hp', sumber_crm]], on='clean_hp', how='left')
                        
                        closing_tiktok = len(df_merged[df_merged[sumber_crm].astype(str).str.contains('Tiktok', case=False, na=False)])
                        closing_meta = len(df_merged[df_merged[sumber_crm].astype(str).str.contains(r'Instagram|Facebook|IG|FB|Meta', case=False, regex=True, na=False)])
    except:
        pass

    # --- C. LOAD DATA BUDGET IKLAN DARI SPREADSHEET (OPTIMASI QUOTA API) ---
    try:
        client = init_connection()
        if client:
            master_spreadsheet = client.open("MASTER DATA DIGITAL MARKETING 2.0")

            # TIKTOK ADS (INDEX 6)
            try:
                sheet_tiktok = master_spreadsheet.get_worksheet(6)
                records_tiktok = sheet_tiktok.get_all_records()
                if records_tiktok:
                    df_ads_tiktok_db = pd.DataFrame(records_tiktok)
                    df_calc_tk = df_ads_tiktok_db.copy()
                    df_calc_tk.columns = [str(c).strip().lower() for c in df_calc_tk.columns]
                    col_cost_tk = next((c for c in df_calc_tk.columns if 'cost' in c), None)
                    if col_cost_tk:
                        df_calc_tk[col_cost_tk] = pd.to_numeric(df_calc_tk[col_cost_tk].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
                        total_spend_tiktok = df_calc_tk[col_cost_tk].sum()
            except: pass

            # META ADS (INDEX 7)
            try:
                sheet_meta = master_spreadsheet.get_worksheet(7)
                records_meta = sheet_meta.get_all_records()
                if records_meta:
                    df_ads_meta_db = pd.DataFrame(records_meta)
                    df_calc_mt = df_ads_meta_db.copy()
                    df_calc_mt.columns = [str(c).strip().lower() for c in df_calc_mt.columns]
                    col_cost_mt = next((c for c in df_calc_mt.columns if 'spent' in c or 'spend' in c or 'cost' in c), None)
                    if col_cost_mt:
                        df_calc_mt[col_cost_mt] = pd.to_numeric(df_calc_mt[col_cost_mt].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
                        total_spend_meta = df_calc_mt[col_cost_mt].sum()
            except: pass

            # MEKARI WA (INDEX 8)
            try:
                sheet_mekari = master_spreadsheet.get_worksheet(8)
                records_mekari = sheet_mekari.get_all_records()
                if records_mekari:
                    df_ads_mekari_db = pd.DataFrame(records_mekari)
                    df_calc_mk = df_ads_mekari_db.copy()
                    df_calc_mk.columns = [str(c).strip().lower() for c in df_calc_mk.columns]
                    
                    col_cost_mk = next((c for c in df_calc_mk.columns if 'biaya' in c or 'deducted balance' in c or 'balance' in c), None)
                    if col_cost_mk:
                        df_calc_mk[col_cost_mk] = pd.to_numeric(df_calc_mk[col_cost_mk].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
                        total_spend_mekari = df_calc_mk[col_cost_mk].sum()
                        
                    col_pesan_mk = next((c for c in df_calc_mk.columns if 'interaksi' in c or 'pesan' in c or 'broadcast amount' in c or 'amount' in c), None)
                    if col_pesan_mk:
                        df_calc_mk[col_pesan_mk] = pd.to_numeric(df_calc_mk[col_pesan_mk].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
                        total_pesan_mekari = df_calc_mk[col_pesan_mk].sum()
            except: pass
    except: pass

    # =====================================================================
    # 2. TAMPILAN RINGKASAN GLOBAL
    # =====================================================================
    global_spend = total_spend_tiktok + total_spend_meta + total_spend_mekari
    global_leads = total_leads_tiktok + total_leads_meta
    global_omzet = global_closing * BIAYA_PELATIHAN 
    
    global_cpl = global_spend / global_leads if global_leads > 0 else 0
    global_cac = global_spend / global_closing if global_closing > 0 else 0
    global_roas = (global_omzet / global_spend) if global_spend > 0 else 0

    st.markdown('<div class="feature-header">🌍 ULTIMATE ROI DASHBOARD (SEMUA PLATFORM)</div>', unsafe_allow_html=True)
    g1, g2, g3, g4, g5 = st.columns(5)
    with g1:
        with st.container(border=True):
            st.markdown(f"<div style='font-size:12px; color:gray; font-weight:800; margin-bottom:5px;'>💸 TOTAL SPEND</div><div style='font-size:24px; font-weight:bold; color:#8B0000;'>Rp {global_spend:,.0f}</div>", unsafe_allow_html=True)
    with g2:
        with st.container(border=True):
            st.markdown(f"<div style='font-size:12px; color:gray; font-weight:800; margin-bottom:5px;'>👥 LEADS CRM</div><div style='font-size:24px; font-weight:bold;'>{global_leads}</div>", unsafe_allow_html=True)
    with g3:
        with st.container(border=True):
            st.markdown(f"<div style='font-size:12px; color:gray; font-weight:800; margin-bottom:5px;'>🎓 TOTAL CLOSING</div><div style='font-size:24px; font-weight:bold; color:#006400;'>{global_closing} Siswa</div>", unsafe_allow_html=True)
    with g4:
        with st.container(border=True):
            st.markdown(f"<div style='font-size:12px; color:gray; font-weight:800; margin-bottom:5px;'>🎯 BIAYA/SISWA (CAC)</div><div style='font-size:24px; font-weight:bold; color:#D2691E;'>Rp {global_cac:,.0f}</div>", unsafe_allow_html=True)
    with g5:
        with st.container(border=True):
            st.markdown(f"<div style='font-size:12px; color:gray; font-weight:800; margin-bottom:5px;'>🚀 ROAS (KEUNTUNGAN)</div><div style='font-size:24px; font-weight:bold; color:#1E3A8A;'>{global_roas:,.1f}x Lipat</div>", unsafe_allow_html=True)

    if global_roas > 0:
        st.success(f"🔥 **Status Bisnis:** Dengan total investasi pengadaan prospek & perawatan leads **Rp {global_spend:,.0f}**, kamu menghasilkan omzet kotor **Rp {global_omzet:,.0f}**. Nilai investasimu kembali **{global_roas:,.1f} kali lipat**!")
    elif global_spend > 0 and global_closing == 0:
        st.error("⚠️ **Peringatan:** Saldo (Iklan/Mekari) sudah digunakan, namun belum ada siswa yang Closing. Segera evaluasi materi iklan atau proses follow-up CS!")

    st.markdown("<br>", unsafe_allow_html=True)

    # =====================================================================
    # 3. TAB UNTUK RINCIAN PER PLATFORM
    # =====================================================================
    tab_tiktok, tab_meta, tab_mekari = st.tabs(["📱 Rincian TikTok Ads", "🟦 Rincian Meta Ads", "🟩 Rincian Mekari (WA)"])

    # ---------------- TAB TIKTOK ----------------
    with tab_tiktok:
        cpl_tk = total_spend_tiktok / total_leads_tiktok if total_leads_tiktok > 0 else 0
        cac_tk = total_spend_tiktok / closing_tiktok if closing_tiktok > 0 else 0
        
        t1, t2, t3, t4, t5 = st.columns(5)
        t1.metric("💸 Spend TikTok", f"Rp {total_spend_tiktok:,.0f}")
        t2.metric("👥 Leads Masuk", total_leads_tiktok)
        t3.metric("🎯 Cost Per Lead", f"Rp {cpl_tk:,.0f}")
        t4.metric("🎓 Closing TikTok", closing_tiktok)
        t5.metric("💰 Biaya/Siswa (CAC)", f"Rp {cac_tk:,.0f}")
        
        st.markdown("---")
        with st.container(border=True):
            st.markdown("### 📤 Upload Laporan TikTok Ads Baru")
            up_tk = st.file_uploader("Upload File Laporan TikTok Ads", type=['csv', 'xlsx'], key="up_tk")
            if up_tk is not None:
                try:
                    df_up_tk = pd.read_csv(up_tk) if up_tk.name.endswith('.csv') else pd.read_excel(up_tk)
                    col_pertama_tk = df_up_tk.columns[0]
                    df_clean_tk = df_up_tk[~df_up_tk[col_pertama_tk].astype(str).str.strip().str.lower().str.startswith('total')].copy()
                    
                    df_calc_up = df_clean_tk.copy()
                    df_calc_up.columns = [str(c).strip().lower() for c in df_calc_up.columns]
                    col_cost_up = next((c for c in df_calc_up.columns if 'cost' in c), None)
                    up_spend_tk = pd.to_numeric(df_calc_up[col_cost_up], errors='coerce').fillna(0).sum() if col_cost_up else 0
                        
                    st.success(f"✅ Budget TikTok yang akan ditambahkan: **Rp {up_spend_tk:,.0f}**")
                    if st.button("📥 Import ke Spreadsheet (TikTok)", use_container_width=True, key="btn_imp_tk"):
                        with st.spinner("Mengirim ke Tab 7..."):
                            df_final = df_clean_tk.fillna("")
                            bulk_data = [df_final.columns.tolist()] + df_final.values.tolist() if df_ads_tiktok_db.empty else df_final.values.tolist()
                            if append_sheet_rows(6, bulk_data): 
                                st.success("✅ Berhasil masuk ke Tab TikTok."); st.balloons(); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Gagal memproses: {e}")

        with st.expander("📑 Database TikTok Tersimpan (Klik untuk lihat & Reset)", expanded=False):
            if not df_ads_tiktok_db.empty:
                st.dataframe(df_ads_tiktok_db, use_container_width=True, hide_index=True)
                if st.button("🗑️ Kosongkan Database TikTok", use_container_width=True, key="rst_tk"):
                    init_connection().open("MASTER DATA DIGITAL MARKETING 2.0").get_worksheet(6).clear()
                    st.cache_data.clear(); st.rerun()

    # ---------------- TAB META ----------------
    with tab_meta:
        cpl_mt = total_spend_meta / total_leads_meta if total_leads_meta > 0 else 0
        cac_mt = total_spend_meta / closing_meta if closing_meta > 0 else 0
        
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("💸 Spend Meta", f"Rp {total_spend_meta:,.0f}")
        m2.metric("👥 Leads Masuk", total_leads_meta)
        m3.metric("🎯 Cost Per Lead", f"Rp {cpl_mt:,.0f}")
        m4.metric("🎓 Closing Meta", closing_meta)
        m5.metric("💰 Biaya/Siswa (CAC)", f"Rp {cac_mt:,.0f}")
        
        st.markdown("---")
        with st.container(border=True):
            st.markdown("### 📤 Upload Laporan Meta Ads Baru")
            up_mt = st.file_uploader("Upload File Laporan Meta Ads", type=['csv', 'xlsx'], key="up_mt")
            if up_mt is not None:
                try:
                    df_up_mt = pd.read_csv(up_mt) if up_mt.name.endswith('.csv') else pd.read_excel(up_mt)
                    col_pertama_mt = df_up_mt.columns[0]
                    df_clean_mt = df_up_mt[~df_up_mt[col_pertama_mt].astype(str).str.strip().str.lower().str.startswith('total')].copy()
                    
                    df_calc_up_mt = df_clean_mt.copy()
                    df_calc_up_mt.columns = [str(c).strip().lower() for c in df_calc_up_mt.columns]
                    col_cost_up_mt = next((c for c in df_calc_up_mt.columns if 'spent' in c or 'spend' in c or 'cost' in c), None)
                    up_spend_mt = pd.to_numeric(df_calc_up_mt[col_cost_up_mt], errors='coerce').fillna(0).sum() if col_cost_up_mt else 0
                        
                    st.success(f"✅ Budget Meta yang akan ditambahkan: **Rp {up_spend_mt:,.0f}**")
                    if st.button("📥 Import ke Spreadsheet (Meta)", use_container_width=True, key="btn_imp_mt"):
                        with st.spinner("Mengirim ke Tab 8..."):
                            df_final_mt = df_clean_mt.fillna("")
                            bulk_data_mt = [df_final_mt.columns.tolist()] + df_final_mt.values.tolist() if df_ads_meta_db.empty else df_final_mt.values.tolist()
                            if append_sheet_rows(7, bulk_data_mt): 
                                st.success("✅ Berhasil masuk ke Tab Meta."); st.balloons(); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Gagal memproses: {e}")

        with st.expander("📑 Database Meta Tersimpan (Klik untuk lihat & Reset)", expanded=False):
            if not df_ads_meta_db.empty:
                st.dataframe(df_ads_meta_db, use_container_width=True, hide_index=True)
                if st.button("🗑️ Kosongkan Database Meta", use_container_width=True, key="rst_mt"):
                    init_connection().open("MASTER DATA DIGITAL MARKETING 2.0").get_worksheet(7).clear() 
                    st.cache_data.clear(); st.rerun()

    # ---------------- TAB MEKARI (SMART IMPORTER) ----------------
    with tab_mekari:
        st.info("💡 **Smart Importer:** Sistem merekap file otomatis menjadi **1 Baris Struk Ringkas** beserta Periode Datanya agar tidak ada duplikasi input.")
        
        mk1, mk2 = st.columns(2)
        mk1.metric("💸 Total Saldo WA Terpakai", f"Rp {total_spend_mekari:,.0f}")
        mk2.metric("💬 Total Interaksi WA Terbayar", f"{total_pesan_mekari:,.0f} Pesan")
        
        st.markdown("---")
        with st.container(border=True):
            st.markdown("### 📤 Upload Laporan Mekari Baru")
            st.markdown("Bisa upload file `Campaign Logs` atau `Billing Logs`.")
            up_mk = st.file_uploader("Upload Laporan Mekari (CSV/Excel)", type=['csv', 'xlsx'], key="up_mk")
            
            if up_mk is not None:
                try:
                    df_up_mk = pd.read_csv(up_mk) if up_mk.name.endswith('.csv') else pd.read_excel(up_mk)
                    df_calc_mk = df_up_mk.copy()
                    df_calc_mk.columns = [str(c).strip().lower() for c in df_calc_mk.columns]
                    
                    jenis_laporan = "Tidak Dikenali"
                    up_spend_mk = 0
                    up_pesan_mk = 0
                    periode_data = "Tanggal Tidak Terdeteksi"
                    
                    # 1. Deteksi File: CAMPAIGN LOGS (Broadcast)
                    if 'deducted balance' in df_calc_mk.columns or 'broadcast amount' in df_calc_mk.columns:
                        jenis_laporan = "WA Campaign (Broadcast)"
                        col_cost = next((c for c in df_calc_mk.columns if 'deducted balance' in c), None)
                        col_pesan = next((c for c in df_calc_mk.columns if 'broadcast amount' in c), None)
                        
                        up_spend_mk = float(pd.to_numeric(df_calc_mk[col_cost], errors='coerce').fillna(0).sum()) if col_cost else 0.0
                        up_pesan_mk = int(pd.to_numeric(df_calc_mk[col_pesan], errors='coerce').fillna(0).sum()) if col_pesan else 0
                        
                    # 2. Deteksi File: CONVERSATION / BILLING LOGS (Chat Individu)
                    elif 'credit' in df_calc_mk.columns and 'conversation_id' in df_calc_mk.columns:
                        jenis_laporan = "WA Conversation (Billing/Follow Up)"
                        col_cost = next((c for c in df_calc_mk.columns if 'credit' in c), None)
                        
                        up_spend_mk = float(pd.to_numeric(df_calc_mk[col_cost], errors='coerce').fillna(0).sum()) if col_cost else 0.0
                        up_pesan_mk = int(len(df_calc_mk))
                    
                    # 3. EXTRACTION TANGGAL (MEMBUAT PERIODE DATA)
                    col_date = next((c for c in df_calc_mk.columns if 'created' in c or 'date' in c or 'tanggal' in c), None)
                    if col_date:
                        try:
                            # Parse format tanggal Mekari dengan utc=True agar tahan banting terhadap format timezone (+07:00)
                            temp_dates = pd.to_datetime(df_calc_mk[col_date], utc=True, errors='coerce')
                            min_date = temp_dates.min()
                            max_date = temp_dates.max()
                            if pd.notnull(min_date) and pd.notnull(max_date):
                                periode_data = f"{min_date.strftime('%d %b %Y')} s/d {max_date.strftime('%d %b %Y')}"
                        except:
                            pass
                        
                    st.success(f"✅ Format terdeteksi sebagai: **{jenis_laporan}**")
                    st.info(f"📅 **Periode Data:** {periode_data}\n\n📊 **Total Saldo:** Rp {up_spend_mk:,.0f} | **Jumlah Pesan:** {up_pesan_mk:,.0f}")
                    
                    if st.button("📥 Catat Saldo Ini ke Database", use_container_width=True, key="btn_imp_mk"):
                        with st.spinner("Mengirim ringkasan ke Tab 9..."):
                            import datetime
                            tgl_sekarang = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                            
                            # Header dan Baris Ditambah Kolom Periode Data
                            header_mk = ["Waktu Import", "Periode Laporan", "Jenis Laporan WA", "Total Interaksi", "Total Biaya (Rp)"]
                            baris_data_mk = [str(tgl_sekarang), str(periode_data), str(jenis_laporan), int(up_pesan_mk), float(up_spend_mk)]
                            
                            bulk_data_mk = [header_mk, baris_data_mk] if df_ads_mekari_db.empty else [baris_data_mk]
                            
                            if append_sheet_rows(8, bulk_data_mk): 
                                st.success("✅ Berhasil menyimpan riwayat saldo Mekari!"); st.balloons(); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error(f"Gagal memproses file Mekari: {e}")

        with st.expander("📑 Riwayat Saldo Mekari Tersimpan", expanded=False):
            if not df_ads_mekari_db.empty:
                st.dataframe(df_ads_mekari_db, use_container_width=True, hide_index=True)
                if st.button("🗑️ Kosongkan Riwayat Mekari", use_container_width=True, key="rst_mk"):
                    init_connection().open("MASTER DATA DIGITAL MARKETING 2.0").get_worksheet(8).clear() # INDEX 8
                    st.cache_data.clear(); st.rerun()

# =====================================================================
# SYSTEM RUNNER (JANGAN DIHAPUS, PASTIKAN ADA DI PALING BAWAH FILE)
# =====================================================================
if __name__ == "__main__":
    if not st.runtime.exists():
        import sys
        from streamlit.web import cli as stcli
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
