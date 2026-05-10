import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import base64
import datetime
import sys
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
            sheet.append_rows(all_data_list)
        except Exception as e:
            st.error(f"Gagal batch update ke Google Sheets: {e}")

def append_rows_to_crm(bulk_data):
    try:
        # Buka Spreadsheet
        sh = client.open_by_key("ISI_DENGAN_KEY_SPREADSHEET_MAS")
        
        # Coba buka berdasarkan NAMA SHEET agar lebih pasti (Ganti jika namanya beda)
        sheet = sh.worksheet("DATABASE NOMOR") 
        
        # Kirim Data
        sheet.append_rows(bulk_data, value_input_option='USER_ENTERED')
        return True
    except Exception as e:
        # TULISAN INI AKAN MUNCUL DI TERMINAL VS CODE MAS
        print(f"❌ ERROR GOOGLE SHEETS: {e}") 
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

        valid_tags = ["Hot Lead", "Warm Lead", "Cold Lead", "Pending Form - L1", "Pending Form - L2", "Re-engagement", "Future Prospect", "Form Submitted", "Sales Progress"]
        mekari_col = next((c for c in df_wa.columns if 'Mekari' in c), None)
        
        if not mekari_col:
            st.error("❌ Kolom Mekari Tag tidak ditemukan di WA Admin.")
            return
            
        new_leads = df_wa[df_wa[mekari_col].isin(valid_tags)].copy()
        
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
            st.success(f"✅ Berhasil menarik {len(all_new_rows)} Prospek (Mapping Asal ke Domisili Berhasil)!")
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
# 2. SISTEM KEAMANAN & BACKGROUND
# =====================================================================
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        return base64.b64encode(f.read()).decode()

def set_bg_local(png_file):
    try:
        bin_str = get_base64(png_file)
        st.markdown(f'''
            <style>
            [data-testid="stAppViewContainer"] {{
                background-image: url("data:image/png;base64,{bin_str}");
                background-size: cover; background-attachment: fixed;
            }}
            [data-testid="stAppViewContainer"]::before {{
                content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
                background-color: rgba(255, 255, 255, 0.4); z-index: -1;
            }}
            </style>
        ''', unsafe_allow_html=True)
    except: pass

def check_password():
    if st.session_state.get("password_correct"): return True
    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        st.markdown(f'<div style="text-align:center;"><img src="{LOGO_URL}" width="180"><h2>COMMAND CENTER</h2></div>', unsafe_allow_html=True)
        with st.form("login_form"):
            user = st.text_input("Username:").strip().lower()
            pwd = st.text_input("Password:", type="password")
            if st.form_submit_button("Masuk"):
                if "credentials" in st.secrets and user in st.secrets["credentials"] and st.secrets["credentials"][user] == pwd:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: st.error("Username/Password Salah")
    return False

