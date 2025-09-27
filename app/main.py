"""Command line entrypoint for the Python Grafana FastMCP SSE server."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import sys
from typing import Tuple

from dotenv import find_dotenv, load_dotenv

from . import __version__
from .config import (
    GRAFANA_ACCESS_TOKEN_ENV,
    GRAFANA_API_KEY_ENV,
    GRAFANA_ID_TOKEN_ENV,
    GRAFANA_PASSWORD_ENV,
    GRAFANA_SERVICE_ACCOUNT_ENV,
    GRAFANA_URL_ENV,
    GRAFANA_USERNAME_ENV,
)
from .server import create_app


def _request_shutdown(app: object, transport: str) -> None:
    """Best-effort cleanup when shutting down the FastMCP application."""

    logger = logging.getLogger(__name__)

    session_manager = getattr(app, "_session_manager", None)
    if session_manager is not None:
        task_group = getattr(session_manager, "_task_group", None)
        cancel_scope = getattr(task_group, "cancel_scope", None) if task_group is not None else None
        if cancel_scope is not None:
            try:
                cancel_scope.cancel()
                logger.debug("Cancelled StreamableHTTP session manager task group")
            except Exception:  # pragma: no cover - defensive cleanup
                logger.debug("Failed to cancel StreamableHTTP session manager", exc_info=True)

    if transport == "sse":
        server = getattr(app, "_uvicorn_server", None)
        if server is not None:
            try:
                server.should_exit = True
                logger.debug("Requested SSE server shutdown")
            except Exception:  # pragma: no cover - defensive cleanup
                logger.debug("Failed to request SSE server shutdown", exc_info=True)


def _parse_address(value: str) -> Tuple[str, int]:
    if ":" not in value:
        raise argparse.ArgumentTypeError("Address must be in HOST:PORT format")
    host, port_str = value.rsplit(":", 1)
    try:
        port = int(port_str)
    except ValueError as exc:  # pragma: no cover - defensive
        raise argparse.ArgumentTypeError("Port must be an integer") from exc
    return host, port


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Grafana FastMCP server.")
    parser.add_argument("--env-file", dest="env_file", default=None, help="Path to a .env file to load before starting")
    parser.add_argument("--address", default="localhost:8000", help="Host and port to bind the server")
    parser.add_argument("--base-path", default="/", help="Base path when using the SSE or Streamable HTTP transports")
    parser.add_argument("--log-level", default="INFO", help="Log level (DEBUG, INFO, WARN, ERROR)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode for FastMCP")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument(
        "--transport",
        choices=["sse", "streamable-http", "stdio"],
        default="stdio",
        help="Transport protocol to run (sse, streamable-http, or stdio)",
    )
    parser.add_argument(
        "--streamable-http-path",
        default="mcp",
        help="Path for the streamable HTTP endpoint (absolute or relative to the base path)",
    )

    env_arguments = {
        GRAFANA_URL_ENV: ("grafana_url", "Grafana base URL"),
        GRAFANA_SERVICE_ACCOUNT_ENV: ("grafana_service_account_token", "Grafana service account token"),
        GRAFANA_API_KEY_ENV: ("grafana_api_key", "Legacy Grafana API key"),
        GRAFANA_USERNAME_ENV: ("grafana_username", "Grafana username for basic auth"),
        GRAFANA_PASSWORD_ENV: ("grafana_password", "Grafana password for basic auth"),
        GRAFANA_ACCESS_TOKEN_ENV: ("grafana_access_token", "Grafana access token"),
        GRAFANA_ID_TOKEN_ENV: ("grafana_id_token", "Grafana ID token"),
    }

    for env_name, (dest, description) in env_arguments.items():
        parser.add_argument(
            f"--{env_name}",
            dest=dest,
            help=f"{description}. Overrides the {env_name} environment variable when provided.",
        )

    # First pass to resolve env-file parameter without consuming CLI overrides
    pre_args, _ = parser.parse_known_args(argv)

    project_root = Path(__file__).resolve().parent.parent
    running_frozen = bool(getattr(sys, "frozen", False))
    default_env = None if running_frozen else project_root / ".env"

    def _resolve_candidate(value: str | Path | None) -> Path | None:
        if not value:
            return None
        return Path(value).expanduser().resolve()

    selected_env: Path | None = None

    if default_env and default_env.exists():
        selected_env = default_env.resolve()
    else:
        fallback_candidates: list[Path | None] = [
            _resolve_candidate(pre_args.env_file),
            _resolve_candidate(os.getenv("ENV_FILE")),
            _resolve_candidate(Path.cwd() / ".env"),
        ]

        discovered = find_dotenv(usecwd=True)
        if discovered:
            fallback_candidates.append(_resolve_candidate(discovered))
        discovered_relative = find_dotenv(usecwd=False)
        if discovered_relative:
            fallback_candidates.append(_resolve_candidate(discovered_relative))

        for candidate in fallback_candidates:
            if candidate and candidate.exists():
                selected_env = candidate
                break

    if selected_env:
        # CLI arguments will override these values later; shell exports only apply when .env is missing.
        load_dotenv(selected_env, override=True)

    env_defaults = {
        "address": os.getenv("APP_ADDRESS"),
        "base_path": os.getenv("BASE_PATH"),
        "log_level": os.getenv("LOG_LEVEL"),
        "transport": os.getenv("TRANSPORT"),
        "streamable_http_path": os.getenv("STREAMABLE_HTTP_PATH"),
    }
    parser.set_defaults(**{key: value for key, value in env_defaults.items() if value })

    args = parser.parse_args(argv)

    argv_list = list(argv) if argv is not None else []
    transport_overridden = any(arg.startswith("--transport") for arg in argv_list)
    if running_frozen and not transport_overridden:
        args.transport = "stdio"
        os.environ["TRANSPORT"] = "stdio"

    if args.version:
        print(__version__)
        return

    for env_name, (dest, _) in env_arguments.items():
        value = getattr(args, dest, None)
        if value is not None:
            os.environ[env_name] = value

    host, port = _parse_address(args.address)
    log_level_name = args.log_level.upper()
    log_level_value = getattr(logging, log_level_name, logging.INFO)
    logging.basicConfig(level=log_level_value, format="%(levelname)s %(name)s: %(message)s")

    noisy_loggers = [
        "mcp.server",
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "httpx",
    ]
    target_level = logging.WARNING if (not args.debug and log_level_value >= logging.INFO) else log_level_value
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(target_level)

    base_path = args.base_path or "/"
    transport = args.transport
    app = create_app(
        host=host,
        port=port,
        base_path=base_path,
        streamable_http_path=args.streamable_http_path,
        log_level=log_level_name,
        debug=args.debug,
    )
    
    logger = logging.getLogger(__name__)
    if transport == "sse":
        logger.info("SSE endpoint available at '%s' (messages at '%s')", app.settings.sse_path, app.settings.message_path)
    elif transport == "streamable-http":
        logger.info("Streamable HTTP endpoint available at '%s'", app.settings.streamable_http_path)
    elif base_path not in ("", "/"):
        logger.info(
            "Ignoring base path '%s' because transport '%s' does not expose HTTP routes.",
            base_path,
            transport,
        )

    mount_path = app.settings.mount_path if transport == "sse" else None
    try:
        app.run(transport, mount_path=mount_path)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down Grafana FastMCP server...")
        _request_shutdown(app, transport)
        logger.info("Grafana FastMCP server stopped")

if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
