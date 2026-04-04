import sys
import time
import asyncio
import aiohttp
import numpy as np
from typing import List

async def fetch_job(session: aiohttp.ClientSession, url: str, payload: dict) -> float:
    """Send a single request and return the elapsed time in seconds."""
    start = time.time()
    try:
        async with session.post(url, json=payload, headers={"Authorization": "Bearer admin-key"}) as response:
            await response.json()
            return time.time() - start
    except Exception as e:
        print(f"❌ Benchmarking Error: {e}")
        return 0.0

async def run_benchmark(api_url: str, concurrency: int = 10, total_jobs: int = 50):
    """Run a high-concurrency benchmark and report latency statistics."""
    print("\n⚡ Starting Concurrency Benchmark...")
    print(f"🔹 Target: {api_url}")
    print(f"🔹 Jobs: {total_jobs} total, {concurrency} concurrent")
    print("-" * 50)

    endpoint = f"{api_url}/v1/execute"
    payload = {
        "task": "summarize",
        "input": {"text": "This is a high-concurrency benchmark test for the Varaha LLM Proxy."}
    }

    latencies: List[float] = []
    
    # Use a semaphore to control concurrency
    sem = asyncio.Semaphore(concurrency)

    async def sem_fetch(session):
        async with sem:
            lat = await fetch_job(session, endpoint, payload)
            if lat > 0:
                latencies.append(lat)

    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        tasks = [sem_fetch(session) for _ in range(total_jobs)]
        await asyncio.gather(*tasks)
    
    total_duration = time.time() - start_time

    if not latencies:
        print("❌ Benchmark failed to collect results.")
        return

    # Calculate statistics (ms)
    l_ms = np.array(latencies) * 1000
    p50 = np.percentile(l_ms, 50)
    p95 = np.percentile(l_ms, 95)
    p99 = np.percentile(l_ms, 99)
    avg = np.mean(l_ms)
    rps = len(latencies) / total_duration

    print(f"✅ Benchmark Complete in {total_duration:.2f}s")
    print(f"📈 Throughput: {rps:.2f} req/s")
    print("-" * 40)
    print(f"📊 Mean Latency: {avg:.1f} ms")
    print(f"📊 Median (p50): {p50:.1f} ms")
    print(f"🚀 p95 Latency:  {p95:.1f} ms")
    print(f"🔥 p99 Latency:  {p99:.1f} ms")
    print("-" * 40)

    # 🕵️ Final Verification: Check Database for the last job
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_url}/v1/requests") as r:
                ids = (await r.json()).get("requests", [])
                if ids:
                    recent_id = ids[0]
                    async with session.get(f"{api_url}/v1/requests/{recent_id}/metrics") as mr:
                        metrics_data = (await mr.json()).get("metrics", {})
                        print(f"✅ DB Verification: Job {recent_id[:8]} found in SQLite")
                        print(f"   📊 Metrics: {metrics_data.get('input_tokens')} in, {metrics_data.get('output_tokens')} out | TPS: {metrics_data.get('tps')}")
                else:
                    print("⚠️ DB Verification: No requests found in database.")
    except Exception as e:
        print(f"⚠️ DB Verification failed: {e}")

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    conc = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    jobs = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    
    asyncio.run(run_benchmark(url, conc, jobs))
