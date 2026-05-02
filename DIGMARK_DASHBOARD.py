import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import sys
from streamlit.web import cli as stcli

# =====================================================================
# 1. KONFIGURASI GLOBAL
# =====================================================================
st.set_page_config(page_title="Digmark Command Center", layout="wide", page_icon="🚀")

LOGO_URL = "https://www.dutapersadajogja.com/assets/img/logo.png" 

BRAND_BLUE = "#005696"
BRAND_YELLOW = "#FDB813"
TEXT_BLACK = "#000000" 
BG_WHITE = "#FFFFFF"

# =====================================================================
# 2. SISTEM KEAMANAN (USERNAME & PASSWORD)
# =====================================================================
def check_password():
    # Jika sudah berhasil login sebelumnya, langsung beri akses
    if st.session_state.get("password_correct"):
        return True

    # CSS untuk merapikan logo dan kotak login
    st.markdown(f"""
        <style>
        .login-box {{ display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }}
        .centered-image {{ display: block; margin-left: auto; margin-right: auto; border-radius: 50%; border: 3px solid {BRAND_YELLOW}; }}
        /* Sedikit styling tambahan untuk tombol Login agar senada dengan warna Brand */
        [data-testid="stFormSubmitButton"] button {{ width: 100%; background-color: {BRAND_BLUE}; color: white; border-radius: 5px; }}
        </style>
    """, unsafe_allow_html=True)

    _, col_mid, _ = st.columns([1, 2, 1])
    with col_mid:
        st.markdown(f"""
            <div class="login-box">
                <img src="{LOGO_URL}" class="centered-image" width="180">
                <h2 style='color: {BRAND_BLUE}; margin-top: 15px;'>DIGITAL MARKETING COMMAND CENTER</h2>
                <p style='color: gray; margin-top: -10px;'>LPK Duta Persada Yogyakarta</p>
                <hr style='border: 1px solid {BRAND_YELLOW}; width: 100%; margin-bottom: 20px;'>
            </div>
        """, unsafe_allow_html=True)

        # Membuat Form Login
        with st.form("login_form"):
            input_username = st.text_input("Username:")
            input_password = st.text_input("Password:", type="password")
            submit_button = st.form_submit_button("Masuk ke Dashboard")

            if submit_button:
                # Membersihkan input dari spasi berlebih dan menjadikan huruf kecil
                user = input_username.strip().lower()
                
                # Cek apakah blok [credentials] ada di Secrets
                if "credentials" in st.secrets:
                    # Validasi Username dan Password
                    if user in st.secrets["credentials"] and st.secrets["credentials"][user] == input_password:
                        st.session_state["password_correct"] = True
                        st.session_state["current_user"] = user.capitalize() # Menyimpan nama user yang login
                        st.rerun() # Refresh halaman untuk langsung masuk
                    else:
                        st.error("😕 Username atau Password salah.")
                else:
                    st.error("⚠️ Sistem Keamanan: Data kredensial tidak ditemukan di server.")

    return False

# GERBANG KEAMANAN MUTLAK
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
        st.error(f"⚠️ Koneksi Gagal: {e}")
        return None

def get_raw_df(sheet_index):
    client = init_connection()
    if client:
        try:
            spreadsheet = client.open("MASTER DATA DIGITAL MARKETING 2.0")
            sheet = spreadsheet.get_worksheet(sheet_index)
            return pd.DataFrame(sheet.get_all_records())
        except Exception as e:
            st.error(f"Gagal akses Tab {sheet_index}: {e}")
    return pd.DataFrame()

@st.cache_data(ttl=5)
def load_sosmed():
    df = get_raw_df(0)
    if not df.empty:
        col = 'Tanggal Deadline'
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
            df['Bulan-Deadline'] = df[col].dt.strftime('%B %Y')
        else:
            df['Bulan-Deadline'] = "Unknown"
        for c in ['IG', 'YT', 'TIKTOK']:
            if c in df.columns:
                df[c] = df[c].apply(lambda x: True if str(x).upper() in ['TRUE', 'V', '1', 'CHECKED'] else False)
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
    for col in ['View', 'Reach', 'Interaction', 'Link Clicks', 'Profile Visit', 'Follow']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

@st.cache_data(ttl=5)
def load_wa_admin():
    df = get_raw_df(3)
    if not df.empty and 'Tanggal Masuk' in df.columns:
        df['Tanggal Filter'] = pd.to_datetime(df['Tanggal Masuk'], dayfirst=True, errors='coerce')
        df['Bulan-Masuk'] = df['Tanggal Filter'].dt.strftime('%B %Y')
    return df

