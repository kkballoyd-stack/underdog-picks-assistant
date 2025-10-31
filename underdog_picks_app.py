import streamlit as st
import pandas as pd
import math
import os

# --- Helper functions ---
def normal_cdf(x, mean=0, std=1):
    """Cumulative distribution function for a normal distribution."""
    return 0.5 * (1 + math.erf((x - mean) / (std * (2 ** 0.5))))

def grade_edge(p):
    """Assign letter grade based on win probability."""
    pct = p * 100
    if pct >= 70:
        return "A+"
    if pct >= 65:
        return "A"
    if pct >= 60:
        return "B"
    if pct >= 55:
        return "C"
    if pct >= 50:
        return "D"
    return "F"

# --- App Title ---
st.set_page_config(page_title="Underdog Edge Assistant", page_icon="🏈", layout="wide")
st.title("🏈 Underdog Edge Assistant — All Sports Version")
st.markdown("""
Select a sport, filter players, and see the biggest **edges** in pick’em games!
""")

# --- Sport selection ---
sport = st.selectbox("Select Sport", ["NBA", "NFL", "MLB", "NHL"])

# --- CSV filename mapping ---
csv_files = {
    "NBA": "NBA.csv",
    "NFL": "NFL.csv",
    "MLB": "MLB.csv",
    "NHL": "NHL.csv"
}

# --- Load CSV ---
if os.path.exists(csv_files[sport]):
    df = pd.read_csv(csv_files[sport])
else:
    st.warning(f"No CSV file found for {sport}. Using sample data.")
    df = pd.DataFrame([
        {"player": "Sample Player 1", "underdog_line": 20, "your_projection": 22, "std_dev": 5, "team": "Team A", "position": "Pos 1"},
        {"player": "Sample Player 2", "underdog_line": 18, "your_projection": 17, "std_dev": 6, "team": "Team B", "position": "Pos 2"},
    ])

# --- Default std_dev ---
if "std_dev" not in df.columns:
    df["std_dev"] = 6.0

# --- Filters ---
teams = ["All"] + sorted(df["team"].dropna().unique().tolist())
positions = ["All"] + sorted(df["position"].dropna().unique().tolist())

selected_team = st.selectbox("Filter by Team", teams)
selected_position = st.selectbox("Filter by Position", positions)

filtered_df = df.copy()
if selected_team != "All":
    filtered_df = filtered_df[filtered_df["team"] == selected_team]
if selected_position != "All":
    filtered_df = filtered_df[filtered_df["position"] == selected_position]

# --- Calculations ---
filtered_df["edge_pct"] = ((filtered_df["your_projection"] - filtered_df["underdog_line"]) / filtered_df["underdog_line"]) * 100
filtered_df["win_prob_over"] = filtered_df.apply(
    lambda r: 1 - normal_cdf(r["underdog_line"], mean=r["your_projection"], std=r["std_dev"]),
    axis=1
)
filtered_df["win_pct_over"] = (filtered_df["win_prob_over"] * 100).round(1)
filtered_df["grade"] = filtered_df["win_prob_over"].apply(grade_edge)

# --- Display Results ---
st.subheader(f"📊 {sport} Pick'em Insights")
st.dataframe(
    filtered_df[["player", "team", "position", "underdog_line", "your_projection", "std_dev", "edge_pct", "win_pct_over", "grade"]]
    .sort_values(by="edge_pct", ascending=False),
    use_container_width=True
)

# --- Download CSV ---
st.markdown("### 💾 Export Results")
st.download_button(
    "Download Filtered CSV",
    filtered_df.to_csv(index=False).encode("utf-8"),
    file_name=f"{sport}_underdog_picks_with_calcs.csv"
)

# --- Notes ---
st.markdown("---")
st.markdown("""
**How it works:**  
- **Edge %** shows how far your projection is from the Underdog line.  
- **Win Probability** uses a normal distribution around your projection (`std_dev` reflects volatility).  
- **Grades** are based on probability tiers for easier decision-making.  
- Use the filters to narrow down by **team** or **position**.
""")
