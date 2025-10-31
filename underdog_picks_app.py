# underdog_picks_app_pro.py
import streamlit as st
import pandas as pd
import requests
import math
import time

# --------------------
# Helper Functions
# --------------------
def normal_cdf(x, mean=0, std=1):
    return 0.5 * (1 + math.erf((x - mean) / (std * math.sqrt(2))))

def calculate_edge(projection, line, std_dev=5):
    """Calculate edge % and win probability over line"""
    try:
        edge_pct = ((projection - line) / line) * 100
        win_prob = 1 - normal_cdf(line, mean=projection, std=std_dev)
        grade = "Strong" if win_prob >= 0.65 else "Moderate" if win_prob >= 0.55 else "Weak"
        return pd.Series([edge_pct, win_prob, grade])
    except:
        return pd.Series([0, 0, "N/A"])

# --------------------
# Fetch NBA Active Players & Stats
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
                    "position": p.get('position')
                })
            page += 1
            time.sleep(0.05)
        df = pd.DataFrame(players)
        if df.empty: return pd.DataFrame(columns=["player","team","position","pts","reb","ast","projection"])
        
        # Get season averages
        projections = []
        pts_list, reb_list, ast_list = [], [], []
        for p in df.itertuples():
            try:
                r = requests.get(f"https://www.balldontlie.io/api/v1/season_averages?season=2025&player_ids[]={p.id}")
                r.raise_for_status()
                data = r.json().get('data', [])
                if data:
                    pts = data[0].get('pts', 10)
                    reb = data[0].get('reb', 5)
                    ast = data[0].get('ast', 5)
                else:
                    pts, reb, ast = 10, 5, 5
                projections.append(pts)  # basic pick projection
                pts_list.append(pts)
                reb_list.append(reb)
                ast_list.append(ast)
            except:
                projections.append(10)
                pts_list.append(10)
                reb_list.append(5)
                ast_list.append(5)
            time.sleep(0.05)
        df['projection'] = projections
        df['pts'] = pts_list
        df['reb'] = reb_list
        df['ast'] = ast_list
        df['line'] = df['projection'] * 0.95
        df['std_dev'] = 5
        df[['edge_pct','win_prob','grade']] = df.apply(lambda row: calculate_edge(row['projection'], row['line'], row['std_dev']), axis=1)
        return df
    except:
        return pd.DataFrame(columns=["player","team","position","pts","reb","ast","projection","edge_pct","win_prob","grade"])

# --------------------
# Fetch NFL Active Players & Stats
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
                # simplified projection based on generic metric
                projection = p.get('averageStat', 10)  # fallback
                players.append({
                    "player": name.strip(),
                    "team": team,
                    "position": pos,
                    "projection": projection
                })
            page += 1
            time.sleep(0.05)
        df = pd.DataFrame(players)
        if df.empty: return pd.DataFrame(columns=["player","team","position","projection","edge_pct","win_prob","grade"])
        df['line'] = df['projection'] * 0.95
        df['std_dev'] = 5
        df[['edge_pct','win_prob','grade']] = df.apply(lambda row: calculate_edge(row['projection'], row['line'], row['std_dev']), axis=1)
        return df
    except:
        return pd.DataFrame(columns=["player","team","position","projection","edge_pct","win_prob","grade"])

# --------------------
# Streamlit Layout
# --------------------
st.set_page_config(page_title="Underdog Picks Assistant", layout="wide")
st.title("Underdog Picks Assistant – NBA & NFL")
st.markdown("Analyze real active players, projections, and calculated edges for pick'em advantage.")

tabs = st.tabs(["NBA", "NFL"])

# --------------------
# NBA Tab
# --------------------
with tabs[0]:
    with st.spinner("Loading NBA players..."):
        nba_df = fetch_nba()
    if not nba_df.empty:
        pos_filter = st.multiselect("Filter by position:", options=nba_df['position'].dropna().unique(), default=nba_df['position'].dropna().unique())
        filtered_nba = nba_df[nba_df['position'].isin(pos_filter)]
        
        st.subheader("NBA – Active Players & Stats")
        st.dataframe(filtered_nba[['player','team','position','pts','reb','ast','projection','line','edge_pct','win_prob','grade']].sort_values('edge_pct', ascending=False).reset_index(drop=True))
        st.download_button("Download NBA CSV", filtered_nba.to_csv(index=False).encode('utf-8'), file_name="NBA_Underdog_Picks.csv")
        
        # Top 10 picks
        top10 = filtered_nba.nlargest(10,'edge_pct')
        st.markdown("### Top 10 NBA Picks")
        st.dataframe(top10[['player','team','position','projection','edge_pct','grade']].reset_index(drop=True))
    else:
        st.warning("No NBA data available.")

# --------------------
# NFL Tab
# --------------------
with tabs[1]:
    with st.spinner("Loading NFL players..."):
        nfl_df = fetch_nfl()
    if not nfl_df.empty:
        pos_filter = st.multiselect("Filter by position:", options=nfl_df['position'].dropna().unique(), default=nfl_df['position'].dropna().unique())
        filtered_nfl = nfl_df[nfl_df['position'].isin(pos_filter)]
        
        st.subheader("NFL – Active Players & Stats")
        st.dataframe(filtered_nfl[['player','team','position','projection','line','edge_pct','win_prob','grade']].sort_values('edge_pct', ascending=False).reset_index(drop=True))
        st.download_button("Download NFL CSV", filtered_nfl.to_csv(index=False).encode('utf-8'), file_name="NFL_Underdog_Picks.csv")
        
        # Top 10 picks
        top10 = filtered_nfl.nlargest(10,'edge_pct')
        st.markdown("### Top 10 NFL Picks")
        st.dataframe(top10[['player','team','position','projection','edge_pct','grade']].reset_index(drop=True))
    else:
        st.warning("No NFL data available.")
