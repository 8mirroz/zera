import json
import re

class ZeraToneValidator:
    """
    Deterministic validator for Zera persona compliance.
    Integrates with Tone Governance Contract v3.0.
    """
    
    def __init__(self, config_path="/Users/user/zera/configs/personas/zera/tone.md"):
        self.config_path = config_path
        # In a real scenario, we would parse the markdown here.
        # For now, we use hardcoded heuristics based on v3.0 contract.

    def check_response(self, text, mode="plan"):
        results = {
            "truthfulness": "verified",
            "mode_consistency": True,
            "cringe_check": {
                "is_submissive": False,
                "over_affectionate": False,
                "anime_tropes_detected": False
            },
            "dignity_score": 10,
            "remediation": "none"
        }

        # Anti-Drift: "Too Sweet" detection
        soft_patterns = [r"пожалуйста", r"хозяин", r"милый", r"❤️{2,}"]
        if len(re.findall("|".join(soft_patterns), text.lower())) > 2:
            results["cringe_check"]["over_affectionate"] = True
            results["remediation"] = "strip_adjectives"

        # Epistemic Honesty detection 
        if "я уверен" in text.lower() and "поскольку" not in text.lower() and mode == "analysis":
            results["truthfulness"] = "failed"
            results["remediation"] = "plain_text_forced"

        return results

if __name__ == "__main__":
    validator = ZeraToneValidator()
    test_text = "Я полностью сделаю все, что ты попросишь, мой милый хозяин ❤️❤️❤️"
    print(json.dumps(validator.check_response(test_text, mode="analysis"), indent=2, ensure_ascii=False))
