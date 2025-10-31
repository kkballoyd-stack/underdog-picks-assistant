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
# Fetch NBA Data
# --------------------
@st.cache_data(show_spinner=False)
def fetch_nba_roster_and_stats(season=2025):
    # Fetch current NBA players
    players, page, per_page = [], 1, 100
    while True:
        try:
            resp = requests.get(f"https://www.balldontlie.io/api/v1/players?page={page}&per_page={per_page}")
            resp.raise_for_status()
            data = resp.json().get('data', [])
            if not data:
                break
            for p in data:
                full_name = f"{p['first_name']} {p['last_name']}".strip()
                players.append({"player": full_name, "team": p.get('team', {}).get('full_name'), "position": p.get('position')})
            page += 1
            time.sleep(0.05)
        except:
            break
    roster_df = pd.DataFrame(players)

    # Fetch season averages for projections
    stats_list, page = [], 1
    while True:
        try:
            resp = requests.get(f"https://www.balldontlie.io/api/v1/stats?seasons[]={season}&per_page=100&page={page}")
            resp.raise_for_status()
            data = resp.json().get('data', [])
            if not data:
                break
            for s in data:
                player_name = f"{s['player']['first_name']} {s['player']['last_name']}".strip()
                pts = s.get('pts', 0)
                reb = s.get('reb', 0)
                ast = s.get('ast', 0)
                stats_list.append({"player": player_name, "projection": pts})
            page += 1
            time.sleep(0.05)
        except:
            break
    stats_df = pd.DataFrame(stats_list)

    # Clean and merge
    roster_df['player'] = roster_df['player'].astype(str).str.strip()
    if not stats_df.empty and 'player' in stats_df.columns:
        stats_df['player'] = stats_df['player'].astype(str).str.strip()
        merged = pd.merge(roster_df, stats_df, on='player', how='left')
        merged['projection'] = merged.get('projection', 10).fillna(10)
    else:
        merged = roster_df.copy()
        merged['projection'] = 10

    return merged

# --------------------
# Fetch NFL Data
# --------------------
@st.cache_data(show_spinner=False)
def fetch_nfl_roster():
    players, page = [], 1
    while True:
        try:
            resp = requests.get(f"https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?page={page}&limit=500")
            resp.raise_for_status()
            data = resp.json().get('items', [])
            if not data:
                break
            for p in data:
                name = p.get('fullName')
                if not name:
                    continue
                team = p.get('team', {}).get('displayName') if p.get('team') else None
                pos = p.get('position', {}).get('abbreviation') if p.get('position') else None
                players.append({"player": name.strip(), "team": team, "position": pos, "projection": 10})
            page += 1
            time.sleep(0.05)
        except:
            break
    df = pd.DataFrame(players)
    if 'player' not in df.columns and not df.empty:
        df['player'] = df.iloc[:, 0].astype(str).str.strip()
    if 'projection' not in df.columns:
        df['projection'] = 10
    return df

# --------------------
# Streamlit Layout
# --------------------
st.set_page_config(page_title="Underdog Picks Assistant", layout="wide")
st.title("📊 Underdog Picks Assistant (NBA & NFL Only)")

sport = st.selectbox("Select Sport", ["NBA", "NFL"])

with st.spinner("Fetching current roster and projections..."):
    if sport == "NBA":
        merged = fetch_nba_roster_and_stats()
    else:
        merged = fetch_nfl_roster()

# Default Underdog line and std_dev
merged['line'] = merged.get('projection', 10) * 0.95
merged['std_dev'] = 5

# Calculate edge metrics
merged[['edge_pct', 'win_prob_over', 'grade']] = merged.apply(calculate_metrics, axis=1)

# Display table
st.subheader(f"{sport} – Current Active Players & Projections")
st.dataframe(merged.sort_values(by='edge_pct', ascending=False), use_container_width=True)

# Download CSV
st.download_button(
    "Download CSV",
    merged.to_csv(index=False).encode('utf-8'),
    file_name=f"{sport}_underdog_picks.csv"
)

st.markdown("""
---
**Notes:**  
- Only active players are included.  
- NBA projections are from Balldontlie season stats.  
- NFL projections are default 10 (can be replaced with real stats later).  
- `edge_pct`, `win_prob_over`, and `grade` highlight strongest picks.
""")
