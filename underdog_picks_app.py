import streamlit as st
import pandas as pd
import math

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
st.title("🏈 Underdog Picks Assistant — Prototype")
st.markdown("""
Quickly find the biggest **edges** on Underdog pick’em games!  
Upload your projection data or use the sample below to see **HIGHER / LOWER** insights, win %s, and grades.
""")

# --- File Upload ---
uploaded = st.file_uploader(
    "📂 Upload CSV with columns: player, underdog_line, your_projection, std_dev (optional)",
    type=["csv"]
)

if uploaded is not None:
    df = pd.read_csv(uploaded)
else:
    st.info("No file uploaded — using sample player data.")
    df = pd.DataFrame([
        {"player": "LeBron James", "underdog_line": 28.5, "your_projection": 31.2, "std_dev": 6.0},
        {"player": "Stephen Curry", "underdog_line": 24.5, "your_projection": 23.1, "std_dev": 5.0},
        {"player": "Nikola Jokic", "underdog_line": 21.0, "your_projection": 22.8, "std_dev": 5.5},
        {"player": "Jayson Tatum", "underdog_line": 26.5, "your_projection": 25.0, "std_dev": 6.2},
    ])

# --- Default values if missing ---
if "std_dev" not in df.columns:
    df["std_dev"] = 6.0

# --- Calculations ---
df["edge_pct"] = ((df["your_projection"] - df["underdog_line"]) / df["underdog_line"]) * 100
df["win_prob_over"] = df.apply(
    lambda r: 1 - normal_cdf(r["underdog_line"], mean=r["your_projection"], std=r["std_dev"]),
    axis=1
)
df["win_pct_over"] = (df["win_prob_over"] * 100).round(1)
df["grade"] = df["win_prob_over"].apply(grade_edge)

# --- Display Results ---
st.subheader("📊 Pick'em Insights")
st.dataframe(
    df[["player", "underdog_line", "your_projection", "std_dev", "edge_pct", "win_pct_over", "grade"]]
    .sort_values(by="edge_pct", ascending=False),
    use_container_width=True
)

# --- Download Results ---
st.markdown("### 💾 Export Results")
st.download_button(
    "Download CSV with calculations",
    df.to_csv(index=False).encode("utf-8"),
    file_name="underdog_picks_with_calcs.csv"
)

# --- Notes ---
st.markdown("---")
st.markdown("""
**How it works:**  
- **Edge %** shows how far your projection is from the Underdog line.  
- **Win Probability** uses a normal distribution around your projection (smaller std_dev = more confidence).  
- **Grades** are based on probability tiers for easier decision-making.  
""")
