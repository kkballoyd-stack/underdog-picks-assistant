# underdog_picks_app.py
import streamlit as st
import pandas as pd
import requests
import time
import math

# --------------------
# Helper Functions
# --------------------
def normal_cdf(x, mean=0, std=1):
    return 0.5 * (1 + math.erf((x - mean) / (std * math.sqrt(2))))

def grade_edge(p):
    if p is None:
        return None
    pct = p * 100
    if pct >= 70: return "A+"
    if pct >= 65: return "A"
    if pct >= 60: return "B"
    if pct >= 55: return "C"
    if pct >= 50: return "D"
    return "F"

def calculate_metrics(row):
    try:
        if pd.isna(row.get('projection')) or pd.isna(row.get('line')) or pd.isna(row.get('std_dev')):
            return pd.Series([None, None, None])
        edge = ((row['projection'] - row['line']) / row['line']) * 100
        win_prob = 1 - normal_cdf(row['line'], mean=row['projection'], std=row['std_dev'])
        grade = grade_edge(win_prob)
        return pd.Series([edge, win_prob, grade])
    except:
        return pd.Series([None, None, None])

# --------------------
# Fetch Rosters and Stats
# --------------------
@st.cache_data(show_spinner=False)
def fetch_nba():
    players, page, per_page = [], 1, 100
    while True:
        try:
            resp = requests.get(f"https://www.balldontlie.io/api/v1/players?page={page}&per_page={per_page}")
            resp.raise_for_status()
            data = resp.json().get('data', [])
            if not data: break
            for p in data:
                players.append({
                    "player": f"{p['first_name']} {p['last_name']}",
                    "team": p.get('team', {}).get('full_name'),
                    "position": p.get('position')
                })
            page += 1
            time.sleep(0.05)
        except:
            break
    return pd.DataFrame(players)

@st.cache_data(show_spinner=False)
def fetch_nba_stats():
    stats_list = []
    page, per_page = 1, 100
    while True:
        try:
            resp = requests.get(f"https://www.balldontlie.io/api/v1/stats?seasons[]=2025&per_page={per_page}&page={page}")
            resp.raise_for_status()
            data = resp.json().get('data', [])
            if not data: break
            for s in data:
                player_name = f"{s['player']['first_name']} {s['player']['last_name']}"
                pts = s.get('pts', 0)
                reb = s.get('reb', 0)
                ast = s.get('ast', 0)
                stats_list.append({
                    "player": player_name,
                    "pts": pts,
                    "reb": reb,
                    "ast": ast,
                    "projection": pts  # simple projection based on season points average
                })
            page += 1
            time.sleep(0.05)
        except:
            break
    return pd.DataFrame(stats_list)

# You can similarly add fetch_nfl(), fetch_mlb(), fetch_nhl() and their stats using public APIs

# --------------------
# Streamlit Layout
# --------------------
st.set_page_config(page_title="Underdog Picks Assistant", layout="wide")
st.title("📊 Underdog Picks Assistant (All Major Sports)")

sport = st.selectbox("Select Sport", ["NBA"])  # Start with NBA for demonstration

with st.spinner("Fetching roster and stats..."):
    if sport == "NBA":
        roster_df = fetch_nba()
        stats_df = fetch_nba_stats()
        merged = pd.merge(roster_df, stats_df, on='player', how='left')
        merged['line'] = merged['projection'] * 0.95  # example: Underdog line is 95% of projected points
        merged['std_dev'] = 5  # default standard deviation

merged[['edge_pct', 'win_prob_over', 'grade']] = merged.apply(calculate_metrics, axis=1)

st.subheader(f"{sport} – Current Roster & Projections")
st.dataframe(merged.sort_values(by='edge_pct', ascending=False), use_container_width=True)

st.download_button(
    "Download CSV",
    merged.to_csv(index=False).encode('utf-8'),
    file_name=f"{sport}_underdog_picks.csv"
)

st.markdown("""
---
**Notes:**  
- Rosters and stats come from public legal APIs.  
- Projections are simple season averages (can be adjusted).  
- `edge_pct`, `win_prob_over`, and `grade` highlight top picks.
""")
