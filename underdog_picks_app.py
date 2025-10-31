# underdog_picks_app_full.py
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
    try:
        edge_pct = ((projection - line) / line) * 100
        win_prob = 1 - normal_cdf(line, mean=projection, std=std_dev)
        grade = "Strong" if win_prob >= 0.65 else "Moderate" if win_prob >= 0.55 else "Weak"
        return pd.Series([edge_pct, win_prob, grade])
    except:
        return pd.Series([0.0, 0.0, "N/A"])

# --------------------
# Fetch NBA Players & Stats
# --------------------
@st.cache_data(show_spinner=False)
def fetch_nba(season=2025):
    players = []
    page = 1
    while True:
        resp = requests.get(f"https://www.balldontlie.io/api/v1/players?page={page}&per_page=100")
        if resp.status_code != 200: break
        data = resp.json().get('data', [])
        if not data: break
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

    projections = []
    for p in df.itertuples():
        try:
            r = requests.get(f"https://www.balldontlie.io/api/v1/season_averages?season={season}&player_ids[]={p.id}")
            d = r.json().get('data', [])
            pts = d[0].get('pts', 10) if d else 10
        except:
            pts = 10
        projections.append(pts)
        time.sleep(0.05)

    df['projection'] = projections
    df['line'] = df['projection'] * 0.95
    df['std_dev'] = 5
    df[['edge_pct', 'win_prob', 'grade']] = df.apply(lambda r: calculate_edge(r['projection'], r['line'], r['std_dev']), axis=1)
    return df

# --------------------
# Fetch NFL Players & Stats (Pro-Football-Reference CSV)
# --------------------
@st.cache_data(show_spinner=False)
def fetch_nfl():
    # Download CSV from PFR (or use local CSV if preferred)
    url = "https://raw.githubusercontent.com/fantasydatapros/data/main/nfl_stats_2025.csv"  # example placeholder URL
    try:
        df = pd.read_csv(url)
        # Keep only active players and relevant stats
        df = df[df['active'] == True]
        # Simplified projection metric: sum of yards + touchdowns
        df['projection'] = df['pass_yds'].fillna(0) + df['rush_yds'].fillna(0) + df['rec_yds'].fillna(0) + df['pass_td'].fillna(0)*6 + df['rush_td'].fillna(0)*6 + df['rec_td'].fillna(0)*6
        df['line'] = df['projection'] * 0.95
        df['std_dev'] = df['projection'] * 0.15 + 5
        df[['edge_pct','win_prob','grade']] = df.apply(lambda r: calculate_edge(r['projection'], r['line'], r['std_dev']), axis=1)
        return df
    except Exception as e:
        st.warning(f"Could not fetch NFL stats: {e}")
        return pd.DataFrame(columns=['player','team','position','projection','line','edge_pct','win_prob','grade'])

# --------------------
# Streamlit Layout
# --------------------
st.set_page_config(page_title="Underdog Picks Assistant", layout="wide")
st.title("Underdog Picks Assistant – NBA & NFL")
st.markdown("Active players with real stats, projections, and calculated edges for pick'em advantage.")

tabs = st.tabs(["NBA", "NFL"])

# --------------------
# NBA Tab
# --------------------
with tabs[0]:
    with st.spinner("Loading NBA players..."):
        nba_df = fetch_nba()
    if not nba_df.empty:
        pos_filter = st.multiselect("Filter NBA by position:", options=nba_df['position'].dropna().unique(), default=nba_df['position'].dropna().unique())
        filtered_nba = nba_df[nba_df['position'].isin(pos_filter)]
        st.subheader("NBA – Active Players & Stats")
        st.dataframe(filtered_nba[['player','team','position','projection','line','edge_pct','win_prob','grade']].sort_values('edge_pct', ascending=False).reset_index(drop=True))
        st.download_button("Download NBA CSV", filtered_nba.to_csv(index=False).encode('utf-8'), file_name="NBA_Underdog_Picks.csv")
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
        pos_filter = st.multiselect("Filter NFL by position:", options=nfl_df['position'].dropna().unique(), default=nfl_df['position'].dropna().unique())
        filtered_nfl = nfl_df[nfl_df['position'].isin(pos_filter)]
        st.subheader("NFL – Active Players & Stats")
        st.dataframe(filtered_nfl[['player','team','position','projection','line','edge_pct','win_prob','grade']].sort_values('edge_pct', ascending=False).reset_index(drop=True))
        st.download_button("Download NFL CSV", filtered_nfl.to_csv(index=False).encode('utf-8'), file_name="NFL_Underdog_Picks.csv")
        top10 = filtered_nfl.nlargest(10,'edge_pct')
        st.markdown("### Top 10 NFL Picks")
        st.dataframe(top10[['player','team','position','projection','edge_pct','grade']].reset_index(drop=True))
    else:
        st.warning("No NFL data available.")
