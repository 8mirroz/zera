#!/usr/bin/env python3
"""Routing latency benchmark for Phase 8 Performance Optimization."""

import json
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent_os.model_router import ModelRouter
from agent_os.contracts import ModelRouteInput


def run_benchmark(router, num_iterations=100):
    """Benchmark routing latency for all T×C combinations."""
    task_types = ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]
    complexities = ["C1", "C2", "C3", "C4", "C5"]
    
    all_latencies = []
    combo_latencies = {}
    
    for _ in range(num_iterations):
        for task_type in task_types:
            for complexity in complexities:
                combo_key = f"{task_type}_{complexity}"
                
                start = time.perf_counter()
                try:
                    route_input = ModelRouteInput(
                        task_type=task_type,
                        complexity=complexity,
                        token_budget=20000,
                        cost_budget=0.3,
                        preferred_models=[],
                    )
                    router.route(route_input)
                except Exception as e:
                    print(f"Error routing {combo_key}: {e}")
                    continue
                elapsed_ms = (time.perf_counter() - start) * 1000
                
                all_latencies.append(elapsed_ms)
                if combo_key not in combo_latencies:
                    combo_latencies[combo_key] = []
                combo_latencies[combo_key].append(elapsed_ms)
    
    # Calculate percentiles
    all_latencies.sort()
    n = len(all_latencies)
    
    def percentile(data, p):
        if not data:
            return 0
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        return data[f] + (data[c] - data[f]) * (k - f)
    
    p50 = percentile(all_latencies, 50)
    p95 = percentile(all_latencies, 95)
    p99 = percentile(all_latencies, 99)
    
    # Per-combo stats
    combo_stats = {}
    for combo, latencies in combo_latencies.items():
        latencies.sort()
        combo_stats[combo] = {
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
            "count": len(latencies),
        }
    
    return {
        "total_requests": n,
        "p50_ms": round(p50, 3),
        "p95_ms": round(p95, 3),
        "p99_ms": round(p99, 3),
        "min_ms": round(min(all_latencies), 3) if all_latencies else 0,
        "max_ms": round(max(all_latencies), 3) if all_latencies else 0,
        "combo_stats": combo_stats,
    }


def main():
    repo_root = Path(__file__).parent.parent.parent.parent
    print(f"Repository root: {repo_root}")
    print(f"Running routing benchmark (100 iterations × 35 T×C combos = 3500 requests)...")
    
    router = ModelRouter(repo_root=repo_root)
    results = run_benchmark(router, num_iterations=100)
    
    print(f"\n=== BENCHMARK RESULTS ===")
    print(f"Total requests: {results['total_requests']}")
    print(f"p50 latency: {results['p50_ms']:.3f} ms")
    print(f"p95 latency: {results['p95_ms']:.3f} ms")
    print(f"p99 latency: {results['p99_ms']:.3f} ms")
    print(f"Min latency: {results['min_ms']:.3f} ms")
    print(f"Max latency: {results['max_ms']:.3f} ms")
    
    # Save results
    output_file = Path(__file__).parent.parent.parent.parent / "audit" / "110326" / "routing_benchmark_before.json"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    main()
