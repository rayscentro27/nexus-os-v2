from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]

types_file = ROOT / "src/lib/creditReportParserTypes.ts"
parser_file = ROOT / "src/lib/creditReportParser.ts"
bridge_file = ROOT / "src/lib/creditReportParserToCaseEngine.ts"
cli_file = ROOT / "scripts/credit/parse_credit_report_fixture.py"
fixture_dir = ROOT / "test_fixtures/credit_reports"
manifest = fixture_dir / "expected_extraction_manifest.json"
results_report = ROOT / "reports/credit_repair/credit_report_parser_fixture_results_latest.md"
admin = ROOT / "src/components/CreditSpecialistWorkbench.jsx"
upload_panel = ROOT / "src/components/client/SimpleDocumentUploadPanel.jsx"

texts = {
    "types": types_file.read_text(errors="ignore") if types_file.exists() else "",
    "parser": parser_file.read_text(errors="ignore") if parser_file.exists() else "",
    "bridge": bridge_file.read_text(errors="ignore") if bridge_file.exists() else "",
    "cli": cli_file.read_text(errors="ignore") if cli_file.exists() else "",
    "report": results_report.read_text(errors="ignore") if results_report.exists() else "",
    "admin": admin.read_text(errors="ignore") if admin.exists() else "",
    "upload": upload_panel.read_text(errors="ignore") if upload_panel.exists() else "",
}
combined = "\n".join(texts.values()).lower()

checks = []


def add(name, ok):
    checks.append((name, bool(ok)))


json_results = sorted((ROOT / "reports/credit_repair/parser_fixture_results").glob("*.json"))
parsed_results = []
for path in json_results:
    try:
        parsed_results.append(json.loads(path.read_text()))
    except Exception:
        pass

add("creditReportParserTypes.ts exists", types_file.exists() and "CreditReportParseResult" in texts["types"])
add("creditReportParser.ts exists", parser_file.exists() and "parseCreditReportText" in texts["parser"])
add("creditReportParserToCaseEngine.ts exists", bridge_file.exists() and "createConfirmedReportItemsFromDrafts" in texts["bridge"])
add("parse_credit_report_fixture.py exists", cli_file.exists() and "Suggested extraction only" in texts["cli"])
add("test_fixtures/credit_reports exists", fixture_dir.exists() and any(fixture_dir.glob("*.pdf")))
add("expected_extraction_manifest.json exists", manifest.exists())
add("parser fixture results report exists", results_report.exists() and "Files tested" in texts["report"])
add("parser output includes needsSpecialistReview true", parsed_results and all(r.get("needsSpecialistReview") is True for r in parsed_results))
add("parser output uses suggested extraction language", "suggested extraction" in combined and "needs goclear specialist review" in combined)
add("admin specialist parser preview exists", "Credit Report Parser Preview" in texts["admin"] and "Live report parsing requires backend extraction worker" in texts["admin"])
add("client upload copy keeps parser gated", "specialist must confirm" in texts["upload"] and "pending GoClear review" in texts["upload"])
add("parser bridge does not auto-create letters", "createLetterDraftFromOption" not in texts["bridge"] and "createDocuPost" not in texts["bridge"])
add("no verified-by-AI language", all(term not in combined for term in ["verified by ai", "ai verified", "clyde verified this", "parser verified"]))
add("no guaranteed deletion/score/funding language", all(term not in combined for term in ["guaranteed deletion", "guaranteed score", "guaranteed funding", "instant score increase"]))
add("no full sensitive data collection", all(term not in combined for term in ["collect ssn", "full dob storage", "full ein storage", "full account number", "bureau password", "bureau username"]))
add("no auto-letter creation from parser output", "credit_dispute_letter" not in texts["bridge"] and "createLetterDraftFromOption" not in texts["bridge"])
add("no auto-DocuPost send", "docupost gates remain unchanged" in combined and "auto-send" not in texts["bridge"].lower())
add("scanned fixture requires OCR/manual review when OCR unavailable", "scanned_screenshot" in texts["report"] and "OCR/manual review required" in texts["report"])

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    raise SystemExit(f"FAIL: {len(failed)} credit report parser preview checks failed")

print("RESULT: PASS - credit report parser preview checks passed")
