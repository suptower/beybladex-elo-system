# update.py
"""
Beyblade X Unified Update Pipeline

This script serves as the single entry point to regenerate all dependent data
in the Beyblade X ELO System. It orchestrates the execution of all processing
scripts in the correct dependency order.

Pipeline Stages:
1. Core Data Generation
   - ELO calculations (beyblade_elo.py)
   - Advanced statistics (advanced_stats.py)

2. Analysis Modules
   - RPG Stats & Archetypes (rpg_stats.py)
   - Upset Analysis (upset_analysis.py)
   - Meta Balance (meta_balance.py)
   - Synergy Heatmaps (synergy_heatmaps.py)
   - Bey Counters (counter_checker.py)
   - Combo Explorer (combo_explorer.py)

3. Visualization (runs by default, use --skip-plots to skip)
   - Plot Generation (gen_plots.py)
   - Position Plots (plot_positions.py)

4. Export (optional, requires explicit flags)
   - PDF Leaderboard (export_leaderboard_pdf.py)
   - Google Sheets Upload (sheets_upload.py)

Usage:
    python update.py                    # Run full pipeline including plots
    python update.py --skip-plots       # Skip plot generation (faster)
    python update.py --stats-only       # Only run stats calculations
    python update.py --plots-only       # Only run plot generation
    python update.py --upload           # Include Google Sheets upload
    python update.py --pdf              # Include PDF generation
"""
import subprocess
import sys
import os
import argparse
import time
from datetime import datetime

# --- Script Paths ---
# Core data generation
SCRIPT_BLADE_ELO = "./src/beyblade_elo.py"
SCRIPT_ADVANCED_STATS = "./src/advanced_stats.py"

# Analysis modules
SCRIPT_RPG_STATS = "./src/rpg_stats.py"
SCRIPT_UPSET_ANALYSIS = "./src/upset_analysis.py"
SCRIPT_META_BALANCE = "./src/meta_balance.py"
SCRIPT_SYNERGY_HEATMAPS = "./src/synergy_heatmaps.py"
SCRIPT_COUNTER_CHECKER = "./src/counter_checker.py"
SCRIPT_COMBO_EXPLORER = "./src/combo_explorer.py"

# Visualization
SCRIPT_GEN_PLOTS = "./src/gen_plots.py"
SCRIPT_PLOT_POSITIONS = "./src/plot_positions.py"

# Export
SCRIPT_SHEETS_UPLOAD = "./src/sheets_upload.py"
SCRIPT_EXPORT_PDF = "./src/export_leaderboard_pdf.py"

# Enable ANSI colors in Windows terminals (no-op on other systems)
os.system("")

# --- Colors ---
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
DIM = "\033[2m"


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Beyblade X Unified Update Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python update.py                    Run full pipeline (stats + analysis + plots)
  python update.py --skip-plots       Run without plot generation (faster)
  python update.py --stats-only       Only ELO and advanced stats
  python update.py --plots-only       Only generate plots
  python update.py --upload --pdf     Include upload and PDF export
        """
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run complete pipeline (same as default, included for clarity)"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only run core statistics (ELO + Advanced Stats)"
    )
    parser.add_argument(
        "--plots-only",
        action="store_true",
        help="Only run visualization/plot generation"
    )
    parser.add_argument(
        "--skip-plots", "-s",
        action="store_true",
        help="Skip plot generation (faster updates)"
    )
    parser.add_argument(
        "--upload", "-u",
        action="store_true",
        help="Upload data to Google Sheets after processing"
    )
    parser.add_argument(
        "--pdf", "-p",
        action="store_true",
        help="Generate PDF leaderboard after processing"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output from each script"
    )
    return parser.parse_args()


def log_step(message, level="info"):
    """
    Log a pipeline step with formatting and timestamp.

    Args:
        message (str): The message to log
        level (str): Log level, one of:
            - "info": Standard progress message (yellow arrow)
            - "success": Successful completion (green checkmark)
            - "error": Error message (red X)
            - "header": Pipeline header (cyan decorated box)
            - "section": Section divider (yellow arrow prefix)
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    if level == "info":
        print(f"{DIM}[{timestamp}]{RESET} {YELLOW}→{RESET} {message}")
    elif level == "success":
        print(f"{DIM}[{timestamp}]{RESET} {GREEN}✓{RESET} {message}")
    elif level == "error":
        print(f"{DIM}[{timestamp}]{RESET} {RED}✗{RESET} {message}")
    elif level == "header":
        print(f"\n{BOLD}{CYAN}{'=' * 60}{RESET}")
        print(f"{BOLD}{CYAN}  {message}{RESET}")
        print(f"{BOLD}{CYAN}{'=' * 60}{RESET}\n")
    elif level == "section":
        print(f"\n{BOLD}{YELLOW}▶ {message}{RESET}")


