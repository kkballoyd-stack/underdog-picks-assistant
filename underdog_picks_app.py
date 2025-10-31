# underdog_picks_app_cached.py
import streamlit as st
import pandas as pd
import requests
import math
import time
from datetime import datetime

# --------------------
# Helper Functions
# --------------------
def normal_cdf(x, mean=0, std=1):
    return 0.5 * (1 + math.erf((x - mean) / (std * math.sqrt(2))))

def calculate_edge(projection, line, std_dev=5):
    try:
        edge_pct = ((projection - line) / line) * 100
        win_prob = 1 - normal_cdf(line, mean=projection, std=std_dev)
        grade = "Strong" if win_prob >= 0.65 else "Moderate" if win_prob >= 0.55 else "Weak"
        return pd.Series([edge_pct, win_prob, grade])
    except:
        return pd.Series([0.0, 0.0, "N/A"])

# --------------------
# Cached NBA Fetch
# --------------------
@st.cache_data(show_spinner=False)
def fetch_nba(season=2025):
    players = []
    page = 1
    while True:
        resp = requests.get(f"https://www.balldontlie.io/api/v1/players?page={page}&per_page=100")
        if resp.status_code != 200:
            break
        data = resp.json().get('data', [])
        if not data:
            break
        for p in data:
            if p.get('first_name') and p.get('last_name') and p.get('team'):
                players.append({
                    "id": p['id'],
                    "player": f"{p['first_name']} {p['last_name']}".strip(),
                    "team": p.get('team', {}).get('full_name'),
                    "position": p.get('position')
                })
        page += 1
        time.sleep(0.05)

    df = pd.DataFrame(players)
    if df.empty: return df

    # Add projections
    projections = []
    for p in df.itertuples():
        try:
            r = requests.get(f"https://www.balldontlie.io/api/v1/season_averages?season={season}&player_ids[]={p.id}")
            d = r.json().get('data', [])
            pts = d[0].get('pts', 10) if d else 10
        except:
            pts = 10
        projections.append(pts)
        time.sleep(0.02)

    df['projection'] = projections
    df['line'] = df['projection'] * 0.95
    df['std_dev'] = 5
    df[['edge_pct', 'win_prob', 'grade']] = df.apply(lambda r: calculate_edge(r['projection'], r['line'], r['std_dev']), axis=1)
    return df

# --------------------
# Cached NFL Fetch (Simulated for cache + reliability)
# --------------------
@st.cache_data(show_spinner=False)
def fetch_nfl():
    # For simplicity, we'll simulate active NFL players + stats
    # In production, you could replace with a CSV or API with real data
    data = [
        {"player": "Patrick Mahomes", "team": "KC Chiefs", "position": "QB", "pass_yds": 4200, "rush_yds": 150, "pass_td": 38, "rush_td": 2},
        {"player": "Derrick Henry", "team": "TEN Titans", "position": "RB", "rush_yds": 1800, "rush_td": 17, "pass_yds":0, "pass_td":0},
        {"player": "Davante Adams", "team": "LV Raiders", "position": "WR", "rec_yds": 1300, "rec_td": 12, "pass_yds":0, "pass_td":0, "rush_yds":0, "rush_td":0},
        # Add more cached players as needed
    ]
    df = pd.DataFrame(data).fillna(0)
    # Projection = yards + TDs*6
    df['projection'] = df['pass_yds'] + df['rush_yds'] + df['rec_yds'] + (df['pass_td']+df['rush_td']+df['rec_td'])*6
    df['line'] = df['projection'] * 0.95
    df['std_dev'] = df['projection'] * 0.15 + 5
    df[['edge_pct','win_prob','grade']] = df.apply(lambda r: calculate_edge(r['projection'], r['line'], r['std_dev']), axis=1)
    return df

# --------------------
# Streamlit Layout
# --------------------
st.set_page_config(page_title="Underdog Picks Assistant", layout="wide")
st.title("Underdog Picks Assistant – NBA & NFL")
st.markdown(f"Cached active players with projections and calculated edges. Data cached at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.")

tabs = st.tabs(["NBA", "NFL"])

# --------------------
# NBA Tab
# --------------------
with tabs[0]:
    nba_df = fetch_nba()
    if not nba_df.empty:
        pos_filter = st.multiselect("Filter NBA by position:", options=nba_df['position'].dropna().unique(), default=nba_df['position'].dropna().unique())
        filtered_nba = nba_df[nba_df['position'].isin(pos_filter)]
        st.subheader("NBA – Active Players & Stats")
        st.dataframe(filtered_nba[['player','team','position','projection','line','edge_pct','win_prob','grade']].sort_values('edge_pct', ascending=False).reset_index(drop=True))
        st.download_button("Download NBA CSV", filtered_nba.to_csv(index=False).encode('utf-8'), file_name="NBA_Underdog_Picks.csv")
    else:
        st.warning("No NBA data available.")

# --------------------
# NFL Tab
# --------------------
with tabs[1]:
    nfl_df = fetch_nfl()
    if not nfl_df.empty:
        pos_filter = st.multiselect("Filter NFL by position:", options=nfl_df['position'].dropna().unique(), default=nfl_df['position'].dropna().unique())
        filtered_nfl = nfl_df[nfl_df['position'].isin(pos_filter)]
        st.subheader("NFL – Active Players & Stats")
        st.dataframe(filtered_nfl[['player','team','position','projection','line','edge_pct','win_prob','grade']].sort_values('edge_pct', ascending=False).reset_index(drop=True))
        st.download_button("Download NFL CSV", filtered_nfl.to_csv(index=False).encode('utf-8'), file_name="NFL_Underdog_Picks.csv")
    else:
        st.warning("No NFL data available.")
