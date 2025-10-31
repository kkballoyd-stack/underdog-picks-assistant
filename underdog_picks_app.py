# underdog_picks_app.py
import streamlit as st
import pandas as pd
import requests
import statsapi
import time
import math

# --------------------
# Helper Functions
# --------------------
def normal_cdf(x, mean=0, std=1):
    """Cumulative distribution function for normal distribution."""
    return 0.5 * (1 + math.erf((x - mean) / (std * math.sqrt(2))))

def grade_edge(p):
    if p is None:
        return None
    pct = p * 100
    if pct >= 70:
        return "A+"
    elif pct >= 65:
        return "A"
    elif pct >= 60:
        return "B"
    elif pct >= 55:
        return "C"
    elif pct >= 50:
        return "D"
    else:
        return "F"

# --------------------
# Roster Fetch Functions
# --------------------
def fetch_nba():
    players = []
    page = 1
    per_page = 100
    while True:
        url = f"https://www.balldontlie.io/api/v1/players?page={page}&per_page={per_page}"
        resp = requests.get(url).json()
        data = resp.get('data', [])
        if not data:
            break
        for p in data:
            players.append({
                "player": f"{p['first_name']} {p['last_name']}",
                "team": p.get('team', {}).get('full_name'),
                "position": p.get('position')
            })
        page += 1
        time.sleep(0.2)
    return pd.DataFrame(players)

def fetch_nfl():
    players = []
    page = 1
    while True:
        url = f"https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?page={page}&limit=500"
        resp = requests.get(url).json()
        data = resp.get('items', [])
        if not data:
            break
        for p in data:
            name = p.get('fullName')
            team = p.get('team', {}).get('displayName') if p.get('team') else None
            pos = p.get('position', {}).get('abbreviation') if p.get('position') else None
            if name:
                players.append({"player": name, "team": team, "position": pos})
        page += 1
        time.sleep(0.2)
    return pd.DataFrame(players).drop_duplicates(subset=["player"])

def fetch_mlb():
    players = []
    teams = statsapi.get('teams', {'sportIds':1})  # MLB sportId=1
    for team in teams:
        roster = statsapi.get('team_roster', {'teamId': team['id']})
        for p in roster.get('roster', []):
            players.append({
                "player": p['person']['fullName'],
                "team": team['name'],
                "position": p['position']['abbreviation']
            })
        time.sleep(0.1)
    return pd.DataFrame(players)

def fetch_nhl():
    players = []
    teams_resp = requests.get("https://statsapi.web.nhl.com/api/v1/teams").json().get('teams', [])
    for t in teams_resp:
        roster = requests.get(f"https://statsapi.web.nhl.com/api/v1/teams/{t['id']}/roster").json().get('roster', [])
        for p in roster:
            players.append({
                "player": p['person']['fullName'],
                "team": t['name'],
                "position": p['position']['code']
            })
        time.sleep(0.1)
    return pd.DataFrame(players)

# --------------------
# Streamlit App Layout
# --------------------
st.set_page_config(page_title="Underdog Picks App", layout="wide")
st.title("📊 Underdog Picks Assistant")

sport = st.selectbox("Select Sport", ["NBA", "NFL", "MLB", "NHL"])

uploaded_file = st.file_uploader(
    f"Upload your CSV for {sport} with columns: player, underdog_line, your_projection, std_dev (optional)",
    type=["csv"]
)

# Fetch roster
with st.spinner("Fetching roster..."):
    if sport == "NBA":
        roster_df = fetch_nba()
    elif sport == "NFL":
        roster_df = fetch_nfl()
    elif sport == "MLB":
        roster_df = fetch_mlb()
    else:
        roster_df = fetch_nhl()

st.write(f"Fetched {len(roster_df)} players for {sport}")

# Merge with user CSV
if uploaded_file is not None:
    user_df = pd.read_csv(uploaded_file)
    if "std_dev" not in user_df.columns:
        user_df["std_dev"] = 6.0
    merged_df = pd.merge(roster_df, user_df, on="player", how="left")
else:
    merged_df = roster_df.copy()
    merged_df["underdog_line"] = None
    merged_df["your_projection"] = None
    merged_df["std_dev"] = None

# Calculate edge & win probability
def calculate_metrics(row):
    try:
        if pd.isna(row['your_projection']) or pd.isna(row['underdog_line']):
            return pd.Series([None, None, None])
        edge_pct = ((row['your_projection'] - row['underdog_line']) / row['underdog_line']) * 100
        win_prob = 1 - normal_cdf(row['underdog_line'], mean=row['your_projection'], std=row['std_dev'])
        grade