# =====================================================================
# 4. STYLING CUSTOM
# =====================================================================
st.markdown(f"""
    <style>
    .stApp {{ background-color: {BG_WHITE} !important; }}
    [data-testid="stSidebar"] {{ background-color: {BG_WHITE} !important; border-right: 3px solid {BRAND_BLUE}; }}
    .feature-header {{
        background-color: {BRAND_BLUE}; color: white !important; padding: 15px; border-radius: 8px; 
        border-left: 10px solid {BRAND_YELLOW}; font-size: 22px; font-weight: 800; margin-top: 20px; margin-bottom: 20px;
    }}
    p, span, label, li, .stMarkdown, .streamlit-expanderHeader p {{ color: {TEXT_BLACK} !important; font-weight: 700 !important; }}
    </style>
    """, unsafe_allow_html=True)

# =====================================================================
# 5. NAVIGASI UTAMA (DENGAN KONTROL SESSION STATE)
# =====================================================================
# Inisialisasi memori sistem agar tombol di Homepage bisa memindah Sidebar
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "🏠 HOMEPAGE"

st.sidebar.markdown(f"<h1 style='color:{BRAND_BLUE};'>🚀 NAVIGATION</h1>", unsafe_allow_html=True)

# Tambahkan parameter 'key="nav_page"' agar terkunci dengan memori
page = st.sidebar.radio(
    "Pilih Proses Kerja:", 
    ["🏠 HOMEPAGE", "📱 SOSIAL MEDIA", "🌐 WEBSITE AUDIT", "📈 INSIGHTS & ANALYTICS", "💬 WA ADMIN REPORT"],
    key="nav_page" 
)

if st.sidebar.button("🔄 Force Global Refresh"):
    st.cache_data.clear()
    st.rerun()

st.success("✅ Login Berhasil! Selamat bekerja, Tim Digmark.")
    
# --- RUNNING TEXT NOTIFICATION ---
st.markdown(f"""
    <div style="
        background-color: #d1e7dd; 
        color: #0f5132; 
        padding: 12px 15px; 
        border-radius: 8px; 
        border-left: 8px solid #198754;
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 25px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    ">
        <marquee behavior="scroll" direction="left" scrollamount="6">
            ✅ Login Berhasil! Selamat bekerja, Tim Digmark LPK Duta Persada. Tetap jaga sinergi dan ketangguhan tim, mari wujudkan target 450 pendaftaran siswa baru! 🚀
        </marquee>
    </div>
""", unsafe_allow_html=True)

# =====================================================================
# 6. LOGIKA HALAMAN & GRAFIK LENGKAP
# =====================================================================

