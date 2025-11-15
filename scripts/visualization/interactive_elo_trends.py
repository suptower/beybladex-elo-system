# interactive_elo_trends.py
import pandas as pd
import plotly.graph_objects as go
import os
import glob

# --- Ordner für Diagramme ---
OUTPUT_DIR = "./plots/official"
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "elo_trends_interactive.html")

# --- CSVs einlesen ---
df_ts = pd.read_csv("./csv/elo_timeseries.csv")      # Date,Bey,ELO,match_id,MatchIndex
df_hist = pd.read_csv("./csv/elo_history.csv")       # Date,BeyA,BeyB,ScoreA,ScoreB,PreA,PreB,PostA,PostB
df_adv = pd.read_csv("./csv/advanced_leaderboard.csv")  # ELO, Volatility etc.

# --- Gegner-Spalte automatisch füllen ---
def fill_opponent(df_ts, df_hist):
    opponents = []
    for idx, row in df_ts.iterrows():
        date = row['Date']
        bey = row['Bey']
        elo = row['ELO']

        hist_day = df_hist[(df_hist['Date']==date) & ((df_hist['BeyA']==bey) | (df_hist['BeyB']==bey))]
        if len(hist_day) == 1:
            r = hist_day.iloc[0]
        else:
            r = None
            for _, m in hist_day.iterrows():
                post_elo = m['PostA'] if m['BeyA']==bey else m['PostB']
                if abs(post_elo - elo) < 0.01:
                    r = m
                    break
            if r is None:
                r = hist_day.iloc[0]

        opponent = r['BeyB'] if r['BeyA']==bey else r['BeyA']
        opponents.append(opponent)
    df_ts['Opponent'] = opponents
    return df_ts

df_ts = fill_opponent(df_ts, df_hist)

# --- Turnierbasierte Deltas einfügen ---
delta_files = sorted(glob.glob("./csv/leaderboards/leaderboard_*.csv"))
df_ts['Positionsdelta'] = 0
df_ts['ELODelta'] = 0

for f in delta_files:
    df_t = pd.read_csv(f)
    for _, r in df_t.iterrows():
        bey = r['Name']
        # MatchIndex abschätzen über Anzahl gespielter Matches bis Turnier
        mask = df_ts['Bey']==bey
        df_ts.loc[mask, 'Positionsdelta'] = r.get('Positionsdelta', 0)
        df_ts.loc[mask, 'ELODelta'] = r.get('ELODelta', 0)

# --- Top 5 nach ELO ---
top5_beys = df_adv.sort_values(by='ELO', ascending=False).head(5)['Bey'].tolist()

# --- Farbcode nach Volatilität ---
def color_volatility(vol):
    if vol < 5:
        return 'green'
    elif vol < 10:
        return 'orange'
    else:
        return 'red'

bey_colors = {row['Bey']: color_volatility(row['Volatility']) for _, row in df_adv.iterrows()}

# --- Plotly-Figur erstellen ---
fig = go.Figure()

for bey in df_ts['Bey'].unique():
    df_b = df_ts[df_ts['Bey']==bey].sort_values(by='MatchIndex')
    line_width = 3 if bey in top5_beys else 1.2
    opacity = 0.9 if bey in top5_beys else 0.5
    color = bey_colors.get(bey, 'gray')

    hover_text = [
        f"Bey: {bey}<br>"
        f"MatchIndex: {int(row['MatchIndex'])}<br>"
        f"Date: {row['Date']}<br>"
        f"ELO: {round(row['ELO'],2)}<br>"
        f"Score: {row.get('ScoreA','')} - {row.get('ScoreB','')}<br>"
        f"Opponent: {row['Opponent']}<br>"
        f"ELO Δ: {row.get('ELODelta','0')}<br>"
        f"Positions Δ: {row.get('Positionsdelta','0')}"
        for _, row in df_b.iterrows()
    ]

    # Score über Marker anzeigen
    scores = [
        f"{row.get('ScoreA','')}-{row.get('ScoreB','')}"
        for _, row in df_b.iterrows()
    ]

    fig.add_trace(go.Scatter(
        x=df_b['MatchIndex'],
        y=df_b['ELO'],
        mode='lines+markers+text',
        name=bey,
        line=dict(color=color, width=line_width),
        opacity=opacity,
        text=scores,
        textposition="top center",
        textfont=dict(size=10, color='black'),
        hovertext=hover_text,
        hoverinfo='text'
    ))

fig.update_layout(
    title="Beyblade X - Interaktive ELO Verläufe mit Gegnerinfo",
    xaxis_title="Match Index",
    yaxis_title="ELO",
    legend_title="Bey",
    template="plotly_white",
    hovermode="closest",
    width=1400,
    height=800
)

# --- HTML speichern ---
fig.write_html(OUTPUT_FILE)
print(f"Interaktive ELO-Trends mit Gegnerinfo erstellt: {OUTPUT_FILE}")
