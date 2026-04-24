from typing import List

class RetrievedResult:
    def __init__(self, content: str, source: str, confidence: float):
        self.content = content
        self.source = source
        self.confidence = confidence

def activate_fallback(query: str, chain: List[str]) -> List[RetrievedResult]:
    """Activate fallback chain in deterministic order."""
    for strategy in chain:
        if strategy == 'session_memory':
            return [RetrievedResult("Recovered from Zera session memory", "session_log", 0.4)]
        elif strategy == 'explicit_unknown':
            return [RetrievedResult("No information found in Zera vault.", "system", 1.0)]
    return []
