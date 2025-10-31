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
    if pct >= 70: return "A+ 🏆"
    if pct >= 65: return "A ⚡"
    if pct >= 60: return "B"
    if pct >= 55: return "C"
    if pct >= 50: return "D"
    return "F ❌"

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
# Fetch NBA Active Players & Stats (Fixed)
# --------------------
@st.cache_data(show_spinner=False)
def fetch_nba(season=2025):
    players, page = [], 1
    while True:
        try:
            resp = requests.get(f"https://www.balldontlie.io/api/v1/players?page={page}&per_page=100")
            if resp.status_code != 200:
                st.warning(f"NBA API request failed with status {resp.status_code}")
                break
            try:
                data = resp.json().get('data', [])
            except ValueError:
                st.warning("Received invalid JSON from NBA API")
                break
            if not data:
                break
            for p in data:
                if not p['team'] or not p['first_name'] or not p['last_name']:
                    continue
                players.append({
                    "id": p['id'],
                    "player": f"{p['first_name']} {p['last_name']}".strip(),
                    "team": p.get('team', {}).get('full_name'),
                    "position": p.get('position')
                })
            page += 1
            time.sleep(0.05)
        except Exception as e:
            st.warning(f"Error fetching NBA players: {e}")
            break

    roster_df = pd.DataFrame(players)
    if roster_df.empty:
        st.warning("No NBA players fetched.")
        return pd.DataFrame(columns=["player", "team", "position", "projection"])

    stats_list = []
    for p in roster_df.itertuples():
        try:
            resp = requests.get(f"https://www.balldontlie.io/api/v1/season_averages?season={season}&player_ids[]={p.id}")
            if resp.status_code != 200:
                projection = 10
            else:
                try:
                    data = resp.json().get('data', [])
                    projection = data[0]['pts'] if data else 10
                except ValueError:
                    projection = 10
            stats_list.append({"player": p.player, "projection": projection})
            time.sleep(0.05)
        except:
            stats_list.append({"player": p.player, "projection": 10})

    stats_df = pd.DataFrame(stats_list)
    roster_df['player'] = roster_df['player'].astype(str).str.strip()
    stats_df['player'] = stats_df['player'].astype(str).str.strip()
    merged = pd.merge(roster_df, stats_df, on='player', how='left')
    merged['projection'] = merged.get('projection', 10).fillna(10)
    return merged

# --------------------
# Fetch NFL Active Players
# --------------------
@st.cache_data(show_spinner=False)
def fetch_nfl():
    players, page = [], 1
    while True:
        try:
            resp = requests.get(f"https://sports.core.api.espn.com/v3/sports/football/nfl/athletes?page={page}&limit=500")
            resp.raise_for_status()
            try:
                data = resp.json().get('items', [])
            except ValueError:
                st.warning("Received invalid JSON from NFL API")
                break
            if not data: break
            for p in data:
                name = p.get('fullName')
                if not name: continue
                team = p.get('team', {}).get('displayName') if p.get('team') else None
                pos = p.get('position', {}).get('abbreviation') if p.get('position') else None
                players.append({"player": name.strip(), "team": team, "position": pos, "projection": 10})
            page += 1
            time.sleep(0.05)
        except:
            break
    df = pd.DataFrame(players)
    if not df.empty:
        df['player'] = df['player'].astype(str).str.strip()
        if 'projection' not in df.columns:
            df['projection'] = 10
    return df

# --------------------
# Streamlit Fun Layout
# --------------------
st.set_page_config(page_title="Underdog Picks", layout="wide")
st.title("🎯 Underdog Picks Assistant")
st.markdown("Pick the strongest edges in NBA & NFL with style ⚡🏆")

sport_tab = st.tabs(["NBA", "NFL"])

with sport_tab[0]:
    with st.spinner("Fetching NBA players and stats..."):
        nba_df = fetch_nba()
    nba_df['line'] = nba_df['projection'] * 0.95
    nba_df['std_dev'] = 5
    nba_df[['edge_pct', 'win_prob_over', 'grade']] = nba_df.apply(calculate_metrics, axis=1)
    pos_filter = st.multiselect("Filter by position:", options=nba_df['position'].dropna().unique(), default=nba_df['position'].dropna().unique())
    filtered_nba = nba_df[nba_df['position'].isin(pos_filter)]
    st.subheader("NBA – Active Players & Projections")
    st.dataframe(filtered_nba.style.background_gradient(subset=['edge_pct'], cmap='coolwarm').format({"projection": "{:.1f}", "edge_pct": "{:.1f}%", "win_prob_over": "{:.1%}"}))
    st.download_button("Download NBA CSV", filtered_nba.to_csv(index=False).encode('utf-8'), file_name="NBA_Underdog_Picks.csv")

with sport_tab[1]:
    with st.spinner("Fetching NFL players..."):
        nfl_df = fetch_nfl()
    nfl_df['line'] = nfl_df['projection'] * 0.95
    nfl_df['std_dev'] = 5
    nfl_df[['edge_pct', 'win_prob_over', 'grade']] = nfl_df.apply(calculate_metrics, axis=1)
    pos_filter = st.multiselect("Filter by position:", options=nfl_df['position'].dropna().unique(), default=nfl_df['position'].dropna().unique())
    filtered_nfl = nfl_df[nfl_df['position'].isin(pos_filter)]
    st.subheader("NFL – Active Players & Projections")
    st.dataframe(filtered_nfl.style.background_gradient(subset=['edge_pct'], cmap='coolwarm').format({"projection": "{:.1f}", "edge_pct": "{:.1f}%", "win_prob_over": "{:.1%}"}))
    st.download_button("Download NFL CSV", filtered_nfl.to_csv(index=False).encode('utf-8'), file_name="NFL_Underdog_Picks.csv")
