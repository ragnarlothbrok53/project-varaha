import sys
import json
import requests
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def evaluate(api_url: str):
    print("\n📦 Loading evaluation model (all-MiniLM-L6-v2)...")
    # small, fast, and high quality for general semantic similarity
    eval_model = SentenceTransformer('all-MiniLM-L6-v2')

    payload_path = "tests/evaluation_payload.json"
    try:
        with open(payload_path, "r") as f:
            tests = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: {payload_path} not found.")
        sys.exit(1)

    print(f"\n📊 Starting Semantic Evaluation of {len(tests)} test cases...")
    print("-" * 60)

    total_score = 0

    for t in tests:
        name = t.get("name", "Unknown Task")
        task = t.get("task")
        input_data = t.get("input")
        expected = t.get("expected_meaning")

        # Call API
        try:
            res = requests.post(
                f"{api_url}/v1/execute",
                json={"task": task, "input": input_data},
                headers={"Authorization": "Bearer admin-key"}
            )
            res.raise_for_status()
            actual = res.json().get("data", "")
        except Exception as e:
            print(f"❌ {name}: API Error ({e})")
            continue

        # Calculate Semantic Similarity
        # Encode both into embeddings
        embeddings = eval_model.encode([expected, actual])
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]

        total_score += similarity

        # Visual feedback based on score
        status_icon = "✅" if similarity > 0.7 else ("⚠️" if similarity > 0.4 else "❌")
        
        # Clean up output for display
        clean_actual = actual.replace('\n', ' ')
        
        print(f"{status_icon} {name:20} | Score: {similarity:.2f}")
        print(f"   Expected: {expected[:70]}")
        print(f"   Actual:   {clean_actual[:70]}")
        print("-" * 60)

    avg = total_score / len(tests)
    print(f"\n🏆 Final Semantic Accuracy: {avg:.2f}")

    if avg < 0.4:
        print("❌ CRITICAL: Accuracy is below the acceptable threshold.")
        sys.exit(1)

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    evaluate(target_url)
