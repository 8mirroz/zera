from __future__ import annotations

import time
import json
from pathlib import Path
from typing import Any

from ..contracts import AgentInput, AgentOutput
from ..observability import emit_event
from .base import RuntimeProvider

try:
    import mlx.core as mx
    import mlx_lm
    from mlx_lm import load
    from mlx_lm.generate import generate_step
    HAS_MLX = True
except ImportError:
    HAS_MLX = False

# TurboQuant Integration
HAS_TURBOQUANT = False
try:
    import sys
    vendor_path = Path(__file__).parent.parent.parent.parent.parent / "vendor" / "turboquant-mlx"
    if vendor_path.exists():
        sys.path.append(str(vendor_path))
        import turboquant.patch as tq_patch
        from turboquant.cache_v2 import TurboQuantKVCacheV2
        tq_patch.apply()
        HAS_TURBOQUANT = True
except Exception:
    HAS_TURBOQUANT = False

class MlxLmRuntimeProvider(RuntimeProvider):
    """
    Direct MLX-LM runtime for Apple Silicon.
    Supports KV-cache quantization (TurboQuant) and direct Metal execution.
    """

    name = "mlx_lm"

    def _make_turboquant_cache(self, model, bits=3):
        """Creates TurboQuant V2 KV-Caches for all layers."""
        head_dim = model.layers[0].self_attn.head_dim
        return [
            TurboQuantKVCacheV2(
                head_dim=head_dim, bits=bits, group_size=64,
                use_qjl=False, seed=42 + i,
            )
            for i in range(len(model.layers))
        ]

    def run(
        self,
        agent_input: AgentInput,
        *,
        repo_root: Path,
        runtime_profile: str | None = None,
    ) -> AgentOutput:
        start_ms = int(time.time() * 1000)
        
        if not HAS_MLX:
            return AgentOutput(
                status="failed",
                diff_summary="MLX libraries not found.",
                test_report={"status": "error", "details": "mlx or mlx_lm is not installed."},
                artifacts=[],
                next_action="Install mlx and mlx-lm packages.",
                response_text="Error: MLX is not available in this environment."
            )

        route_decision = agent_input.route_decision or {}
        model_id = route_decision.get("primary_model", "mlx-community/quantized-gemma-2b-it")
        
        # Clean up model_id if it has provider prefix
        if ":" in model_id:
             model_id = model_id.split(":")[-1]
        
        emit_event(
            "agent_run_started",
            {
                "component": "agent",
                "run_id": agent_input.run_id,
                "status": "ok",
                "message": f"Starting MLX-LM runtime with model {model_id} (TurboQuant: {HAS_TURBOQUANT})",
                "runtime_provider": self.name,
                "model": model_id,
                "turboquant_active": HAS_TURBOQUANT
            },
        )

        try:
            # Model loading (MLX caches models in ~/.cache/huggingface)
            model, tokenizer = load(model_id)
            
            # Persona and Prompt assembly
            persona_context = route_decision.get("persona_context") or ""
            
            # Construct messages with persona if available
            messages = []
            if persona_context:
                # Some models prefer the identity in the first user message or as a system prompt
                messages.append({"role": "user", "content": f"{persona_context}\n\n[USER OBJECTIVE]\n{agent_input.objective}"})
            else:
                messages.append({"role": "user", "content": agent_input.objective})

            if hasattr(tokenizer, "apply_chat_template"):
                prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            else:
                prompt = messages[0]["content"]

            input_ids = mx.array(tokenizer.encode(prompt))
            
            # Setup Cache (TurboQuant vs Standard)
            if HAS_TURBOQUANT:
                cache = self._make_turboquant_cache(model, bits=3) # Extreme 3-bit KV cache
            else:
                from mlx_lm.models.cache import make_prompt_cache
                cache = make_prompt_cache(model)

            # Generate response token by token (to support the custom cache)
            tokens = []
            for token, _ in generate_step(
                prompt=input_ids,
                model=model,
                max_tokens=1024,
                prompt_cache=cache,
            ):
                tok = token.item() if hasattr(token, "item") else int(token)
                if tok == tokenizer.eos_token_id:
                    break
                tokens.append(tok)
            
            response = tokenizer.decode(tokens)
            
            output = AgentOutput(
                status="completed",
                diff_summary="MLX-LM execution completed successfully.",
                test_report={
                    "status": "ok", 
                    "details": f"Model: {model_id}, Cache: {'TurboQuant 3-bit' if HAS_TURBOQUANT else 'Standard FP16'}"
                },
                artifacts=[],
                next_action="Analyze model response and proceed with task.",
                response_text=response
            )
        except Exception as e:
            output = AgentOutput(
                status="failed",
                diff_summary=f"MLX-LM execution failed: {str(e)}",
                test_report={"status": "error", "details": str(e)},
                artifacts=[],
                next_action="Check model compatibility or connectivity.",
                response_text=f"Error during MLX inference: {str(e)}"
            )

        duration_ms = int(time.time() * 1000) - start_ms
        emit_event(
            "agent_run_completed",
            {
                "component": "agent",
                "run_id": agent_input.run_id,
                "status": output.status,
                "duration_ms": duration_ms,
                "runtime_provider": self.name
            },
        )
        
        return output
