# rosters.py
import requests
import pandas as pd
import time
import statsapi

def fetch_nba():
    all_players = []
    page = 1
    while True:
        url = f"https://www.balldontlie.io/api/v1/players?page={page}&per_page=100"
        resp = requests.get(url).json()
        data = resp.get('data', [])
        if not data:
            break
        for p in data:
            all_players.append({
                "player": f"{p['first_name']} {p['last_name']}",
                "team": p.get('team', {}).get('full_name'),
                "position": p.get('position')
            })
        page += 1
        time.sleep(0.2)
    return pd.DataFrame(all_players)

def fetch_nfl():
    all_players = []
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
                all_players.append({"player": name, "team": team, "position": pos})
        page += 1
        time.sleep(0.2)
    return pd.DataFrame(all_players)

def fetch_mlb():
    all_players = []
    teams = statsapi.get('teams', {'sportIds':1})
    for team in teams:
        team_id = team['id']
        team_name = team['name']
        roster = statsapi.get('team_roster', {'teamId': team_id})
        for p in roster.get('roster', []):
            all_players.append({
                "player": p['person']['fullName'],
                "team": team_name,
                "position": p['position']['abbreviation']
            })
        time.sleep(0.1)
    return pd.DataFrame(all_players)

def fetch_nhl():
    all_players = []
    teams_resp = requests.get("https://statsapi.web.nhl.com/api/v1/teams").json().get('teams', [])
    for t in teams_resp:
        team_id = t['id']
        team_name = t['name']
        roster = requests.get(f"https://statsapi.web.nhl.com/api/v1/teams/{team_id}/roster").json().get('roster', [])
        for p in roster:
            all_players.append({"player": p['person']['fullName'], "team": team_name, "position": p['position']['code']})
        time.sleep(0.1)
    return pd.DataFrame(all_players)
