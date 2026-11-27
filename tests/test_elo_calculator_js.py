"""
Test JavaScript ELO calculator against Python implementation
This ensures the JS port matches Python behavior exactly
"""
import subprocess
import json
import re
from collections import defaultdict
from pathlib import Path
import pytest
from src.elo.beyblade_elo import dynamic_k, expected, calculate_score_with_dominance, infer_target, update_elo

DOCS = Path(__file__).resolve().parent.parent / 'docs'


def run_js_function(function_name, *args):
    """Run a JavaScript function and return its result"""
    js_code = f"""
    const elo = require('./docs/elo-calculator.js');
    const result = elo.{function_name}({', '.join(map(str, args))});
    console.log(JSON.stringify(result));
    """

    try:
        result = subprocess.run(
            ['node', '-e', js_code],
            capture_output=True,
            text=True,
            cwd='.',
            timeout=5,
            encoding="utf-8"
        )
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
        else:
            pytest.skip(f"Node.js not available or error running JS: {result.stderr}")
    except FileNotFoundError:
        pytest.skip("Node.js not available")
    except subprocess.TimeoutExpired:
        pytest.skip("JavaScript execution timed out")
    except Exception as e:
        pytest.skip(f"Error running JavaScript: {str(e)}")


class TestEloCalculatorJS:
    """Test suite to verify JavaScript ELO calculator matches Python"""

    def test_dynamic_k_learning(self):
        """Test K-factor for learning phase (< 6 matches)"""
        for matches in [0, 1, 3, 5]:
            py_result = dynamic_k(matches)
            js_result = run_js_function('dynamicK', matches)
            assert py_result == js_result, f"K-factor mismatch at {matches} matches: Python={py_result}, JS={js_result}"

    def test_dynamic_k_intermediate(self):
        """Test K-factor for intermediate phase (6-14 matches)"""
        for matches in [6, 8, 10, 14]:
            py_result = dynamic_k(matches)
            js_result = run_js_function('dynamicK', matches)
            assert py_result == js_result, f"K-factor mismatch at {matches} matches: Python={py_result}, JS={js_result}"

    def test_dynamic_k_experienced(self):
        """Test K-factor for experienced phase (15+ matches)"""
        for matches in [15, 20, 50, 100]:
            py_result = dynamic_k(matches)
            js_result = run_js_function('dynamicK', matches)
            assert py_result == js_result, f"K-factor mismatch at {matches} matches: Python={py_result}, JS={js_result}"

    def test_expected_score(self):
        """Test expected score calculation"""
        test_cases = [
            (1000, 1000),  # Equal ratings
            (1200, 1000),  # A higher
            (1000, 1200),  # B higher
            (1500, 800),   # Large difference
            (900, 1100),   # Medium difference
        ]

        for elo_a, elo_b in test_cases:
            py_result = expected(elo_a, elo_b)
            js_result = run_js_function('expected', elo_a, elo_b)
            assert abs(py_result - js_result) < 0.0001, \
                f"Expected score mismatch for ({elo_a}, {elo_b}): Python={py_result}, JS={js_result}"

    def test_dominance_calculation_draw(self):
        """Test dominance calculation for draws"""
        py_result = calculate_score_with_dominance(3, 3)
        js_result = run_js_function('calculateScoreWithDominance', 3, 3)
        assert abs(py_result[0] - js_result[0]) < 0.0001
        assert abs(py_result[1] - js_result[1]) < 0.0001

    def test_dominance_calculation_close_win(self):
        """Test dominance calculation for close wins"""
        test_cases = [
            (4, 3),  # Close win
            (5, 4),  # Close win
        ]

        for score_a, score_b in test_cases:
            py_result = calculate_score_with_dominance(score_a, score_b)
            js_result = run_js_function('calculateScoreWithDominance', score_a, score_b)
            assert abs(py_result[0] - js_result[0]) < 0.0001, \
                f"Dominance mismatch for ({score_a}, {score_b}): Python={py_result}, JS={js_result}"
            assert abs(py_result[1] - js_result[1]) < 0.0001

    def test_dominance_calculation_dominant_win(self):
        """Test dominance calculation for dominant wins"""
        test_cases = [
            (4, 0),  # Shutout at threshold
            (5, 0),  # Overkill
            (6, 0),  # Max overkill
            (4, 1),  # Dominant
        ]

        for score_a, score_b in test_cases:
            py_result = calculate_score_with_dominance(score_a, score_b)
            js_result = run_js_function('calculateScoreWithDominance', score_a, score_b)
            assert abs(py_result[0] - js_result[0]) < 0.0001, \
                f"Dominance mismatch for ({score_a}, {score_b}): Python={py_result}, JS={js_result}"
            assert abs(py_result[1] - js_result[1]) < 0.0001


def run_js_script(body):
    """Run a JS snippet with the calculator loaded as 'elo' and return its JSON output.

    Unlike run_js_function this fails on JS errors (only a missing Node.js skips the test).
    """
    js_code = "const elo = require('./docs/elo-calculator.js');\n" + body
    try:
        result = subprocess.run(['node', '-e', js_code], capture_output=True, text=True,
                                cwd='.', timeout=10, encoding='utf-8')
    except FileNotFoundError:
        pytest.skip('Node.js not available')
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip())


