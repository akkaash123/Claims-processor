import os
from dotenv import load_dotenv

# MUST BE AT THE VERY TOP: Load environment variables before any LangChain imports
load_dotenv()

import json
import time
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app  

# Initialize TestClient to bypass network overhead during evaluation
client = TestClient(app)

def load_test_cases(filepath: str = "data/test_cases.json") -> list:
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data.get("test_cases", [])

def run_evaluation():
    test_cases = load_test_cases()
    report_lines = []
    
    report_lines.append("# Plum AI Claims Processor - Eval Report")
    report_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"**Total Cases:** {len(test_cases)}\n")
    report_lines.append("---\n")

    print(f"Starting evaluation of {len(test_cases)} cases...")
    print("NOTE: Pacing requests to 1 every 13 seconds to respect free-tier rate limits (5 requests/min).\n")

    for index, tc in enumerate(test_cases):
        case_id = tc["case_id"]
        case_name = tc["case_name"]
        expected = tc["expected"]
        
        print(f"Processing {case_id}: {case_name}...")
        
        report_lines.append(f"## {case_id}: {case_name}")
        report_lines.append(f"**Description:** {tc['description']}\n")
        
        start_time = time.time()
        
        # Execute the test payload against our JSON endpoint
        try:
            response = client.post("/api/v1/evaluate-test-cases", json=tc["input"])
            actual_output = response.json()
            status_code = response.status_code
        except Exception as e:
            actual_output = {"error": str(e)}
            status_code = 500
            
        execution_time = time.time() - start_time
        
        report_lines.append("### Expected Outcome")
        report_lines.append('```json')
        report_lines.append(json.dumps(expected, indent=2))
        report_lines.append('```\n')
        
        report_lines.append("### Actual System Output (With Trace)")
        report_lines.append('```json')
        report_lines.append(json.dumps(actual_output, indent=2))
        report_lines.append('```\n')
        
        report_lines.append(f"**Execution Time:** {execution_time:.2f} seconds")
        report_lines.append("---\n")

        # Rate Limiting: Wait 13 seconds between requests, but don't wait after the very last one.
        if index < len(test_cases) - 1:
            time.sleep(13)

    # Write the Markdown report safely
    with open("eval_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print("\nEvaluation complete! Report generated at eval_report.md")

if __name__ == "__main__":
    run_evaluation()