"""Quiescent PostgreSQL + local Chroma backup; restore only to a different project."""

import argparse
import json
import subprocess
from pathlib import Path


def run(command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "restore"])
    parser.add_argument("directory", type=Path)
    parser.add_argument("--env-file", default=".env.docker")
    parser.add_argument("--project-name", required=True)
    args = parser.parse_args()
    compose = [
        "docker",
        "compose",
        "--env-file",
        args.env_file,
        "-p",
        args.project_name,
    ]
    directory = args.directory.resolve()
    if args.action == "backup":
        directory.mkdir(parents=True, exist_ok=False)
        running = run(
            compose + ["ps", "--status", "running", "--services"],
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        run(compose + ["stop", "app"])
        try:
            with (directory / "postgres.dump").open("wb") as output:
                run(
                    compose
                    + [
                        "exec",
                        "-T",
                        "db",
                        "sh",
                        "-c",
                        'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"',
                    ],
                    stdout=output,
                )
            with (directory / "app-data.tar.gz").open("wb") as output:
                run(
                    compose
                    + [
                        "run",
                        "--rm",
                        "--no-deps",
                        "-T",
                        "--entrypoint",
                        "tar",
                        "app",
                        "-czf",
                        "-",
                        "-C",
                        "/app/data",
                        ".",
                    ],
                    stdout=output,
                )
            (directory / "manifest.json").write_text(
                json.dumps(
                    {
                        "project": args.project_name,
                        "format": 1,
                        "scope": "PostgreSQL + /app/data; local Chroma only, no HF weights",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        finally:
            if "app" in running:
                run(compose + ["start", "app"])
    else:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        if manifest["project"] == args.project_name:
            parser.error("Restore requires a different disposable Compose project.")
        existing = run(compose + ["ps", "-a", "-q"], capture_output=True, text=True).stdout
        volumes = run(
            [
                "docker",
                "volume",
                "ls",
                "-q",
                "--filter",
                f"label=com.docker.compose.project={args.project_name}",
            ],
            capture_output=True,
            text=True,
        ).stdout
        if existing.strip() or volumes.strip():
            parser.error("Target must be a fresh project with no containers or volumes.")
        run(compose + ["up", "-d", "--wait", "db"])
        with (directory / "postgres.dump").open("rb") as source:
            run(
                compose
                + [
                    "exec",
                    "-T",
                    "db",
                    "sh",
                    "-c",
                    'pg_restore --exit-on-error --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
                ],
                stdin=source,
            )
        with (directory / "app-data.tar.gz").open("rb") as source:
            run(
                compose
                + [
                    "run",
                    "--rm",
                    "--no-deps",
                    "-T",
                    "--entrypoint",
                    "tar",
                    "app",
                    "-xzf",
                    "-",
                    "-C",
                    "/app/data",
                ],
                stdin=source,
            )
        print("Restored. Set a free APP_PORT in the target env file before starting app.")


if __name__ == "__main__":
    main()
