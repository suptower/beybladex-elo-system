# tier_flow.py
"""
Tier Flow Diagram — Alluvial/Sankey Plot for Meta-Tier Evolution

This module creates an alluvial (Sankey-style) visualization showing how Beys
move between tiers over time. It helps reveal:

- Which Beys rise into higher tiers
- Which ones fall off
- Meta stability vs volatility
- Emergence of new meta threats
- Decline of formerly dominant picks

The diagram displays:
- Vertical columns = time slices (tournaments or match indices)
- Bands/flows = individual Beys
- Lanes = tier categories (S, A, B, C, D)
- Color coding by tier
"""

import json
import os
import sys

import numpy as np
import pandas as pd

# Add scripts directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

# --- File paths ---
ELO_TIMESERIES_FILE = "./csv/elo_timeseries.csv"
LEADERBOARD_FILE = "./csv/leaderboard.csv"
OUTPUT_DIR = "./docs/plots"

# Ensure output directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "dark"), exist_ok=True)

# --- Tier configuration ---
# ELO-based quantile tiers (configurable)
TIER_QUANTILES = {
    "S": 0.90,  # Top 10%
    "A": 0.70,  # Next 20% (70-90)
    "B": 0.40,  # Next 30% (40-70)
    "C": 0.15,  # Next 25% (15-40)
    "D": 0.00,  # Bottom 15%
}

# Tier colors (consistent across light/dark modes)
TIER_COLORS = {
    "S": "#FF6B6B",  # Red/coral - highest tier
    "A": "#4ECDC4",  # Teal - high tier
    "B": "#45B7D1",  # Blue - mid tier
    "C": "#96CEB4",  # Green - low tier
    "D": "#DDA0DD",  # Plum - lowest tier
}

# Tier order for display (top to bottom)
TIER_ORDER = ["S", "A", "B", "C", "D"]


# ============================================
# TIER ASSIGNMENT FUNCTIONS
# ============================================

def assign_tier_by_quantile(elo: float, elo_values: list) -> str:
    """
    Assign a tier based on ELO quantile position.

    Args:
        elo: The ELO value to classify
        elo_values: List of all ELO values in the snapshot

    Returns:
        Tier string (S, A, B, C, or D)
    """
    if not elo_values or len(elo_values) == 0:
        return "C"  # Default to middle tier if no data

    sorted_elos = sorted(elo_values)
    n = len(sorted_elos)

    # Calculate percentile of this ELO
    rank = sum(1 for e in sorted_elos if e <= elo)
    percentile = rank / n

    # Assign tier based on quantile thresholds
    if percentile >= TIER_QUANTILES["S"]:
        return "S"
    elif percentile >= TIER_QUANTILES["A"]:
        return "A"
    elif percentile >= TIER_QUANTILES["B"]:
        return "B"
    elif percentile >= TIER_QUANTILES["C"]:
        return "C"
    else:
        return "D"


def assign_tier_by_threshold(elo: float) -> str:
    """
    Assign a tier based on fixed ELO thresholds.

    This is an alternative tiering method that uses absolute ELO values.

    Args:
        elo: The ELO value to classify

    Returns:
        Tier string (S, A, B, C, or D)
    """
    if elo >= 1100:
        return "S"
    elif elo >= 1050:
        return "A"
    elif elo >= 1000:
        return "B"
    elif elo >= 950:
        return "C"
    else:
        return "D"


# ============================================
# DATA LOADING AND SNAPSHOT COMPUTATION
# ============================================