if not check_password(): st.stop()
set_bg_local('bg.png')
if not check_password():
    st.stop()
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

    # 2. HEADER & NAVIGASI 5 KOTAK
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

    nav_cols = st.columns(5)
    nav_data = [
        ("📱", "Sosmed", "Jadwal PIC", "📱 SOSIAL MEDIA", "btn_sos"),
        ("🌐", "Website", "SEO Audit", "🌐 WEBSITE AUDIT", "btn_web"),
        ("📈", "Insight", "Analytics", "📈 INSIGHTS & ANALYTICS", "btn_in"),
        ("💬", "WA Admin", "Closing Funnel", "💬 WA ADMIN REPORT", "btn_wa"),
        ("📂", "Database", "CRM Kontak", "📂 DATABASE NOMOR", "btn_db")
    ]

    for col, (icon, title, sub, target, key) in zip(nav_cols, nav_data):
        with col: create_square_card(icon, title, sub, target, key)

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
            
            # Peta (Full Width dengan Shadow)
            with st.container(border=True):
                st.markdown("<div style='font-size:14px; color:gray; font-weight:bold; margin-bottom:10px;'>Titik Persebaran (Heatmap)</div>", unsafe_allow_html=True)
                if not map_data.empty:
                    fig_map = px.scatter_mapbox(
                        map_data, lat="Lat", lon="Lon", size="Jumlah", color="Jumlah", 
                        color_continuous_scale=["#FF8C00", "#FF0000", "#8B0000"], 
                        size_max=50, zoom=5.0, center=dict(lat=-7.0, lon=110.0), 
                        mapbox_style="carto-positron", hover_name="Lokasi", hover_data={"Lat":False, "Lon":False, "Jumlah":True}
                    )
                    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=400, coloraxis_showscale=False)
                    st.plotly_chart(fig_map, use_container_width=True)
                else:
                    st.warning("⚠️ Belum ada koordinat peta yang terdeteksi dari data Asal.")
            
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            
            # Grafik Bar (Full Width dengan Shadow)
            with st.container(border=True):
                st.markdown("<div style='font-size:14px; color:gray; font-weight:bold; margin-bottom:10px;'>Top 10 Asal Leads Terbanyak</div>", unsafe_allow_html=True)
                top_10_asal = asal_counts.head(10)
                fig_bar = px.bar(top_10_asal, y='Lokasi', x='Jumlah', text_auto=True, orientation='h', color_discrete_sequence=[BRAND_BLUE])
                fig_bar.update_layout(
                    margin={"r":0,"t":0,"l":0,"b":0}, height=350, 
                    xaxis_title="Jumlah Prospek (Leads)", yaxis_title="", 
                    yaxis={'categoryorder':'total ascending'}, 
                    paper_bgcolor='white', plot_bgcolor='white'
                )
                fig_bar.update_yaxes(tickfont=dict(color="#000000", size=11, family="Arial Black"))
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Data Asal belum tersedia untuk dipetakan.")
    except Exception as e:
        st.error(f"Gagal memuat Peta: {e}")

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