def run_script(script_path, description, verbose=False, stream_output=False):
    """
    Run a Python script and handle its output.

    Args:
        script_path (str): Path to the Python script to execute
        description (str): Human-readable description of the script for logging
        verbose (bool): If True, prints detailed output from the script.
            Default is False.
        stream_output (bool): If True, streams output line-by-line in real-time.
            Use for long-running scripts like plot generation. Default is False.

    Returns:
        tuple: A tuple containing:
            - success (bool): True if script exited with code 0
            - duration (float): Execution time in seconds
    """
    log_step(f"{description}...")
    start_time = time.time()

    try:
        if stream_output:
            # Stream output in real-time for long-running scripts
            process = subprocess.Popen(
                [sys.executable, "-u", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            for line in process.stdout:
                if verbose:
                    print(f"    {line}", end="")
            process.wait()
            returncode = process.returncode
            stdout = ""
            stderr = ""
        else:
            # Capture output for shorter scripts
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True
            )
            returncode = result.returncode
            stdout = result.stdout
            stderr = result.stderr

        duration = time.time() - start_time

        if returncode == 0:
            log_step(f"{description} ({duration:.1f}s)", "success")
            if verbose and stdout:
                for line in stdout.strip().split("\n"):
                    print(f"    {line}")
            return True, duration
        else:
            log_step(f"{description} failed (exit code {returncode})", "error")
            if stderr:
                for line in stderr.strip().split("\n"):
                    print(f"    {RED}{line}{RESET}")
            return False, duration

    except FileNotFoundError:
        duration = time.time() - start_time
        log_step(f"{description} - script not found: {script_path}", "error")
        return False, duration
    except Exception as e:
        duration = time.time() - start_time
        log_step(f"{description} - error: {e}", "error")
        return False, duration


def run_core_stats(verbose=False):
    """Run core statistics generation (ELO + Advanced Stats)."""
    log_step("Core Statistics", "section")
    results = []

    # Step 1: ELO Calculations
    success, duration = run_script(
        SCRIPT_BLADE_ELO,
        "ELO Calculations",
        verbose=verbose
    )
    results.append(("ELO Calculations", success, duration))

    # Step 2: Advanced Statistics (depends on ELO)
    success, duration = run_script(
        SCRIPT_ADVANCED_STATS,
        "Advanced Statistics",
        verbose=verbose
    )
    results.append(("Advanced Statistics", success, duration))

    return results


def run_analysis_modules(verbose=False):
    """Run all analysis modules."""
    log_step("Analysis Modules", "section")
    results = []

    # RPG Stats & Archetypes (depends on advanced_leaderboard)
    success, duration = run_script(
        SCRIPT_RPG_STATS,
        "RPG Stats & Archetypes",
        verbose=verbose
    )
    results.append(("RPG Stats", success, duration))

    # Upset Analysis (depends on elo_history)
    success, duration = run_script(
        SCRIPT_UPSET_ANALYSIS,
        "Upset Analysis",
        verbose=verbose
    )
    results.append(("Upset Analysis", success, duration))

    # Meta Balance (depends on elo_history, beys_data, advanced_leaderboard)
    success, duration = run_script(
        SCRIPT_META_BALANCE,
        "Meta Balance Analysis",
        verbose=verbose
    )
    results.append(("Meta Balance", success, duration))

    # Synergy Heatmaps
    success, duration = run_script(
        SCRIPT_SYNERGY_HEATMAPS,
        "Synergy Heatmaps",
        verbose=verbose
    )
    results.append(("Synergy Heatmaps", success, duration))

    # Bey Counters
    success, duration = run_script(
        SCRIPT_COUNTER_CHECKER,
        "Bey Counters",
        verbose=verbose
    )
    results.append(("Bey Counters", success, duration))

    # Combo Explorer (depends on beys_data, parts_stats, synergy_data, rpg_stats)
    success, duration = run_script(
        SCRIPT_COMBO_EXPLORER,
        "Combo Explorer Data",
        verbose=verbose
    )
    results.append(("Combo Explorer", success, duration))

    return results


def run_visualizations(verbose=False):
    """Run visualization generation."""
    log_step("Visualizations", "section")
    results = []

    # Main plot generation (streams output due to longer runtime)
    success, duration = run_script(
        SCRIPT_GEN_PLOTS,
        "Plot Generation",
        verbose=verbose,
        stream_output=True
    )
    results.append(("Plot Generation", success, duration))

    # Position plots
    success, duration = run_script(
        SCRIPT_PLOT_POSITIONS,
        "Position Plots",
        verbose=verbose
    )
    results.append(("Position Plots", success, duration))

    return results


def run_exports(args, verbose=False):
    """Run optional export steps."""
    results = []

    if args.pdf:
        log_step("Exports", "section")
        success, duration = run_script(
            SCRIPT_EXPORT_PDF,
            "PDF Leaderboard",
            verbose=verbose
        )
        results.append(("PDF Export", success, duration))

    if args.upload:
        if not args.pdf:
            log_step("Exports", "section")
        success, duration = run_script(
            SCRIPT_SHEETS_UPLOAD,
            "Google Sheets Upload",
            verbose=verbose,
            stream_output=True
        )
        results.append(("Sheets Upload", success, duration))

    return results


def print_summary(all_results, total_time):
    """Print a summary of the pipeline execution."""
    print(f"\n{BOLD}{CYAN}{'=' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  Pipeline Summary{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 60}{RESET}\n")

    successes = sum(1 for _, success, _ in all_results if success)
    failures = sum(1 for _, success, _ in all_results if not success)

    for name, success, duration in all_results:
        status = f"{GREEN}✓{RESET}" if success else f"{RED}✗{RESET}"
        print(f"  {status} {name}: {duration:.1f}s")

    print(f"\n  {BOLD}Total:{RESET} {len(all_results)} steps")
    print(f"  {GREEN}Passed:{RESET} {successes}")
    if failures > 0:
        print(f"  {RED}Failed:{RESET} {failures}")
    print(f"  {BOLD}Duration:{RESET} {total_time:.1f}s")

    if failures == 0:
        print(f"\n{GREEN}{BOLD}✓ Pipeline completed successfully!{RESET}")
    else:
        print(f"\n{RED}{BOLD}✗ Pipeline completed with {failures} failure(s){RESET}")


def determine_pipeline_stages(args):
    """
    Determine which pipeline stages to run based on command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        dict: Dictionary with boolean flags for each stage:
            - run_stats: Whether to run core statistics
            - run_analysis: Whether to run analysis modules
            - run_plots: Whether to run visualizations
    """
    # --plots-only: skip stats and analysis, only run plots
    # --stats-only: only run core stats, skip analysis and plots
    # --all: run everything including plots
    # --skip-plots: run stats and analysis, skip plots
    # default: run stats and analysis, skip plots

    run_stats = not args.plots_only
    run_analysis = not args.plots_only and not args.stats_only
    run_plots = args.all or args.plots_only or (not args.skip_plots and not args.stats_only)

    return {
        "run_stats": run_stats,
        "run_analysis": run_analysis,
        "run_plots": run_plots
    }


def main():
    """Main entry point for the update pipeline."""
    args = parse_args()
    start_time = time.time()
    all_results = []

    log_step("Beyblade X Update Pipeline", "header")

    # Determine what to run based on arguments
    stages = determine_pipeline_stages(args)

    # Execute pipeline stages
    if stages["run_stats"]:
        results = run_core_stats(verbose=args.verbose)
        all_results.extend(results)

    if stages["run_analysis"]:
        results = run_analysis_modules(verbose=args.verbose)
        all_results.extend(results)

    if stages["run_plots"]:
        results = run_visualizations(verbose=args.verbose)
        all_results.extend(results)

    # Optional exports
    results = run_exports(args, verbose=args.verbose)
    all_results.extend(results)

    # Print summary
    total_time = time.time() - start_time
    print_summary(all_results, total_time)


if __name__ == "__main__":
    main()
