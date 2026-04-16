#!/usr/bin/env python3
"""Interactive chat with MLX models on Apple Silicon."""

import argparse
import sys

# Available MLX models (already downloaded)
MODELS = {
    "gemma-2b": "mlx-community/gemma-2-2b-it-4bit",
    "gemma-old": "mlx-community/quantized-gemma-2b-it",
}

def main():
    parser = argparse.ArgumentParser(description="Chat with MLX models")
    parser.add_argument(
        "--model", "-m",
        default="gemma-2b",
        choices=MODELS.keys(),
        help="Model to use"
    )
    parser.add_argument(
        "--system",
        default="You are a helpful assistant.",
        help="System prompt"
    )
    args = parser.parse_args()

    from mlx_lm import load, generate

    model_name = MODELS[args.model]
    print(f"\n🔵 Loading model: {args.model}")
    print(f"   Repo: {model_name}")
    print("   Loading...\n")

    model, tokenizer = load(model_name)
    
    print("=" * 60)
    print(f"Model: {args.model}")
    print("Type 'quit' or 'exit' to leave, 'clear' to reset chat")
    print("=" * 60)
    
    messages = [{"role": "system", "content": args.system}]

    while True:
        try:
            user_input = input("\n💬 You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                print("👋 Bye!")
                break
            if user_input.lower() == "clear":
                messages = [{"role": "system", "content": args.system}]
                print("🔄 Chat cleared")
                continue

            messages.append({"role": "user", "content": user_input})

            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            
            print("\n🤖 Assistant: ", end="", flush=True)
            
            response = generate(model, tokenizer, prompt=text)
            print(response)

            messages.append({"role": "assistant", "content": response})

        except KeyboardInterrupt:
            print("\n\n👋 Bye!")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
