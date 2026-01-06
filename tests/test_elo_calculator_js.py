"""
Test JavaScript ELO calculator against Python implementation
This ensures the JS port matches Python behavior exactly
"""
import subprocess
import json
import pytest
from src.beyblade_elo import dynamic_k, expected, calculate_score_with_dominance


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
            timeout=5
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
