import os
from pathlib import Path
from agent_os.config_loader import ModularConfigLoader
from agent_os.routing_vector import RoutingVector, RoutingVectorClassifier

def test_config_loader():
    repo_root = os.getcwd() # Assumes running from antigravity-core root
    loader = ModularConfigLoader(repo_root)
    
    print("Testing ModularConfigLoader with routing_policy.yaml...")
    suite = loader.load_suite("configs/global/routing_policy.yaml")
    
    assert "components" in suite
    intent_catalog = ModularConfigLoader.get_component(suite, "intent_catalog")
    assert intent_catalog is not None
    assert "intent_profiles" in intent_catalog._data
    print("✓ Successfully resolved intent_catalog component.")

def test_routing_intent_classification():
    repo_root = os.getcwd()
    loader = ModularConfigLoader(repo_root)
    
    print("Testing RoutingVector.from_intent for 'refactor'...")
    vec = RoutingVector.from_intent("refactor", loader)
    
    assert vec.blast_radius == 0.7
    assert vec.novelty == 0.3
    assert vec.ambiguity == 0.4
    print(f"✓ Correct dimensions for 'refactor': {vec}")

def test_classifier_initialization():
    repo_root = Path(os.getcwd())
    classifier = RoutingVectorClassifier(repo_root)
    
    print("Testing classifier initialization and loader access...")
    assert classifier.loader is not None
    print("✓ Classifier initialized with ModularConfigLoader.")

if __name__ == "__main__":
    try:
        test_config_loader()
        test_routing_intent_classification()
        test_classifier_initialization()
        print("\nALL SMOKE TESTS PASSED.")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
