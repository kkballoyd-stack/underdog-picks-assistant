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
                    "player": player_name.strip(),
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

@st.cache_data(show_spinner=False)
def fetch_nfl():
    players = []
    page = 1
    while True:
        try:
            resp = requests.get(f"https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?page={page}&limit=500")
            resp.raise_for_status()
            data = resp.json().get('items', [])
            if not data: break
            for p in data:
                name = p.get('fullName')
                team = p.get('team', {}).get('displayName') if p.get('team') else None
                pos = p.get('position', {}).get('abbreviation') if p.get('position') else None
                if name:
                    players.append({"player": name.strip(), "team": team, "position": pos, "projection": 10})  # placeholder projection
            page += 1
            time.sleep(0.05)
        except:
            break
    return pd.DataFrame(players)

@st.cache_data(show_spinner=False)
def fetch_mlb():
    players = []
    try:
        teams = requests.get("https://statsapi.mlb.com/api/v1/teams?sportIds=1").json().get('teams', [])
        for team in teams:
            roster = requests.get(f"https://statsapi.mlb.com/api/v1/teams/{team['id']}/roster").json().get('roster', [])
            for p in roster:
                players.append({
                    "player": p['person']['fullName'].strip(),
                    "team": team['name'],
                    "position": p['position']['abbreviation'],
                    "projection": 10  # placeholder projection
                })
            time.sleep(0.05)
    except: pass
    return pd.DataFrame(players)

@st.cache_data(show_spinner=False)
def fetch_nhl():
    players = []
    try:
        teams = requests.get("https://statsapi.web.nhl.com/api/v1/teams").json().get('teams', [])
        for t in teams:
            roster = requests.get(f"https://statsapi.web.nhl.com/api/v1/teams/{t['id']}/roster").json().get('roster', [])
            for p in roster:
                players.append({
                    "player": p['person']['fullName'].strip(),
                    "team": t['name'],
                    "position": p['position']['code'],
                    "projection": 10  # placeholder projection
                })
            time.sleep(0.05)
    except: pass
    return pd.DataFrame(players)

# --------------------
# Streamlit Layout
# --------------------
st.set_page_config(page_title="Underdog Picks Assistant", layout="wide")
st.title("📊 Underdog Picks Assistant (All Major Sports)")

sport = st.selectbox("Select Sport", ["NBA", "NFL", "MLB", "NHL"])

with st.spinner("Fetching roster and projections..."):
    if sport == "NBA":
        roster_df = fetch_nba()
        stats_df = fetch_nba_stats()
        # Clean up names
        roster_df['player'] = roster_df['player'].astype(str).str.strip()
        stats_df['player'] = stats_df['player'].astype(str).str.strip()
        merged = pd.merge(roster_df, stats_df, on='player', how='left')
        merged['projection'] = merged['projection'].fillna(10)  # fill missing
    elif sport == "NFL":
        merged = fetch_nfl()
    elif sport == "MLB":
        merged = fetch_mlb()
    else:
        merged = fetch_nhl()

# Default Underdog line and std_dev
merged['line'] = merged.get('projection', 10) * 0.95
merged['std_dev'] = 5

# Calculate edge metrics
merged[['edge_pct', 'win_prob_over', 'grade']] = merged.apply(calculate_metrics, axis=1)

# Display table
st.subheader(f"{sport} – Current Roster & Projections")
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
- Rosters come from public legal APIs.  
- Projections are placeholders or season averages (NBA has real stats).  
- `edge_pct`, `win_prob_over`, and `grade` highlight strongest picks.
""")