def load_elo_timeseries() -> pd.DataFrame:
    """
    Load ELO timeseries data.

    Returns:
        DataFrame with columns: Date, Bey, ELO, MatchIndex
    """
    try:
        df = pd.read_csv(ELO_TIMESERIES_FILE)
    except FileNotFoundError:
        print(f"Error: ELO timeseries file not found at {ELO_TIMESERIES_FILE}")
        return pd.DataFrame()
    except pd.errors.ParserError as e:
        print(f"Error: Could not parse CSV file {ELO_TIMESERIES_FILE}: {e}")
        return pd.DataFrame()

    # Ensure correct data types
    df["ELO"] = pd.to_numeric(df["ELO"], errors="coerce")
    df["MatchIndex"] = pd.to_numeric(df["MatchIndex"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Drop rows with NaN values in essential columns
    df = df.dropna(subset=["ELO", "MatchIndex", "Bey"])
    df["MatchIndex"] = df["MatchIndex"].astype(int)

    return df.sort_values(["Bey", "MatchIndex"]).reset_index(drop=True)


def compute_tier_snapshots(df: pd.DataFrame, num_slices: int = 5) -> list:
    """
    Compute tier snapshots at regular intervals across the match timeline.

    Args:
        df: DataFrame with ELO timeseries data
        num_slices: Number of time slices to create

    Returns:
        List of snapshot dictionaries containing tier assignments
    """
    if df.empty:
        return []

    # Get the range of match indices
    max_match_index = df["MatchIndex"].max()

    if max_match_index == 0:
        return []

    # Create slice points (evenly distributed)
    slice_points = np.linspace(0, max_match_index, num_slices + 1, dtype=int)
    # Remove the first point (0) and keep the rest as slice boundaries
    slice_points = slice_points[1:]

    snapshots = []

    for slice_idx, match_index in enumerate(slice_points):
        # Get the most recent ELO for each Bey up to this match index
        slice_df = df[df["MatchIndex"] <= match_index]

        if slice_df.empty:
            continue

        # Get the latest ELO for each Bey
        idx = slice_df.groupby("Bey")["MatchIndex"].idxmax()
        latest_elos = slice_df.loc[idx].reset_index(drop=True)

        if latest_elos.empty:
            continue

        # Get all ELO values for quantile calculation
        all_elos = latest_elos["ELO"].tolist()

        # Compute tier assignments
        snapshot_data = []
        for _, row in latest_elos.iterrows():
            tier = assign_tier_by_quantile(row["ELO"], all_elos)
            snapshot_data.append({
                "bey": row["Bey"],
                "elo": row["ELO"],
                "tier": tier,
                "match_index": match_index,
                "slice_index": slice_idx,
            })

        # Create snapshot label
        slice_label = f"Match {match_index}"

        snapshots.append({
            "slice_index": slice_idx,
            "match_index": match_index,
            "label": slice_label,
            "beys": snapshot_data,
            "elo_range": (min(all_elos), max(all_elos)),
        })

    return snapshots


def load_leaderboard_data() -> dict:
    """
    Load current leaderboard data for additional context.

    Returns:
        Dictionary mapping Bey names to their leaderboard stats
    """
    try:
        df = pd.read_csv(LEADERBOARD_FILE)
    except FileNotFoundError:
        return {}
    except pd.errors.ParserError:
        return {}

    leaderboard = {}
    for _, row in df.iterrows():
        bey_name = row.get("Name", "")
        if bey_name:
            winrate_str = str(row.get("Winrate", "50%")).rstrip("%")
            try:
                winrate = float(winrate_str)
            except ValueError:
                winrate = 50.0

            leaderboard[bey_name] = {
                "rank": row.get("Platz", 0),
                "elo": row.get("ELO", 1000),
                "matches": row.get("Spiele", 0),
                "winrate": winrate,
            }

    return leaderboard


# ============================================
# SANKEY DIAGRAM DATA PREPARATION
# ============================================

def build_sankey_data(snapshots: list, leaderboard: dict) -> dict:
    """
    Build Sankey diagram data from tier snapshots.

    Creates nodes for each (time_slice, tier, bey) combination and
    links connecting beys across time slices.

    Args:
        snapshots: List of tier snapshot dictionaries
        leaderboard: Dictionary of current leaderboard stats

    Returns:
        Dictionary with 'nodes' and 'links' for Sankey diagram
    """
    if not snapshots or len(snapshots) < 2:
        return {"nodes": [], "links": [], "labels": [], "colors": []}

    # Build node and link structures
    nodes = []
    node_labels = []
    node_colors = []
    node_map = {}  # (slice_idx, bey) -> node_index

    # Create nodes for each bey at each time slice
    for snapshot in snapshots:
        slice_idx = snapshot["slice_index"]
        for bey_data in snapshot["beys"]:
            bey = bey_data["bey"]
            tier = bey_data["tier"]

            node_key = (slice_idx, bey)
            if node_key not in node_map:
                node_idx = len(nodes)
                node_map[node_key] = node_idx

                # Get additional context from leaderboard
                lb_data = leaderboard.get(bey, {})
                winrate = lb_data.get("winrate", 50.0)
                matches = lb_data.get("matches", 0)

                nodes.append({
                    "bey": bey,
                    "tier": tier,
                    "elo": bey_data["elo"],
                    "slice_idx": slice_idx,
                    "slice_label": snapshot["label"],
                    "winrate": winrate,
                    "matches": matches,
                })
                node_labels.append(f"{bey}")
                node_colors.append(TIER_COLORS.get(tier, "#808080"))

    # Create links between consecutive time slices
    links = []
    link_sources = []
    link_targets = []
    link_values = []
    link_colors = []
    link_labels = []

    for i in range(len(snapshots) - 1):
        current_snapshot = snapshots[i]
        next_snapshot = snapshots[i + 1]

        current_slice_idx = current_snapshot["slice_index"]
        next_slice_idx = next_snapshot["slice_index"]

        # Build lookup for next snapshot
        next_beys = {b["bey"]: b for b in next_snapshot["beys"]}

        for bey_data in current_snapshot["beys"]:
            bey = bey_data["bey"]

            # Check if bey exists in next snapshot
            if bey in next_beys:
                source_key = (current_slice_idx, bey)
                target_key = (next_slice_idx, bey)

                if source_key in node_map and target_key in node_map:
                    source_idx = node_map[source_key]
                    target_idx = node_map[target_key]

                    current_tier = bey_data["tier"]
                    next_tier = next_beys[bey]["tier"]

                    # Determine flow direction
                    current_tier_rank = TIER_ORDER.index(current_tier)
                    next_tier_rank = TIER_ORDER.index(next_tier)

                    if next_tier_rank < current_tier_rank:
                        flow_type = "rising"
                    elif next_tier_rank > current_tier_rank:
                        flow_type = "falling"
                    else:
                        flow_type = "stable"

                    link_sources.append(source_idx)
                    link_targets.append(target_idx)
                    link_values.append(1)  # Each bey has equal weight
                    link_colors.append(TIER_COLORS.get(current_tier, "#808080") + "80")
                    link_labels.append(f"{bey}: {current_tier} → {next_tier} ({flow_type})")

                    links.append({
                        "source": source_idx,
                        "target": target_idx,
                        "bey": bey,
                        "from_tier": current_tier,
                        "to_tier": next_tier,
                        "flow_type": flow_type,
                    })

    return {
        "nodes": nodes,
        "labels": node_labels,
        "colors": node_colors,
        "link_sources": link_sources,
        "link_targets": link_targets,
        "link_values": link_values,
        "link_colors": link_colors,
        "link_labels": link_labels,
        "links": links,
        "snapshots": snapshots,
    }


# ============================================
# INTERACTIVE PLOTLY VISUALIZATION
# ============================================

def create_tier_flow_interactive(sankey_data: dict, output_file: str):
    """
    Create an interactive Tier Flow Sankey diagram with theme toggle.

    Args:
        sankey_data: Dictionary with Sankey diagram data
        output_file: Path to save the HTML file
    """
    if not sankey_data["nodes"] or not sankey_data["link_sources"]:
        print("Warning: No data available for Tier Flow diagram")
        return

    nodes = sankey_data["nodes"]
    snapshots = sankey_data["snapshots"]

    # Prepare hover text for nodes
    node_hover = []
    for node in nodes:
        hover = (
            f"<b>{node['bey']}</b><br>"
            f"Tier: {node['tier']}<br>"
            f"ELO: {node['elo']:.0f}<br>"
            f"Winrate: {node['winrate']:.1f}%<br>"
            f"Matches: {node['matches']}<br>"
            f"<br>"
            f"<i>{node['slice_label']}</i>"
        )
        node_hover.append(hover)

    # Prepare data for JavaScript
    labels = json.dumps(sankey_data["labels"])
    colors = json.dumps(sankey_data["colors"])
    link_sources = json.dumps(sankey_data["link_sources"])
    link_targets = json.dumps(sankey_data["link_targets"])
    link_values = json.dumps(sankey_data["link_values"])
    link_colors = json.dumps(sankey_data["link_colors"])
    link_labels = json.dumps(sankey_data["link_labels"])
    node_hover_json = json.dumps(node_hover)

    # Create snapshot labels for x-axis
    snapshot_labels = [s["label"] for s in snapshots]
    snapshot_labels_json = json.dumps(snapshot_labels)

    # Calculate node x positions based on slice index
    num_slices = len(snapshots)
    node_x = []
    for node in nodes:
        x_pos = node["slice_idx"] / (num_slices - 1) if num_slices > 1 else 0.5
        node_x.append(x_pos)
    node_x_json = json.dumps(node_x)

    # Calculate node y positions based on tier
    node_y = []
    for node in nodes:
        tier_idx = TIER_ORDER.index(node["tier"])
        # Distribute within tier band
        y_pos = (tier_idx + 0.5) / len(TIER_ORDER)
        node_y.append(y_pos)
    node_y_json = json.dumps(node_y)

    # Tier info for legend
    tier_info = json.dumps({
        tier: {"color": TIER_COLORS[tier], "quantile": f"{int(TIER_QUANTILES[tier] * 100)}%+"}
        for tier in TIER_ORDER
    })

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tier Flow Diagram - Beyblade X</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            transition: background-color 0.3s, color 0.3s;
        }}
        body.light {{
            background-color: #f8f9fa;
            color: #1a1a1a;
        }}
        body.dark {{
            background-color: #0f172a;
            color: #f1f5f9;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding: 10px;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 1.5em;
        }}
        .controls {{
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
        }}
        .theme-toggle {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .theme-toggle label {{
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 20px;
            transition: background-color 0.3s;
        }}
        body.light .theme-toggle label {{
            background-color: #e5e7eb;
        }}
        body.dark .theme-toggle label {{
            background-color: #334155;
        }}
        .theme-toggle input {{
            display: none;
        }}
        .theme-icon {{
            font-size: 1.2em;
        }}
        .back-link {{
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 8px;
            transition: background-color 0.3s;
        }}
        body.light .back-link {{
            color: #1a1a1a;
            background-color: #e5e7eb;
        }}
        body.dark .back-link {{
            color: #f1f5f9;
            background-color: #334155;
        }}
        .back-link:hover {{
            opacity: 0.8;
        }}
        #plotDiv {{
            width: 100%;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .info-section {{
            max-width: 1200px;
            margin: 20px auto;
            padding: 20px;
            border-radius: 12px;
            transition: background-color 0.3s;
        }}
        body.light .info-section {{
            background-color: #ffffff;
            border: 1px solid #e5e7eb;
        }}
        body.dark .info-section {{
            background-color: #1e293b;
            border: 1px solid #334155;
        }}
        .info-section h2 {{
            margin-top: 0;
            font-size: 1.2em;
        }}
        .tier-legend {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin-top: 15px;
        }}
        .tier-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .tier-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}
        .tier-label {{
            font-weight: 600;
        }}
        .tier-desc {{
            font-size: 0.85em;
            opacity: 0.7;
        }}
        ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        li {{
            margin: 5px 0;
        }}
        /* Mobile responsive styles */
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}
            .header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }}
            .header h1 {{
                font-size: 1.2em;
                order: -1;
                width: 100%;
                text-align: center;
            }}
            .back-link {{
                padding: 6px 12px;
                font-size: 0.9em;
            }}
            .controls {{
                width: 100%;
                justify-content: center;
            }}
            .theme-toggle label {{
                padding: 6px 12px;
                font-size: 0.9em;
            }}
            #plotDiv {{
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
            }}
            .info-section {{
                padding: 15px;
                margin: 10px auto;
            }}
            .info-section h2 {{
                font-size: 1.1em;
            }}
            .info-section h3 {{
                font-size: 1em;
            }}
            .tier-legend {{
                gap: 10px;
            }}
            .tier-item {{
                flex: 1 1 calc(50% - 10px);
                min-width: 140px;
            }}
            .tier-desc {{
                font-size: 0.75em;
            }}
        }}
        @media (max-width: 480px) {{
            .header h1 {{
                font-size: 1em;
            }}
            .tier-item {{
                flex: 1 1 100%;
            }}
            .info-section {{
                padding: 10px;
            }}
            ul {{
                padding-left: 15px;
            }}
        }}
    </style>