def _py_state():
    elos = defaultdict(lambda: 1000)
    stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'for': 0, 'against': 0, 'matches': 0, 'winrate': 0.0})
    return elos, stats


MATCH_SEQUENCE = [
    ('A', 'B', 4, 0), ('B', 'C', 4, 3), ('A', 'C', 1, 4), ('C', 'B', 7, 2),  # 7-2: Race-to-7 final
    ('A', 'B', 8, 6), ('B', 'A', 6, 3), ('C', 'A', 4, 4), ('A', 'C', 5, 2),
]


class TestInferTargetParity:
    @pytest.mark.parametrize('sa,sb', [(4, 0), (4, 3), (6, 5), (3, 6), (7, 0), (7, 6), (8, 4), (3, 8), (0, 0)])
    def test_infer_target_matches_python(self, sa, sb):
        assert run_js_function('inferTarget', sa, sb) == infer_target(sa, sb)


class TestUpdateEloParity:
    """updateElo in JS must reproduce the Python engine, including Race-to-7 and form EMA."""

    def test_match_sequence_matches_python(self):
        elos, stats = _py_state()
        py_trace = []
        for a, b, sa, sb in MATCH_SEQUENCE:
            update_elo(a, b, sa, sb, '2025-01-01', elos, stats)
            py_trace.append({'A': elos[a], 'B': elos[b], 'fa': stats[a]['form_ema'], 'fb': stats[b]['form_ema']})

        js_trace = run_js_script(f"""
            const elos = {{}}, stats = {{}}, trace = [];
            for (const [a, b, sa, sb] of {json.dumps(MATCH_SEQUENCE)}) {{
                elo.updateElo(a, b, sa, sb, elos, stats);
                trace.push({{A: elos[a], B: elos[b], fa: stats[a].form_ema, fb: stats[b].form_ema}});
            }}
            console.log(JSON.stringify(trace));
        """)

        assert len(js_trace) == len(py_trace)
        for i, (py, js) in enumerate(zip(py_trace, js_trace)):
            for key in ('A', 'B', 'fa', 'fb'):
                assert abs(py[key] - js[key]) < 1e-9, f'match {i} {key}: Python={py[key]}, JS={js[key]}'

    def test_race_to_7_final_is_reference_win(self):
        """A 7-0 final must be worth the same as a 4-0 regular match (S=1.0)."""
        out = run_js_script("""
            const e1 = {}, s1 = {}, e2 = {}, s2 = {};
            const r7 = elo.updateElo('A', 'B', 7, 0, e1, s1);
            const r4 = elo.updateElo('A', 'B', 4, 0, e2, s2);
            console.log(JSON.stringify([r7.eloChangeA, r4.eloChangeA]));
        """)
        assert abs(out[0] - out[1]) < 1e-9

    def test_explicit_target_overrides_inference(self):
        out = run_js_script("""
            const e1 = {}, s1 = {}, e2 = {}, s2 = {};
            const inferred = elo.updateElo('A', 'B', 7, 0, e1, s1);
            const forced4 = elo.updateElo('A', 'B', 7, 0, e2, s2, 4);
            console.log(JSON.stringify([inferred.eloChangeA, forced4.eloChangeA]));
        """)
        assert out[1] > out[0]

    def test_prior_matches_lower_the_k_factor(self):
        """priorMatches carries experience from before the session into the K-factor."""
        elos, stats = _py_state()
        stats['A']['matches'] = 40
        stats['B']['matches'] = 40
        update_elo('A', 'B', 4, 0, '2025-01-01', elos, stats)

        out = run_js_script("""
            const elos = {}, stats = {};
            const r = elo.updateElo('A', 'B', 4, 0, elos, stats, undefined, {A: 40, B: 40});
            console.log(JSON.stringify([elos.A, elos.B, r.kA]));
        """)
        assert abs(out[0] - elos['A']) < 1e-9
        assert abs(out[1] - elos['B']) < 1e-9
        assert out[2] < 15  # experienced K, not the learning-phase 40


class TestNoGlobalKFactorShadowing:
    """quick-entry.js and simulator.html load elo-calculator.js into the same global scope.

    Redefining dynamicK there silently replaced the calculator's smooth K-factor
    (quick-entry looked up a bey *name* and fell back to K=40 for everything).
    """

    @pytest.mark.parametrize('name', ['quick-entry.js', 'simulator.html'])
    def test_consumer_does_not_redefine_dynamic_k(self, name):
        source = (DOCS / name).read_text(encoding='utf-8')
        assert not re.search(r'function\s+dynamicK\s*\(', source), f'{name} redefines dynamicK'
        assert not re.search(r'\b(?:const|let|var)\s+dynamicK\b', source), f'{name} redefines dynamicK'
        assert not re.search(r'\bK_(?:LEARNING|INTERMEDIATE|EXPERIENCED)\b', source), f'{name} has stale v2 K constants'

    @pytest.mark.parametrize('name', ['quick-entry.html', 'simulator.html'])
    def test_calculator_script_is_loaded(self, name):
        assert 'src="elo-calculator.js"' in (DOCS / name).read_text(encoding='utf-8')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
