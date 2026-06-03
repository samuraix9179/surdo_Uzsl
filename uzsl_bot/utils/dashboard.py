import json
import os
import sys

try:
    import streamlit as st
    import pandas as pd
    import plotly.graph_objects as go
except ImportError:
    print("⚠️ Ushbu vizual dashboardni ishlatish uchun zaruriy kutubxonalarni o'rnating:")
    print("   pip install streamlit pandas plotly")
    sys.exit(1)

EXPORT_DIR = "exports"
METADATA_PATH = os.path.join(EXPORT_DIR, "metadata.json")
LANDMARKS_DIR = os.path.join(EXPORT_DIR, "landmarks")

# Main page configuration
st.set_page_config(
    page_title="UZSL Dataset Visual Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Theme Styling
st.markdown("""
<style>
    .main-title {
        font-size: 38px;
        font-weight: 800;
        color: #673AB7;
        margin-bottom: 5px;
    }
    .sub-title {
        font-size: 16px;
        color: #757575;
        margin-bottom: 25px;
    }
    .metric-card {
        background-color: #f3e5f5;
        border-left: 5px solid #673AB7;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_value=True)


# Load metadata
@st.cache_data
def load_metadata():
    if not os.path.exists(METADATA_PATH):
        return None
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


data = load_metadata()

# Sidebar Config
st.sidebar.markdown("## ⚙️ Sozlamalar")
st.sidebar.info("O'zbek Imo-ishora Tili (UZSL) datasetlarini visual tahlil qilish va 3D skelet nuqtalarini ko'rish uchun interaktiv panel.")

if data is None:
    st.markdown("<div class='main-title'>📊 UZSL Dataset Visual Dashboard</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>O'zbek Surdo Tili Dataset monitoringi va 3D skelet visualizatori</div>", unsafe_allow_html=True)
    
    st.warning("⚠️ **Dataset ma'lumotlari topilmadi!**")
    st.markdown("""
    Dashboard ishlashi uchun avval ko'ngillilar yuborgan videolarni eksport qilishingiz kerak.
    Quyidagi buyruqlarni terminalda bajaring:
    
    ```bash
    # 1. Videolarni va metadatani yuklab olish
    python -m utils.export
    
    # 2. Videolardan landmark nuqtalarini ajratib olish
    python -m utils.extract_landmarks
    ```
    """)
else:
    df = pd.DataFrame(data)

    # 1. Header Section
    st.markdown("<div class='main-title'>📊 UZSL Dataset Visual Dashboard</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='sub-title'>Jami {len(df)} ta tasdiqlangan UZSL video datasetlari va 3D harakat nuqtalari tahlili</div>", unsafe_allow_html=True)

    # Tabs
    tab_stats, tab_3d, tab_progress = st.tabs(["📊 Global Tahlil (Analytics)", "🧬 3D Skelet Visualizatori", "📈 Progress Tracker"])

    # --- TAB 1: Global Stats ---
    with tab_stats:
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("""
            <div class='metric-card'>
                <span style='font-size: 14px; color: #555;'>🎬 Jami videolar</span><br>
                <span style='font-size: 32px; font-weight: bold; color: #311B92;'>{}</span>
            </div>
            """.format(len(df)), unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div class='metric-card'>
                <span style='font-size: 14px; color: #555;'>🏷️ Jami so'zlar</span><br>
                <span style='font-size: 32px; font-weight: bold; color: #311B92;'>{}</span>
            </div>
            """.format(df['word_uz'].nunique()), unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div class='metric-card'>
                <span style='font-size: 14px; color: #555;'>📂 Kategoriyalar</span><br>
                <span style='font-size: 32px; font-weight: bold; color: #311B92;'>{}</span>
            </div>
            """.format(df['category'].nunique()), unsafe_allow_html=True)
        with col4:
            st.markdown("""
            <div class='metric-card'>
                <span style='font-size: 14px; color: #555;'>👤 Ko'ngillilar (vols)</span><br>
                <span style='font-size: 32px; font-weight: bold; color: #311B92;'>{}</span>
            </div>
            """.format(df['user_id'].nunique()), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Charts row
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.subheader("📁 Kategoriyalar Progressi")
            cat_counts = df['category'].value_counts().reset_index()
            cat_counts.columns = ['Category', 'Videos']
            fig1 = go.Figure(data=[go.Pie(
                labels=cat_counts['Category'],
                values=cat_counts['Videos'],
                hole=.3,
                marker_colors=['#673AB7', '#9C27B0', '#E91E63', '#00BCD4', '#4CAF50', '#FFEB3B', '#FF9800']
            )])
            fig1.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=350)
            st.plotly_chart(fig1, use_container_width=True)

        with chart_col2:
            st.subheader("🎥 Video davomiyligi bo'yicha taqsimot")
            fig2 = go.Figure(data=[go.Histogram(
                x=df['duration_seconds'],
                nbinsx=15,
                marker_color='#9C27B0',
                opacity=0.75
            )])
            fig2.update_layout(
                xaxis_title="Davomiylik (soniya)",
                yaxis_title="Videolar soni",
                margin=dict(t=10, b=10, l=10, r=10),
                height=350,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Searchable Table
        st.subheader("📋 Barcha tasdiqlangan videolar ro'yxati")
        st.dataframe(
            df[['video_id', 'user_id', 'word_uz', 'category', 'duration_seconds', 'file_size_bytes', 'submitted_at']],
            use_container_width=True
        )

    # --- TAB 2: 3D Skeleton Visualizer ---
    with tab_3d:
        st.subheader("🧬 3D Kadr nuqtalari tahlili")
        st.markdown("Ushbu bo'limda yuborilgan videolardan MediaPipe Holistic ajratib olgan **543 ta nuqtalarning** 3D harakatini kadrlar bo'yicha interaktiv kuzatishingiz mumkin.")

        # Selection controls
        sel_col1, sel_col2, sel_col3 = st.columns(3)
        with sel_col1:
            categories = sorted(df['category'].unique())
            sel_cat = st.selectbox("📂 Kategoriyani tanlang", categories)

        with sel_col2:
            words = sorted(df[df['category'] == sel_cat]['word_uz'].unique())
            sel_word = st.selectbox("🏷️ So'zni tanlang", words)

        with sel_col3:
            videos = df[(df['category'] == sel_cat) & (df['word_uz'] == sel_word)]
            video_options = {f"video_id: {r['video_id']} (User: {r['user_id']})": r for _, r in videos.iterrows()}
            sel_vid_label = st.selectbox("🎥 Video namunani tanlang", list(video_options.keys()))
            selected_video = video_options[sel_vid_label]

        # Load landmark JSON file
        json_filename = f"{selected_video['video_id']}_{selected_video['user_id']}.json"
        json_path = os.path.join(LANDMARKS_DIR, sel_word, json_filename)

        if not os.path.exists(json_path):
            st.error(f"❌ '{json_path}' fayli topilmadi. Avval nuqtalarni ajratish uchun `python -m utils.extract_landmarks` skriptini ishga tushiring.")
        else:
            with open(json_path, "r", encoding="utf-8") as f:
                landmark_data = json.load(f)

            frames_count = landmark_data.get("frames_count", 0)
            sequence = landmark_data.get("sequence", [])

            if frames_count == 0 or not sequence:
                st.warning("⚠️ Ushbu videoda kadrlar nuqtasi aniqlanmadi.")
            else:
                # Frame Selector Slider
                st.markdown("### 🎥 Kadrni tanlang (Frame Selection)")
                sel_frame = st.slider("Joriy kadr", 1, frames_count, 1) - 1

                # Extract landmark groups for the selected frame
                frame_data = sequence[sel_frame]
                pose_coords = frame_data["pose"]
                face_coords = frame_data["face"]
                lh_coords = frame_data["left_hand"]
                rh_coords = frame_data["right_hand"]

                # Convert flat lists to x, y, z chunks
                def chunk_coords(flat_list):
                    xs, ys, zs = [], [], []
                    for i in range(0, len(flat_list), 3):
                        xs.append(flat_list[i])
                        ys.append(flat_list[i+1])
                        zs.append(flat_list[i+2])
                    return xs, ys, zs

                px, py, pz = chunk_coords(pose_coords)
                fx, fy, fz = chunk_coords(face_coords)
                lx, ly, lz = chunk_coords(lh_coords)
                rx, ry, rz = chunk_coords(rh_coords)

                # Connect hand points for rendering lines
                hand_connections = [
                    (0, 1), (1, 2), (2, 3), (3, 4),  # thumb
                    (0, 5), (5, 6), (6, 7), (7, 8),  # index
                    (5, 9), (9, 10), (10, 11), (11, 12),  # middle
                    (9, 13), (13, 14), (14, 15), (15, 16),  # ring
                    (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)  # pinky/palm
                ]

                # Create 3D Plotly Figure
                fig_3d = go.Figure()

                # 1. Pose landmarks (green scatter)
                if px:
                    fig_3d.add_trace(go.Scatter3d(
                        x=px, y=py, z=pz,
                        mode='markers',
                        marker=dict(size=4, color='#4CAF50'),
                        name='Tana (Pose)'
                    ))

                # 2. Face landmarks (grey scatter - small)
                if fx:
                    fig_3d.add_trace(go.Scatter3d(
                        x=fx, y=fy, z=fz,
                        mode='markers',
                        marker=dict(size=1.5, color='#BDBDBD', opacity=0.5),
                        name='Yuz (Face)'
                    ))

                # 3. Left Hand (blue scatter + lines)
                if lx:
                    fig_3d.add_trace(go.Scatter3d(
                        x=lx, y=ly, z=lz,
                        mode='markers',
                        marker=dict(size=4, color='#00BCD4'),
                        name='Chap qo\'l'
                    ))
                    # Draw skeletal connections
                    for c in hand_connections:
                        fig_3d.add_trace(go.Scatter3d(
                            x=[lx[c[0]], lx[c[1]]],
                            y=[ly[c[0]], ly[c[1]]],
                            z=[lz[c[0]], lz[c[1]]],
                            mode='lines',
                            line=dict(color='#00E5FF', width=3),
                            showlegend=False
                        ))

                # 4. Right Hand (orange scatter + lines)
                if rx:
                    fig_3d.add_trace(go.Scatter3d(
                        x=rx, y=ry, z=rz,
                        mode='markers',
                        marker=dict(size=4, color='#FF9800'),
                        name='O\'ng qo\'l'
                    ))
                    # Draw skeletal connections
                    for c in hand_connections:
                        fig_3d.add_trace(go.Scatter3d(
                            x=[rx[c[0]], rx[c[1]]],
                            y=[ry[c[0]], ry[c[1]]],
                            z=[rz[c[0]], rz[c[1]]],
                            mode='lines',
                            line=dict(color='#FFAB40', width=3),
                            showlegend=False
                        ))

                # Setup Layout (lock camera angles and aspect ratios)
                fig_3d.update_layout(
                    margin=dict(l=0, r=0, b=0, t=30),
                    height=600,
                    scene=dict(
                        xaxis=dict(title="X", backgroundcolor="rgb(20, 20, 20)", gridcolor="grey", showbackground=True),
                        yaxis=dict(title="Y", backgroundcolor="rgb(20, 20, 20)", gridcolor="grey", showbackground=True),
                        zaxis=dict(title="Z", backgroundcolor="rgb(20, 20, 20)", gridcolor="grey", showbackground=True),
                        aspectmode='cube'
                    ),
                    paper_bgcolor='rgba(15,15,15,0.95)',
                    font_color='white'
                )

                st.plotly_chart(fig_3d, use_container_width=True)

    # --- TAB 3: Progress Tracker ---
    with tab_progress:
        st.subheader("📈 Belgilar bo'yicha progress (Target: 50 ta video)")
        st.markdown("Neyron tarmoqni mukammal o'qitish uchun har bir surdo belgisiga kamida **50 ta tasdiqlangan video** kerak. Quyida joriy yig'ilish progressini ko'rishingiz mumkin:")

        # Calculate counts per label
        counts = df['word_uz'].value_counts().reset_index()
        counts.columns = ['Word', 'Current']
        
        # Merge with categories to show full info
        word_info = df[['word_uz', 'category']].drop_duplicates().merge(counts, left_on='word_uz', right_on='Word')
        word_info['Target'] = 50
        word_info['Progress (%)'] = (word_info['Current'] / word_info['Target'] * 100).clip(upper=100.0).round(1)

        # Style layout bars
        st.dataframe(
            word_info[['word_uz', 'category', 'Current', 'Target', 'Progress (%)']].sort_values(by='Current', ascending=True),
            use_container_width=True
        )