</head>
<body class="light">
    <div class="header">
        <a href="../plots.html" class="back-link">← Back to Plots</a>
        <h1>📊 Tier Flow Diagram</h1>
        <div class="controls">
            <div class="theme-toggle">
                <label>
                    <input type="checkbox" id="themeToggle">
                    <span class="theme-icon" id="themeIcon">🌙</span>
                    <span id="themeLabel">Dark Mode</span>
                </label>
            </div>
        </div>
    </div>
    
    <div id="plotDiv"></div>
    
    <div class="info-section">
        <h2>📖 How to Read This Diagram</h2>
        <p>
            The <strong>Tier Flow Diagram</strong> shows how Beys move between competitive tiers over time.
            Each vertical column represents a time slice (based on match count), and the flowing bands
            connect each Bey's tier position across time.
        </p>
        
        <h3>Tier Definitions (ELO Quantiles)</h3>
        <div class="tier-legend" id="tierLegend"></div>
        
        <h3>Reading the Flows</h3>
        <ul>
            <li><strong>Rising flows (upward)</strong> — Bey moved to a higher tier</li>
            <li><strong>Falling flows (downward)</strong> — Bey dropped to a lower tier</li>
            <li><strong>Horizontal flows</strong> — Bey maintained their tier</li>
            <li><strong>Appearing/disappearing bands</strong> — New entries or exits from the meta</li>
        </ul>
        
        <h3>Insights</h3>
        <ul>
            <li>Consistent S-tier presence indicates meta dominance</li>
            <li>Rapid tier changes suggest volatile or shifting meta</li>
            <li>Clustered flows reveal stable tier hierarchies</li>
            <li>Dispersed flows indicate competitive diversity</li>
        </ul>
    </div>
    
    <script>
        // Data from Python
        const labels = {labels};
        const nodeColors = {colors};
        const linkSources = {link_sources};
        const linkTargets = {link_targets};
        const linkValues = {link_values};
        const linkColors = {link_colors};
        const linkLabels = {link_labels};
        const nodeHover = {node_hover_json};
        const nodeX = {node_x_json};
        const nodeY = {node_y_json};
        const snapshotLabels = {snapshot_labels_json};
        const tierInfo = {tier_info};
        
        // Populate tier legend
        const tierOrder = ['S', 'A', 'B', 'C', 'D'];
        const tierDescriptions = {{
            'S': 'Top 10% ELO',
            'A': 'Next 20% ELO',
            'B': 'Next 30% ELO',
            'C': 'Next 25% ELO',
            'D': 'Bottom 15% ELO'
        }};
        
        const legendContainer = document.getElementById('tierLegend');
        tierOrder.forEach(tier => {{
            const item = document.createElement('div');
            item.className = 'tier-item';
            item.innerHTML = `
                <div class="tier-color" style="background-color: ${{tierInfo[tier].color}}"></div>
                <span class="tier-label">Tier ${{tier}}</span>
                <span class="tier-desc">(${{tierDescriptions[tier]}})</span>
            `;
            legendContainer.appendChild(item);
        }});
        
        // Layout configurations
        function getLayout(isDark) {{
            return {{
                title: {{
                    text: 'Meta-Tier Evolution Over Time',
                    font: {{ 
                        size: 18, 
                        color: isDark ? '#f1f5f9' : '#1a1a1a'
                    }}
                }},
                font: {{
                    color: isDark ? '#f1f5f9' : '#1a1a1a'
                }},
                paper_bgcolor: isDark ? '#0f172a' : '#f8f9fa',
                plot_bgcolor: isDark ? '#1e293b' : '#ffffff',
                width: 1100,
                height: 800,
                margin: {{ l: 50, r: 50, t: 80, b: 80 }}
            }};
        }}
        
        // Create Sankey trace
        function createTrace() {{
            return {{
                type: 'sankey',
                orientation: 'h',
                arrangement: 'snap',
                node: {{
                    pad: 15,
                    thickness: 20,
                    line: {{
                        color: 'rgba(128,128,128,0.5)',
                        width: 0.5
                    }},
                    label: labels,
                    color: nodeColors,
                    customdata: nodeHover,
                    hovertemplate: '%{{customdata}}<extra></extra>',
                    x: nodeX,
                    y: nodeY
                }},
                link: {{
                    source: linkSources,
                    target: linkTargets,
                    value: linkValues,
                    color: linkColors,
                    customdata: linkLabels,
                    hovertemplate: '%{{customdata}}<extra></extra>'
                }}
            }};
        }}
        
        const config = {{
            displayModeBar: true,
            modeBarButtonsToAdd: ['pan2d', 'zoomIn2d', 'zoomOut2d', 'resetScale2d'],
            responsive: true
        }};
        
        // Theme handling
        let isDarkMode = localStorage.getItem('theme') === 'dark';
        const toggle = document.getElementById('themeToggle');
        const themeIcon = document.getElementById('themeIcon');
        const themeLabel = document.getElementById('themeLabel');
        
        function updateTheme(isDark) {{
            document.body.className = isDark ? 'dark' : 'light';
            themeIcon.textContent = isDark ? '☀️' : '🌙';
            themeLabel.textContent = isDark ? 'Light Mode' : 'Dark Mode';
            toggle.checked = isDark;
            
            const layout = getLayout(isDark);
            const trace = createTrace();
            
            Plotly.react('plotDiv', [trace], layout, config);
        }}
        
        // Initialize
        updateTheme(isDarkMode);
        
        // Handle toggle
        toggle.addEventListener('change', function() {{
            isDarkMode = this.checked;
            localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
            updateTheme(isDarkMode);
        }});
        
        // Listen for theme changes from other pages
        window.addEventListener('storage', function(e) {{
            if (e.key === 'theme') {{
                isDarkMode = e.newValue === 'dark';
                updateTheme(isDarkMode);
            }}
        }});
    </script>
</body>
</html>'''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Tier Flow Diagram (interactive) saved to: {output_file}")


# ============================================
# MAIN GENERATION FUNCTION
# ============================================

def generate_tier_flow_plots(num_slices: int = 5):
    """
    Generate all Tier Flow plots.

    Args:
        num_slices: Number of time slices to display
    """
    print("Generating Tier Flow Diagram...")

    # Load data
    df = load_elo_timeseries()
    if df.empty:
        print("Warning: No ELO timeseries data available")
        return

    leaderboard = load_leaderboard_data()

    # Compute tier snapshots
    snapshots = compute_tier_snapshots(df, num_slices=num_slices)
    if len(snapshots) < 2:
        print("Warning: Not enough data points for Tier Flow diagram")
        return

    # Build Sankey data
    sankey_data = build_sankey_data(snapshots, leaderboard)

    # Generate interactive plot
    create_tier_flow_interactive(
        sankey_data,
        os.path.join(OUTPUT_DIR, "tier_flow_interactive.html")
    )

    print("Tier Flow Diagram generated successfully!")


# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    generate_tier_flow_plots()
