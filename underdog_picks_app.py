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

# --------------------
# Roster Fetch Functions
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
            time.sleep(0.1)
        except:
            break
    return pd.DataFrame(players)

@st.cache_data(show_spinner=False)
def fetch_nfl():
    players = []
    page = 1
    while True:
        try:
            resp = requests.get(f"https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?page={page}&limit=500")
            resp.raise_for_status()
            data = resp.json().get('items', [])
            if not data:
                break
            for p in data:
                name = p.get('fullName')
                team = p.get('team', {}).get('displayName') if p.get('team') else None
                pos = p.get('position', {}).get('abbreviation') if p.get('position') else None
                if name:
                    players.append({"player": name, "team": team, "position": pos})
            page += 1
            time.sleep(0.1)
        except:
            break
    return pd.DataFrame(players).drop_duplicates(subset=["player"])

@st.cache_data(show_spinner=False)
def fetch_mlb():
    players = []
    try:
        teams = statsapi.get('teams', {'sportIds':1})
        for team in teams:
            roster = statsapi.get('team_roster', {'teamId': team['id']})
            for p in roster.get('roster', []):
                players.append({
                    "player": p['person']['fullName'],
                    "team": team['name'],
                    "position": p['position']['abbreviation']
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
                    "player": p['person']['fullName'],
                    "team": t['name'],
                    "position": p['position']['code']
                })
            time.sleep(0.05)
    except: pass
    return pd.DataFrame(players)

# --------------------
# Metrics Calculation
# --------------------
def calculate_metrics(row):
    try:
        if pd.isna(row.get('your_projection')) or pd.isna(row.get('underdog_line')) or pd.isna(row.get('std_dev')):
            return pd.Series([None, None, None])
        edge = ((row['your_projection'] - row['underdog_line']) / row['underdog_line']) * 100
        win_prob = 1 - normal_cdf(row['underdog_line'], mean=row['your_projection'], std=row['std_dev'])
        grade = grade_edge(win_prob)
        return pd.Series([edge, win_prob, grade])
    except:
        return pd.Series([None, None, None])

# --------------------
# Streamlit Layout
# --------------------
st.set_page_config(page_title="Underdog Picks Assistant", layout="wide")
st.title("📊 Underdog Picks Assistant (All Major Sports)")

sport = st.selectbox("Select Sport", ["NBA","NFL","MLB","NHL"])
uploaded_file = st.file_uploader(
    f"Upload your CSV for {sport} with columns: player, underdog_line, your_projection, std_dev (optional)",
    type=["csv"]
)

with st.spinner("Fetching roster..."):
    if sport == "NBA": roster_df = fetch_nba()
    elif sport == "NFL": roster_df = fetch_nfl()
    elif sport == "MLB": roster_df = fetch_mlb()
    else: roster_df = fetch_nhl()

st.write(f"Fetched {len(roster_df)} players for {sport}")

# CSV merge
if uploaded_file is not None:
    user_df = pd.read_csv(uploaded_file)
    if 'std_dev' not in user_df.columns: user_df['std_dev'] = 6.0
    merged = pd.merge(roster_df, user_df, on='player', how='left')
else:
    merged = roster_df.copy()
    merged['underdog_line'] = None
    merged['your_projection'] = None
    merged['std_dev'] = 6.0

merged[['edge_pct','win_prob_over','grade']] = merged.apply(calculate_metrics, axis=1)

# Display
st.subheader(f"{sport} – Merged Roster & Picks")
st.dataframe(merged.sort_values(by='edge_pct', ascending=False), use_container_width=True)

st.download_button(
    "Download CSV",
    merged.to_csv(index=False).encode('utf-8'),
    file_name=f"{sport}_underdog_picks.csv"
)

st.markdown("""
---
**Notes:**  
- Rosters come from legal public APIs.  
- Upload your projections CSV to merge with rosters.  
- `edge_pct`, `win_prob_over`, and `grade` highlight strongest picks.
""")