# --- HALAMAN 0: HOMEPAGE ---
if page == "🏠 HOMEPAGE":
    # Header Utama
    st.markdown(f"""
        <div class="feature-header" style="text-align: center; font-size: 28px; margin-top: 0px;">
            Pusat Kendali Digital Marketing
        </div>
        <p style='text-align: center; font-size: 16px; color: gray; margin-bottom: 40px;'>
            Pilih modul kerja di bawah ini untuk segera memulai pemantauan data.
        </p>
    """, unsafe_allow_html=True)

    # --- FUNGSI PENCETAK KOTAK 1:1 ---
    def create_square_card(icon, title, subtitle, target_page, button_key):
        # Menggunakan container bergaris bawaan Streamlit agar rapi
        with st.container(border=True):
            # Layout Ikon, Judul, dan Subjudul
            st.markdown(f"""
                <div style="text-align: center; padding: 10px 0px 5px 0px;">
                    <div style="font-size: 70px; line-height: 1; margin-bottom: 15px;">{icon}</div>
                    <div style="font-size: 14px; font-weight: 900; color: {BRAND_BLUE}; text-transform: uppercase; line-height: 1.2;">{title}</div>
                    <div style="font-size: 12px; color: #666; margin-top: 8px; min-height: 35px;">{subtitle}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Tombol ini yang "mengganti" posisi radio sidebar lalu me-refresh layar
            if st.button("Masuk ➔", key=button_key, use_container_width=True):
                st.session_state.nav_page = target_page
                st.rerun()

    # --- MEMBANGUN GRID 4 KOLOM ---
    # Ini yang membuat tampilannya menjadi kotak-kotak 1:1 berjajar rapi
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        create_square_card("📱", "Sosial Media", "Jadwal Tayang & Hutang PIC", "📱 SOSIAL MEDIA", "btn_sos")
    with c2:
        create_square_card("🌐", "Website Audit", "Status Artikel & Pilar SEO", "🌐 WEBSITE AUDIT", "btn_web")
    with c3:
        create_square_card("📈", "Analytics", "Interaksi, Views & Leads", "📈 INSIGHTS & ANALYTICS", "btn_in")
    with c4:
        create_square_card("💬", "WA Report", "Funneling & Sukses Closing", "💬 WA ADMIN REPORT", "btn_wa")

    st.markdown("<hr style='border: 1px solid #EEE; margin-top: 40px;'>", unsafe_allow_html=True)
        
# --- HALAMAN 1: SOSIAL MEDIA ---
if page == "📱 SOSIAL MEDIA":
    st.title("🚀 SOSMED COMMAND CENTER")
    st.markdown("---")
    try:
        df = load_sosmed()
        st.sidebar.markdown(f"<h2 style='color:{BRAND_BLUE};'>Manager Controls</h2>", unsafe_allow_html=True)
        
        months = df['Bulan-Deadline'].dropna().unique().tolist() if 'Bulan-Deadline' in df.columns else []
        selected_months = st.sidebar.multiselect("Bulan Deadline:", options=months, default=months, key="sos_bulan")
        
        list_pic = ["Ejak", "Hana", "Abi", "Hanif"] 
        selected_pic = st.sidebar.multiselect("Pantau PIC:", options=list_pic, default=list_pic, key="sos_pic")

        mask = (df['PIC'].isin(selected_pic)) & (df['Bulan-Deadline'].isin(selected_months))
        filtered_df = df[mask]

        if not filtered_df.empty:
            v_mask = filtered_df['Output'].str.contains('Video', case=False, na=False)
            v_total, v_done = len(filtered_df[v_mask]), len(filtered_df[v_mask & (filtered_df['PROSES'] == 'DONE')])
            d_total, d_done = len(filtered_df[~v_mask]), len(filtered_df[~v_mask & (filtered_df['PROSES'] == 'DONE')])

            ig_p = len(filtered_df[(filtered_df['PROSES'] == 'DONE') & (filtered_df['IG'] == False)])
            tt_p = len(filtered_df[(filtered_df['PROSES'] == 'DONE') & (filtered_df['TIKTOK'] == False)])
            yt_p = len(filtered_df[(filtered_df['PROSES'] == 'DONE') & (v_mask) & (filtered_df['YT'] == False)])

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
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<div class="feature-header">🏛️ Sebaran Pilar Konten</div>', unsafe_allow_html=True)
                p_counts = filtered_df['Konten Pillar'].value_counts().reset_index()
                fig_p = px.pie(p_counts, names='Konten Pillar', values='count', hole=0.3, color_discrete_sequence=[BRAND_BLUE, BRAND_YELLOW, "#003A66", "#FFD700"])
                fig_p.update_traces(textinfo='label+value', textfont_size=14)
                fig_p.update_layout(paper_bgcolor='white', legend=dict(font=dict(color=TEXT_BLACK, size=12)), font=dict(color=TEXT_BLACK))
                st.plotly_chart(fig_p, use_container_width=True)

            with c2:
                st.markdown('<div class="feature-header">⚠️ Hutang Produksi per PIC</div>', unsafe_allow_html=True)
                debt = filtered_df[filtered_df['PROSES'] != 'DONE'].groupby('PIC').size().reset_index(name='Hutang')
                fig_d = px.bar(pd.merge(pd.DataFrame({'PIC': list_pic}), debt, on='PIC', how='left').fillna(0), x='PIC', y='Hutang', color_discrete_sequence=[BRAND_BLUE], text_auto=True)
                fig_d.update_layout(paper_bgcolor='white', plot_bgcolor='white', font=dict(color=TEXT_BLACK), xaxis=dict(tickfont=dict(color=TEXT_BLACK)), yaxis=dict(tickfont=dict(color=TEXT_BLACK), gridcolor='#EEE'))
                st.plotly_chart(fig_d, use_container_width=True)

            st.markdown('<div class="feature-header">🕵️ Komparasi Video vs Design per PIC</div>', unsafe_allow_html=True)
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
                fig_br.update_layout(paper_bgcolor='white', plot_bgcolor='white', font=dict(color=TEXT_BLACK), legend=dict(font=dict(color=TEXT_BLACK)))
                fig_br.update_xaxes(tickfont=dict(color=TEXT_BLACK), title_font=dict(color=TEXT_BLACK))
                fig_br.update_yaxes(tickfont=dict(color=TEXT_BLACK), title_font=dict(color=TEXT_BLACK), gridcolor='#EEE')
                st.plotly_chart(fig_br, use_container_width=True)

            st.markdown('<div class="feature-header">📝 Detail Tugas per PIC</div>', unsafe_allow_html=True)
            for name in selected_pic:
                pic_prod = filtered_df[(filtered_df['PIC'] == name) & (filtered_df['PROSES'] != 'DONE')]
                pic_sched = filtered_df[(filtered_df['PIC'] == name) & (filtered_df['PROSES'] == 'DONE') & 
                                        ((filtered_df['IG'] == False) | ((v_mask) & (filtered_df['YT'] == False)) | (filtered_df['TIKTOK'] == False))]
                if not pic_prod.empty or not pic_sched.empty:
                    with st.expander(f"📋 {name} - Audit Pipeline"):
                        if not pic_prod.empty:
                            st.markdown(f"**Hutang Produksi:**")
                            for _, r in pic_prod.iterrows():
                                st.write(f"🔹 **[{r['Kode Konten']}]** {r['Output']}: {r['Judul Konten']}")
                        if not pic_sched.empty:
                            st.markdown(f"**Hutang Scheduling:**")
                            for _, r in pic_sched.iterrows():
                                plts = [p for p in ['IG', 'TIKTOK'] if not r[p]]
                                if "Video" in r['Output'] and not r['YT']: plts.append("YT")
                                if plts: st.warning(f"⚠️ **[{r['Kode Konten']}]** Belum Post di: {', '.join(plts)}")
                else:
                    st.success(f"✅ {name} - Clear!")

            st.markdown('<div class="feature-header">📋 Master Production Pipeline</div>', unsafe_allow_html=True)
            st.dataframe(filtered_df[['Kode Konten', 'Tanggal Deadline', 'Output', 'PIC', 'Judul Konten', 'PROSES', 'IG', 'YT', 'TIKTOK']], use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Kesalahan Teknis Sosmed: {e}")

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
        
        status_col = next((col for col in df_wa.columns if 'Status' in str(col)), None)
        if status_col:
            df_wa.rename(columns={status_col: 'Status'}, inplace=True)
            df_wa['Status'] = df_wa['Status'].astype(str).str.strip().str.title()
        else:
            df_wa['Status'] = ""
            
        if 'Mekari Tag' in df_wa.columns:
            df_wa = df_wa[~df_wa['Mekari Tag'].astype(str).str.contains('Partnership', case=False, na=False)]
        
        st.sidebar.markdown(f"<h2 style='color:{BRAND_BLUE};'>Filter & Search</h2>", unsafe_allow_html=True)
        
        if 'Bulan-Masuk' in df_wa.columns:
            months_wa = df_wa['Bulan-Masuk'].dropna().unique().tolist()
            selected_months_wa = st.sidebar.multiselect("Pilih Bulan:", options=months_wa, default=months_wa, key="wa_bulan")
            df_wa = df_wa[df_wa['Bulan-Masuk'].isin(selected_months_wa)]
            
        search_city = st.sidebar.text_input("Cari Asal Kota/Provinsi:", "", key="wa_search").strip()
        if search_city:
            df_wa = df_wa[df_wa['Asal'].astype(str).str.contains(search_city, case=False, na=False)]

        if not df_wa.empty:
            total_leads = len(df_wa)
            total_closing = len(df_wa[df_wa['Status'].str.contains('Closing', case=False, na=False)])
            conversion_rate = (total_closing / total_leads * 100) if total_leads > 0 else 0
            
            st.markdown('<div class="feature-header">🎯 Real-Time Lead Health Check</div>', unsafe_allow_html=True)
            a1, a2, a3, a4 = st.columns(4)
            a1.metric("Total Leads Terdeteksi 📲", f"{total_leads}")
            a2.metric("Total Sukses Closing 🎓", f"{total_closing} / 45")
            a3.metric("Conversion Rate ⚡", f"{conversion_rate:.1f}%")
            a4.metric("Unique Locations 📍", f"{df_wa['Asal'].nunique()}")

            st.markdown("---")
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown('<div class="feature-header">📊 Funnel Konversi Prospek</div>', unsafe_allow_html=True)
                funnel_order = ["Follow Up", "Daftar", "Interview", "Closing"]
                funnel_data = []
                funnel_data.append(dict(Tahap="Total Leads", Jumlah=total_leads))
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
                fig_funnel.update_layout(
                    paper_bgcolor='white', plot_bgcolor='white', showlegend=False,
                    xaxis_title="", yaxis_title="", yaxis={'categoryorder':'total descending'},
                    font=dict(color="#000000", size=14)
                )
                fig_funnel.update_yaxes(tickfont=dict(color="#000000", family="Arial Black"))
                fig_funnel.update_traces(textposition='outside', cliponaxis=False, textfont=dict(color="#000000", family="Arial Black"))
                st.plotly_chart(fig_funnel, use_container_width=True)

            with c2:
                st.markdown('<div class="feature-header">🌐 Sumber Prospek</div>', unsafe_allow_html=True)
                if 'Sumber (Ads/Organik/Sales)' in df_wa.columns:
                    sumber_counts = df_wa['Sumber (Ads/Organik/Sales)'].value_counts().reset_index()
                    sumber_counts.columns = ['Sumber', 'Jumlah']
                    fig_sumber = px.pie(sumber_counts, names='Sumber', values='Jumlah', hole=0.4, color_discrete_sequence=[BRAND_BLUE, BRAND_YELLOW, "#003A66"])
                    fig_sumber.update_traces(textinfo='label+percent', textfont_color="#000000")
                    fig_sumber.update_layout(paper_bgcolor='white', font=dict(color="#000000"))
                    st.plotly_chart(fig_sumber, use_container_width=True)

            st.markdown('<div class="feature-header">📍 Mapping Persebaran Asal (Seluruh Data)</div>', unsafe_allow_html=True)
            if 'Asal' in df_wa.columns:
                asal_counts = df_wa['Asal'].value_counts().reset_index()
                asal_counts.columns = ['Asal', 'Jumlah']
                asal_counts = asal_counts[asal_counts['Asal'].str.strip() != '']
                dynamic_height = max(400, len(asal_counts) * 25)
                
                fig_asal = px.bar(asal_counts, y='Asal', x='Jumlah', text_auto=True, orientation='h', color_discrete_sequence=[BRAND_BLUE])
                fig_asal.update_layout(
                    paper_bgcolor='white', plot_bgcolor='white', height=dynamic_height,
                    xaxis_title="Jumlah Leads", yaxis_title="", yaxis={'categoryorder':'total ascending'},
                    font=dict(color="#000000", size=12)
                )
                fig_asal.update_yaxes(tickfont=dict(color="#000000", family="Arial Black"))
                fig_asal.update_traces(textfont=dict(color="#000000"), textposition='outside', cliponaxis=False)
                st.plotly_chart(fig_asal, use_container_width=True)

            st.markdown('<div class="feature-header">🏷️ Tagging & Kategori</div>', unsafe_allow_html=True)
            t1, t2 = st.columns(2)
            with t1:
                if 'Mekari Tag' in df_wa.columns:
                    tag_counts = df_wa['Mekari Tag'].value_counts().reset_index()
                    fig_tag = px.bar(tag_counts, y='Mekari Tag', x='count', text_auto=True, orientation='h', color_discrete_sequence=[BRAND_YELLOW])
                    fig_tag.update_layout(paper_bgcolor='white', plot_bgcolor='white', yaxis={'categoryorder':'total ascending'}, font=dict(color="#000000"))
                    fig_tag.update_yaxes(tickfont=dict(color="#000000", family="Arial Black"))
                    st.plotly_chart(fig_tag, use_container_width=True)
            with t2:
                if 'Kategori (Persyaratan/Biaya/Pendaftaran/Loker/dll)' in df_wa.columns:
                    kat_counts = df_wa['Kategori (Persyaratan/Biaya/Pendaftaran/Loker/dll)'].value_counts().reset_index()
                    fig_kat = px.bar(kat_counts, x='Kategori (Persyaratan/Biaya/Pendaftaran/Loker/dll)', y='count', text_auto=True, color_discrete_sequence=[BRAND_BLUE])
                    fig_kat.update_layout(paper_bgcolor='white', plot_bgcolor='white', font=dict(color="#000000"))
                    st.plotly_chart(fig_kat, use_container_width=True)

            st.markdown('<div class="feature-header">📋 Master Database WA Admin (Cek Data Mentah)</div>', unsafe_allow_html=True)
            st.dataframe(df_wa, use_container_width=True, hide_index=True)
            
        else:
            st.warning("⚠️ Data tidak ditemukan. Cek filter atau pastikan data sudah diinput di Tab 4.")
    except Exception as e:
        st.error(f"Kesalahan Teknis: {e}")

if __name__ == "__main__":
    if not st.runtime.exists():
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
