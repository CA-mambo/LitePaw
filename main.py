# -*- coding: utf-8 -*-
"""LitePaw entry point."""

import asyncio
import logging
import sys
from pathlib import Path

# Load .env file before anything else
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not available

import yaml

from litepaw.config.settings import Settings
from litepaw.server.ws_server import run_server


def setup_logging(level: str = "INFO") -> None:
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_settings(config_path: str | None) -> Settings:
    """Load settings from file or environment."""
    if config_path and Path(config_path).exists():
        return Settings.from_yaml(config_path)
    return Settings.from_env()


def main() -> None:
    """Run LitePaw service."""
    import argparse

    parser = argparse.ArgumentParser(description="LitePaw — Lightweight QwenPaw memory service")
    parser.add_argument("-c", "--config", help="Path to YAML config file")
    parser.add_argument("--host", help="Server bind host")
    parser.add_argument("--port", type=int, help="Server bind port")
    parser.add_argument("--workspace", help="Memory workspace directory")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    args = parser.parse_args()

    setup_logging(args.log_level)

    settings = load_settings(args.config)

    # CLI args override
    if args.host:
        settings.host = args.host
    if args.port:
        settings.port = args.port
    if args.workspace:
        settings.workspace_dir = args.workspace

    # Ensure workspace exists
    Path(settings.workspace_dir).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("litepaw")
    logger.info("Starting LitePaw v0.1.0")
    logger.info("Workspace: %s", settings.workspace_dir)
    logger.info("LLM: %s", settings.llm.model)
    logger.info("Memory backend: %s", settings.memory.backend)
    logger.info("Listening on %s:%d", settings.host, settings.port)

    asyncio.run(run_server(settings))


if __name__ == "__main__":
    main()
