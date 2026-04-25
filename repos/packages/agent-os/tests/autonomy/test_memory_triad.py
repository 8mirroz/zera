import pytest
from datetime import datetime, timedelta, timezone
from agent_os.memory.triad import MemoryTriad, MemoryRecord

@pytest.fixture
def memory_config():
    return {
        "memory_layers": {
            "episodic": {
                "recency_decay": 0.995,
                "importance_threshold": 0.7
            },
            "semantic": {
                "confidence_decay": 0.98
            }
        },
        "retrieval_weights": {
            "episodic": 0.5,
            "semantic": 0.5
        }
    }

def test_scoring_with_decay(memory_config):
    triad = MemoryTriad(memory_config)
    
    # Create a fresh record
    fresh_record = MemoryRecord(
        content="Fresh info",
        layer="episodic",
        timestamp=datetime.now(timezone.utc)
    )
    
    # Create an old record (10 days ago)
    old_record = MemoryRecord(
        content="Old info",
        layer="episodic",
        timestamp=datetime.now(timezone.utc) - timedelta(days=10)
    )
    
    fresh_score = triad.score_record(fresh_record, query_similarity=1.0)
    old_score = triad.score_record(old_record, query_similarity=1.0)
    
    # Fresh should be exactly similarity * importance (1.0 * 1.0)
    assert fresh_score == pytest.approx(1.0)
    # Old should be similarity * (0.995^10) * importance
    expected_old = pow(0.995, 10.0)
    assert old_score == pytest.approx(expected_old)
    assert fresh_score > old_score

def test_memorize(memory_config):
    triad = MemoryTriad(memory_config)
    record = triad.memorize("User likes coffee", layer="semantic", importance=0.9)
    
    assert record.content == "User likes coffee"
    assert record.layer == "semantic"
    assert record.importance == 0.9