# --- HALAMAN 3: INSIGHTS & ANALYTICS ---
elif page == "📈 INSIGHTS & ANALYTICS":
    st.title("📈 PERFORMA & ANALITIK KONTEN")
    st.markdown("---")
    try:
        df_in = load_insight()
        st.sidebar.markdown(f"<h2 style='color:{BRAND_BLUE};'>Analytic Filters</h2>", unsafe_allow_html=True)
        
        if 'Platform' in df_in.columns:
            list_platform = df_in['Platform'].dropna().unique().tolist()
            sel_platform = st.sidebar.multiselect("Pilih Platform:", options=list_platform, default=list_platform, key="in_plat")
            df_in = df_in[df_in['Platform'].isin(sel_platform)]
        
        if not df_in.empty:
            st.markdown('<div class="feature-header">🎯 Total Kinerja Aggregat (Seluruh Platform)</div>', unsafe_allow_html=True)
            t_view = df_in['View'].sum()
            t_reach = df_in['Reach'].sum()
            t_interact = df_in['Interaction'].sum()
            t_clicks = df_in['Link Clicks'].sum()
            t_follow = df_in['Follow'].sum()
            
            i1, i2, i3, i4, i5 = st.columns(5)
            i1.metric("Total Views 👀", f"{t_view:,.0f}")
            i2.metric("Total Jangkauan 🌍", f"{t_reach:,.0f}")
            i3.metric("Total Interaksi 💬", f"{t_interact:,.0f}")
            i4.metric("Klik Link Bio 🔗", f"{t_clicks:,.0f}")
            i5.metric("Total Follower 👥", f"{t_follow:,.0f}")

            st.markdown("---")
            st.markdown('<div class="feature-header">📱 Perincian Kinerja per Platform</div>', unsafe_allow_html=True)
            
            for plat in sel_platform:
                df_plat = df_in[df_in['Platform'] == plat]
                if not df_plat.empty:
                    p_view = df_plat['View'].sum()
                    p_reach = df_plat['Reach'].sum()
                    p_interact = df_plat['Interaction'].sum()
                    p_clicks = df_plat['Link Clicks'].sum()
                    p_follow = df_plat['Follow'].sum()
                    
                    st.subheader(f"Platform: {plat}")
                    p1, p2, p3, p4, p5 = st.columns(5)
                    p1.metric(f"Views {plat}", f"{p_view:,.0f}")
                    p2.metric(f"Reach {plat}", f"{p_reach:,.0f}")
                    p3.metric(f"Interaksi {plat}", f"{p_interact:,.0f}")
                    p4.metric(f"Klik Link {plat}", f"{p_clicks:,.0f}")
                    p5.metric(f"Follower {plat}", f"{p_follow:,.0f}")
                    st.markdown("---")

            st.markdown('<div class="feature-header">📈 Tren Pertumbuhan per Platform</div>', unsafe_allow_html=True)
            
            if 'Platform' in df_in.columns and 'Date' in df_in.columns:
                df_trend = df_in.groupby(['Date', 'Platform'])[['View', 'Reach', 'Interaction', 'Profile Visit', 'Link Clicks', 'Follow']].sum().reset_index()
                df_trend['Sort_Date'] = pd.to_datetime(df_trend['Date'], errors='coerce', dayfirst=True)
                df_trend = df_trend.sort_values(by=['Sort_Date', 'Platform']).drop(columns=['Sort_Date'])
                line_colors = [BRAND_BLUE, BRAND_YELLOW, "#003A66", "#87CEEB", "#FF8C00"]

                def update_fig_style(fig):
                    fig.update_layout(
                        paper_bgcolor='white', plot_bgcolor='white', font=dict(color="#000000", size=12),
                        legend=dict(font=dict(color="#000000", size=12), bgcolor="rgba(255,255,255,0.5)"),
                        xaxis=dict(tickfont=dict(color="#000000"), title_font=dict(color="#000000")),
                        yaxis=dict(tickfont=dict(color="#000000"), title_font=dict(color="#000000"), gridcolor='#EEE')
                    )
                    fig.update_traces(textfont=dict(color="#000000"))
                    return fig

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("<h4 style='text-align: center; color: black;'>👀 Tren Views</h4>", unsafe_allow_html=True)
                    fig_view = px.line(df_trend, x='Date', y='View', color='Platform', text='View', color_discrete_sequence=line_colors)
                    fig_view.update_traces(mode='lines+markers+text', textposition='top center', texttemplate='%{text:,.0f}', line_shape='spline', marker=dict(size=8))
                    st.plotly_chart(update_fig_style(fig_view), use_container_width=True)

                with c2:
                    st.markdown("<h4 style='text-align: center; color: black;'>💬 Tren Interaction</h4>", unsafe_allow_html=True)
                    fig_int = px.line(df_trend, x='Date', y='Interaction', color='Platform', text='Interaction', color_discrete_sequence=line_colors)
                    fig_int.update_traces(mode='lines+markers+text', textposition='top center', texttemplate='%{text:,.0f}', line_shape='spline', marker=dict(size=8))
                    st.plotly_chart(update_fig_style(fig_int), use_container_width=True)

                c3, c4 = st.columns(2)
                with c3:
                    st.markdown("<h4 style='text-align: center; color: black;'>👥 Tren Profile Visit</h4>", unsafe_allow_html=True)
                    fig_prof = px.line(df_trend, x='Date', y='Profile Visit', color='Platform', text='Profile Visit', color_discrete_sequence=line_colors)
                    fig_prof.update_traces(mode='lines+markers+text', textposition='top center', texttemplate='%{text:,.0f}', line_shape='spline', marker=dict(size=8))
                    st.plotly_chart(update_fig_style(fig_prof), use_container_width=True)

                with c4:
                    st.markdown("<h4 style='text-align: center; color: black;'>🔗 Tren Link Clicks (Leads)</h4>", unsafe_allow_html=True)
                    fig_click = px.line(df_trend, x='Date', y='Link Clicks', color='Platform', text='Link Clicks', color_discrete_sequence=line_colors)
                    fig_click.update_traces(mode='lines+markers+text', textposition='top center', texttemplate='%{text:,.0f}', line_shape='spline', marker=dict(size=8))
                    st.plotly_chart(update_fig_style(fig_click), use_container_width=True)

                c5, c6 = st.columns(2)
                with c5:
                    st.markdown("<h4 style='text-align: center; color: black;'>📈 Tren Pertumbuhan Follower</h4>", unsafe_allow_html=True)
                    fig_follow = px.line(df_trend, x='Date', y='Follow', color='Platform', text='Follow', color_discrete_sequence=line_colors)
                    fig_follow.update_traces(mode='lines+markers+text', textposition='top center', texttemplate='%{text:,.0f}', line_shape='spline', marker=dict(size=8))
                    st.plotly_chart(update_fig_style(fig_follow), use_container_width=True)

            st.markdown('<div class="feature-header">📋 Master Database Insight</div>', unsafe_allow_html=True)
            st.dataframe(df_in, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Tidak ada data analitik.")
    except Exception as e:
        st.error(f"Kesalahan Teknis Insight: {e}")

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
# --- HALAMAN 5: DATABASE NOMOR (CRM) ---
elif page == "📂 DATABASE NOMOR":
    st.title("🗂️ CRM & DETAILED LEAD DATABASE")
    
    import io 
    import datetime

    # 1. AREA INPUT DATA
    c_sync, c_upload = st.columns([1, 1])
    
    with c_sync:
        st.markdown("### 🔄 Sinkronisasi")
        if st.button("Tarik Data Unik dari WA Admin", use_container_width=True):
            sync_leads_to_crm() 
            st.success("Berhasil sinkronisasi!")
            st.rerun()

    with c_upload:
        st.markdown("### ⬆️ Import Data Baru")
        with st.expander("Upload File Excel (.xlsx)"):
            st.info("💡 Format Mekari: **phone_number**, **full_name**, **customer_name**, **company**.")
            
            # --- DOWNLOAD TEMPLATE ---
            df_template = pd.DataFrame(columns=["phone_number", "full_name", "customer_name", "company"])
            buffer_template = io.BytesIO()
            with pd.ExcelWriter(buffer_template, engine='xlsxwriter') as writer:
                df_template.to_excel(writer, index=False, sheet_name='Template_Mekari')
            
            st.download_button(
                label="📥 Download Template Mekari", 
                data=buffer_template.getvalue(), 
                file_name="Template_CRM_Mekari.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                use_container_width=True
            )
            
            st.markdown("---")
            
            # --- FITUR UPLOAD BULK ---
            uploaded_file = st.file_uploader("Upload file Excel Mekari", type=["xlsx"], key="crm_uploader")
            
            if uploaded_file is not None:
                try:
                    df_upload = pd.read_excel(uploaded_file)
                    # Normalisasi Kolom
                    df_upload.columns = [str(c).strip().lower() for c in df_upload.columns]
                    req_cols = ['phone_number', 'full_name', 'customer_name', 'company']
                    
                    if all(col in df_upload.columns for col in req_cols):
                        st.write(f"✅ Terdeteksi {len(df_upload)} data siap import.")
                        
                        # LOGIKA EKSEKUSI TOMBOL
                        if st.button("📥 Konfirmasi Import Massal (Fast)", use_container_width=True):
                            with st.spinner("Mengirim data massal ke Google Sheets..."):
                                tgl_hari_ini = datetime.date.today().strftime("%Y-%m-%d")
                                
                                # Menyiapkan data: Company jadi Domisili
                                bulk_data = []
                                for _, row in df_upload.iterrows():
                                    data_baris = [
                                        row['full_name'],        # Kolom Nama
                                        str(row['phone_number']), # Kolom No Hp
                                        row['company'],          # Kolom Domisili (Dari Company)
                                        "Siswa",                 # Kolom Kategori (Default)
                                        tgl_hari_ini             # Kolom Tanggal Masuk
                                    ]
                                    bulk_data.append(data_baris)
                                
                                # EKSEKUSI KE BACKEND
                                try:
                                    # Memastikan fungsi dipanggil
                                    success = append_rows_to_crm(bulk_data) 
                                    
                                    if success:
                                        st.success(f"🚀 Sukses! {len(df_upload)} data berhasil masuk ke Google Sheets.")
                                        st.cache_data.clear() # Hapus cache agar data baru terbaca
                                        st.rerun() # Refresh tampilan
                                    else:
                                        st.error("Gagal mengirim data. Cek koneksi internet atau API Google Mas.")
                                except Exception as e:
                                    st.error(f"Error Backend: {e}")
                    else:
                        st.error("⚠️ Header file tidak sesuai format Mekari!")
                except Exception as e:
                    st.error(f"Gagal baca Excel: {e}")
            
    st.markdown("---")
    
    # Bagian tampilan database tetap sama seperti sebelumnya...
    try:
        df_crm = load_database_nomor()
        if not df_crm.empty:
            # (Gunakan kode tampilan tabel yang sudah Mas miliki di sini)
            st.dataframe(df_crm, use_container_width=True)
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
if __name__ == "__main__":
    if not st.runtime.exists():
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
