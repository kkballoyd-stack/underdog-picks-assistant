# underdog_picks_app_fun.py
import streamlit as st
import pandas as pd
import requests
import time
import math
import plotly.express as px

# --------------------
# Helper Functions
# --------------------
def normal_cdf(x, mean=0, std=1):
    return 0.5 * (1 + math.erf((x - mean) / (std * math.sqrt(2))))

def grade_edge(p):
    if p is None:
        return "N/A"
    pct = p * 100
    if pct >= 70: return "A+ 🏆"
    if pct >= 65: return "A ⚡"
    if pct >= 60: return "B 🔥"
    if pct >= 55: return "C 🌟"
    if pct >= 50: return "D"
    return "F ❌"

def calculate_metrics_safe(row):
    try:
        projection = float(row.get('projection', 10))
        line = float(row.get('line', projection * 0.95))
        std_dev = float(row.get('std_dev', 5))
        edge = ((projection - line) / line) * 100
        win_prob = 1 - normal_cdf(line, mean=projection, std=std_dev)
        grade = grade_edge(win_prob)
        return pd.Series([edge, win_prob, grade])
    except:
        return pd.Series([0.0, 0.0, "N/A"])

# --------------------
# Fetch NBA Players & Stats
# --------------------
@st.cache_data(show_spinner=False)
def fetch_nba():
    players = []
    try:
        page = 1
        while True:
            resp = requests.get(f"https://www.balldontlie.io/api/v1/players?page={page}&per_page=100")
            resp.raise_for_status()
            data = resp.json().get('data', [])
            if not data: break
            for p in data:
                if not p['first_name'] or not p['last_name']: continue
                players.append({
                    "id": p['id'],
                    "player": f"{p['first_name']} {p['last_name']}".strip(),
                    "team": p.get('team', {}).get('full_name'),
                    "position": p.get('position'),
                    "projection": 10
                })
            page += 1
            time.sleep(0.05)
        df = pd.DataFrame(players)
        if df.empty: return pd.DataFrame(columns=["player","team","position","projection"])
        projections = []
        for p in df.itertuples():
            try:
                r = requests.get(f"https://www.balldontlie.io/api/v1/season_averages?season=2025&player_ids[]={p.id}")
                r.raise_for_status()
                data = r.json().get('data', [])
                pts = data[0]['pts'] if data else 10
                projections.append(pts)
            except: projections.append(10)
            time.sleep(0.05)
        df['projection'] = projections
        return df
    except:
        return pd.DataFrame(columns=["player","team","position","projection"])

# --------------------
# Fetch NFL Players
# --------------------
@st.cache_data(show_spinner=False)
def fetch_nfl():
    players = []
    page = 1
    try:
        while True:
            resp = requests.get(f"https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?page={page}&limit=500")
            resp.raise_for_status()
            data = resp.json().get('items', [])
            if not data: break
            for p in data:
                name = p.get('fullName')
                if not name: continue
                team = p.get('team', {}).get('displayName') if p.get('team') else None
                pos = p.get('position', {}).get('abbreviation') if p.get('position') else None
                players.append({
                    "player": name.strip(),
                    "team": team,
                    "position": pos,
                    "projection": 10
                })
            page += 1
            time.sleep(0.05)
        return pd.DataFrame(players)
    except:
        return pd.DataFrame(columns=["player","team","position","projection"])

# --------------------
# Streamlit Layout
# --------------------
st.set_page_config(page_title="Underdog Picks Fun", layout="wide")
st.title("🔥 Underdog Picks Assistant")
st.markdown("Discover your strongest edges in NBA & NFL with visuals, colors, and fun!")

tabs = st.tabs(["NBA", "NFL"])

# --------------------
# NBA Tab
# --------------------
with tabs[0]:
    with st.spinner("Fetching NBA players and stats..."):
        nba_df = fetch_nba()
    if not nba_df.empty:
        nba_df['line'] = nba_df['projection']*0.95
        nba_df['std_dev'] = 5
        metrics = nba_df.apply(calculate_metrics_safe, axis=1)
        metrics.columns = ['edge_pct','win_prob_over','grade']
        nba_df[['edge_pct','win_prob_over','grade']] = metrics

        pos_filter = st.multiselect("Filter by position:", options=nba_df['position'].dropna().unique(), default=nba_df['position'].dropna().unique())
        filtered_nba = nba_df[nba_df['position'].isin(pos_filter)]
        
        st.subheader("NBA – Active Players & Projections")
        st.dataframe(filtered_nba.style.background_gradient(subset=['edge_pct'], cmap='plasma').format({
            "projection":"{:.1f}", "edge_pct":"{:.1f}%", "win_prob_over":"{:.1%}"
        }))

        st.download_button("Download NBA CSV", filtered_nba.to_csv(index=False).encode('utf-8'), file_name="NBA_Underdog_Picks.csv")
        
        # Fun chart: Top 10 edges
        top10 = filtered_nba.nlargest(10, 'edge_pct')
        if not top10.empty:
            fig = px.bar(top10, x='player', y='edge_pct', color='edge_pct', color_continuous_scale='plasma', title="Top 10 NBA Player Edges")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No NBA data available.")

# --------------------
# NFL Tab
# --------------------
with tabs[1]:
    with st.spinner("Fetching NFL players..."):
        nfl_df = fetch_nfl()
    if not nfl_df.empty:
        nfl_df['line'] = nfl_df['projection']*0.95
        nfl_df['std_dev'] = 5
        metrics = nfl_df.apply(calculate_metrics_safe, axis=1)
        metrics.columns = ['edge_pct','win_prob_over','grade']
        nfl_df[['edge_pct','win_prob_over','grade']] = metrics

        pos_filter = st.multiselect("Filter by position:", options=nfl_df['position'].dropna().unique(), default=nfl_df['position'].dropna().unique())
        filtered_nfl = nfl_df[nfl_df['position'].isin(pos_filter)]

        st.subheader("NFL – Active Players & Projections")
        st.dataframe(filtered_nfl.style.background_gradient(subset=['edge_pct'], cmap='plasma').format({
            "projection":"{:.1f}", "edge_pct":"{:.1f}%", "win_prob_over":"{:.1%}"
        }))

        st.download_button("Download NFL CSV", filtered_nfl.to_csv(index=False).encode('utf-8'), file_name="NFL_Underdog_Picks.csv")
        
        # Fun chart: Top 10 edges
        top10 = filtered_nfl.nlargest(10, 'edge_pct')
        if not top10.empty:
            fig = px.bar(top10, x='player', y='edge_pct', color='edge_pct', color_continuous_scale='plasma', title="Top 10 NFL Player Edges")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No NFL data available.")
