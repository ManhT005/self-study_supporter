"""Default offline. --live is a manual opt-in to at most two synthetic model requests."""

import argparse
import asyncio
import json
import os
from dataclasses import asdict

from study_supporter.infrastructure.llm.langchain_bridge import (
    NativeModelConfig,
    create_native_model,
    probe_native_model,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--provider", choices=["ollama", "gemini"])
    parser.add_argument("--model")
    parser.add_argument("--base-url", default="http://localhost:11434")
    args = parser.parse_args()
    if args.live:
        if not args.provider or not args.model:
            parser.error("--live requires --provider and an explicit --model")
        config = NativeModelConfig(
            args.provider,
            args.model,
            base_url=args.base_url,
            api_key=os.environ.get("GEMINI_API_KEY", ""),
        )
        model = create_native_model(config)
    else:
        from scripts.langchain_fixtures import capability_model

        config = NativeModelConfig("ollama", "offline-fixture:1")
        model = capability_model()
    receipt = asyncio.run(probe_native_model(model, config))
    print(json.dumps({"mode": "live" if args.live else "offline", **asdict(receipt)}))
    return 0 if receipt.available else 1


if __name__ == "__main__":
    raise SystemExit(main())
