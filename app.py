import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import base64

st.set_page_config(page_title="Pass Map HAC", layout="wide")

# --- CSS : ESTHÉTIQUE ---
st.markdown("""
    <style>
        /* Réduit les marges pour que le terrain prenne toute la place */
        .block-container { padding-top: 1rem; padding-bottom: 1rem; padding-left: 1rem; padding-right: 1rem; }
        [data-testid="stMetricValue"] { font-size: 1.4rem; }
        footer {visibility: hidden;}
        .site-footer {
            text-align: center; color: #888; font-size: 0.9rem; margin-top: 20px; 
            border-top: 1px solid #333; padding-top: 10px; font-family: 'Georgia', serif;
        }
    </style>
""", unsafe_allow_html=True)

# --- 1. CONFIGURATION ---
DATA_FOLDER = '.\data'

def get_available_files():
    if not os.path.exists(DATA_FOLDER):
        try: os.makedirs(DATA_FOLDER)
        except: pass
        return []
    return sorted([f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')])

def get_local_logo():
    if not os.path.exists(DATA_FOLDER): return None
    img_extensions = ['.png', '.jpg', '.jpeg', '.svg', '.webp']
    logo_file = None
    for f in os.listdir(DATA_FOLDER):
        if any(f.lower().endswith(ext) for ext in img_extensions):
            logo_file = os.path.join(DATA_FOLDER, f)
            break
    if logo_file:
        try:
            with open(logo_file, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
            ext = os.path.splitext(logo_file)[1].lower().replace('.', '')
            if ext == 'svg': ext = 'svg+xml'
            return f"data:image/{ext};base64,{encoded_string}"
        except: return None
    return None

@st.cache_data
def load_data(file_path):
    try:
        df = pd.read_csv(file_path)
        if df.shape[1] < 2:
            df = pd.read_csv(file_path, sep=';')
        return df
    except: return None

# --- 2. LOGIQUE TACTIQUE ---
def calculate_progressive(df):
    if 'prog_pass' not in df.columns or 'qualifiers' not in df.columns:
        return pd.Series([False] * len(df), index=df.index)

    q_str = df['qualifiers'].astype(str)
    is_open = ~q_str.str.contains('CornerTaken|Freekick', case=False, regex=True)
    is_standard = (df['prog_pass'] >= 9.11) & (df['x'] >= 35) & is_open
    is_long = q_str.str.contains('Longball', case=False, regex=False)
    is_long_prog = is_long & (df['prog_pass'] >= 4)
    is_forward = df['endX'] > df['x']
    
    return (is_standard | is_long_prog) & is_forward

def get_stats(df_player):
    total = len(df_player)
    success = len(df_player[df_player['outcomeType'] == 'Successful'])
    q_str = df_player['qualifiers'].astype(str)
    key = q_str.str.contains('KeyPass', case=False, regex=False).sum()
    ast = q_str.str.contains('GoalAssist', case=False, regex=False).sum()
    prog = len(df_player[df_player['is_progressive'] & (df_player['outcomeType'] == 'Successful')])
    return total, success, key, ast, prog

def create_uefa_pitch():
    length, width = 105.0, 68.0
    lc = "white"
    shapes = [
        dict(type="rect", x0=0, y0=0, x1=length, y1=width, line=dict(color=lc, width=2), layer="below"),
        dict(type="line", x0=length/2, y0=0, x1=length/2, y1=width, line=dict(color=lc, width=2), layer="below"),
        dict(type="circle", x0=length/2-9.15, y0=width/2-9.15, x1=length/2+9.15, y1=width/2+9.15, line=dict(color=lc, width=2), layer="below"),
        dict(type="circle", x0=length/2-0.3, y0=width/2-0.3, x1=length/2+0.3, y1=width/2+0.3, fillcolor=lc, line=dict(width=0)),
        dict(type="rect", x0=0, y0=width/2-20.16, x1=16.5, y1=width/2+20.16, line=dict(color=lc, width=2), layer="below"),
        dict(type="rect", x0=length-16.5, y0=width/2-20.16, x1=length, y1=width/2+20.16, line=dict(color=lc, width=2), layer="below"),
        dict(type="rect", x0=0, y0=width/2-9.16, x1=5.5, y1=width/2+9.16, line=dict(color=lc, width=2), layer="below"),
        dict(type="rect", x0=length-5.5, y0=width/2-9.16, x1=length, y1=width/2+9.16, line=dict(color=lc, width=2), layer="below"),
        dict(type="circle", x0=11-0.3, y0=width/2-0.3, x1=11+0.3, y1=width/2+0.3, fillcolor=lc, line=dict(width=0)),
        dict(type="circle", x0=length-11-0.3, y0=width/2-0.3, x1=length-11+0.3, y1=width/2+0.3, fillcolor=lc, line=dict(width=0)),
    ]
    return shapes, length, width

# --- 3. INTERFACE ---
with st.sidebar:
    st.header("⚽ Analyse HAC")
    files = get_available_files()
    if not files:
        st.error(f"Aucun CSV trouvé dans `{DATA_FOLDER}`.")
        st.stop()
    
    selected_file = st.selectbox("Match", files, format_func=lambda x: x.replace(".csv", ""))
    file_path = os.path.join(DATA_FOLDER, selected_file)
    df = load_data(file_path)

    if df is not None:
        if 'teamName' in df.columns:
            df_hac = df[df['teamName'] == 'Le Havre']
            pool = df_hac if not df_hac.empty else df
        else: pool = df
        
        plist = sorted(pool['name'].dropna().unique())
        player_name = st.selectbox("Joueur", plist, index=0)
        
        st.divider()
        st.subheader("Filtres")
        f_success = st.checkbox("✅ Passes Réussies", value=False)
        f_prog = st.checkbox("🚀 Progressives", value=False)

# --- 4. VISUALISATION ---
if df is not None:
    df_p = df[(df['name'] == player_name) & (df['type'] == 'Pass')].copy()
    df_p['is_progressive'] = calculate_progressive(df_p)
    
    q_str = df_p['qualifiers'].astype(str)
    df_p['is_assist'] = q_str.str.contains('GoalAssist', case=False, regex=False)
    df_p['is_keypass'] = q_str.str.contains('KeyPass', case=False, regex=False) & ~df_p['is_assist']
    
    tot, suc, key, ast, prog = get_stats(df_p)
    pct = (suc / tot * 100) if tot > 0 else 0

    st.title(f"📊 {player_name}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Volume", f"{suc}/{tot}", f"{pct:.0f}%")
    c2.metric("Clés", key)
    c3.metric("Décisives", ast)
    c4.metric("Progressives", prog)

    df_viz = df_p.copy()
    if f_success: df_viz = df_viz[df_viz['outcomeType'] == 'Successful']
    if f_prog: df_viz = df_viz[df_viz['is_progressive']]

    receivers = []
    for i, row in df_viz.iterrows():
        try:
            nxt = df.loc[i + 1]
            receivers.append(nxt['name'] if nxt['teamId'] == row['teamId'] else "Perte")
        except: receivers.append("-")
    df_viz['receiver'] = receivers

    shapes, length, width = create_uefa_pitch()
    
    layout = go.Layout(
        shapes=shapes,
        plot_bgcolor="#1e1e1e", paper_bgcolor="#1e1e1e",
        xaxis=dict(visible=False, range=[-1, length+1], fixedrange=True),
        yaxis=dict(visible=False, range=[-1, width+1], fixedrange=True, scaleanchor="x", scaleratio=1),
        # MARGE RÉDUITE + HAUTEUR AUGMENTÉE (800px)
        margin=dict(l=5, r=5, t=40, b=5),
        height=800, 
        showlegend=True,
        legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center", font=dict(color="white"), bgcolor="rgba(0,0,0,0)", itemclick=False, itemdoubleclick=False)
    )
    
    fig = go.Figure(layout=layout)
    
    logo_base64 = get_local_logo()
    if logo_base64:
        fig.add_layout_image(dict(
            source=logo_base64, xref="x", yref="y", x=2, y=2, sizex=12, sizey=12,
            opacity=0.3, layer="below", sizing="contain", xanchor="left", yanchor="bottom"
        ))
    else:
        fig.add_annotation(text="Logo introuvable", x=2, y=2, showarrow=False, font=dict(color="gray"))

    fig.add_annotation(
        text="<i>Viz by @alex8841t</i>",
        xref="x", yref="y", x=length - 2, y=2, showarrow=False,
        xanchor="right", yanchor="bottom",
        font=dict(color="rgba(255,255,255,0.6)", size=16, family="Georgia")
    )

    # TRACES : On utilise endX / endY pour les marqueurs
    df_no = df_viz[df_viz['outcomeType'] != 'Successful']
    df_ok = df_viz[df_viz['outcomeType'] == 'Successful']
    df_ast = df_ok[df_ok['is_assist']]
    df_kp = df_ok[df_ok['is_keypass']]
    df_nrm = df_ok[~df_ok['is_assist'] & ~df_ok['is_keypass']]

    # Ratées
    if not df_no.empty:
        for _, r in df_no.iterrows():
            fig.add_trace(go.Scatter(x=[r['x'], r['endX']], y=[r['y'], r['endY']], mode='lines', line=dict(color='#ef553b', width=1, dash='dot'), opacity=0.5, showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=df_no['endX'], y=df_no['endY'], mode='markers', name='Ratées', marker=dict(size=6, color='#1e1e1e', symbol='x', line=dict(width=1, color='#ef553b')), text=df_no['receiver'], hovertemplate="<b>Perte</b><br>%{customdata}'<extra></extra>", customdata=df_no['minute']))
    
    # Normales
    if not df_nrm.empty:
        for _, r in df_nrm.iterrows():
            fig.add_trace(go.Scatter(x=[r['x'], r['endX']], y=[r['y'], r['endY']], mode='lines', line=dict(color='#00cc96', width=2), opacity=0.6, showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=df_nrm['endX'], y=df_nrm['endY'], mode='markers', name='Réussies', marker=dict(size=6, color='#1e1e1e', line=dict(width=1, color='#00cc96')), text=df_nrm['receiver'], hovertemplate="<b>%{text}</b><br>%{customdata}'<extra></extra>", customdata=df_nrm['minute']))
    
    # Clés
    if not df_kp.empty:
        for _, r in df_kp.iterrows():
            fig.add_trace(go.Scatter(x=[r['x'], r['endX']], y=[r['y'], r['endY']], mode='lines', line=dict(color='#FFD700', width=3), opacity=0.9, showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=df_kp['endX'], y=df_kp['endY'], mode='markers', name='Passes Clés', marker=dict(size=10, color='#FFD700', symbol='star', line=dict(width=1, color='white')), text=df_kp['receiver'], hovertemplate="<b>🔑 Clé</b><br>%{text}<br>%{customdata}'<extra></extra>", customdata=df_kp['minute']))
    
    # Décisives
    if not df_ast.empty:
        for _, r in df_ast.iterrows():
            fig.add_trace(go.Scatter(x=[r['x'], r['endX']], y=[r['y'], r['endY']], mode='lines', line=dict(color='#00BFFF', width=4), opacity=1, showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=df_ast['endX'], y=df_ast['endY'], mode='markers', name='Assists', marker=dict(size=12, color='#00BFFF', symbol='diamond', line=dict(width=1, color='white')), text=df_ast['receiver'], hovertemplate="<b>🅰️ ASSIST</b><br>%{text}<br>%{customdata}'<extra></extra>", customdata=df_ast['minute']))

    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="site-footer">Data Visualization by @alex8841t</div>', unsafe_allow_html=True)

