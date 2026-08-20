#!/usr/bin/env python3
"""Role detection — scan project files and return applicable roles.

No LLM. No API calls. File pattern matching only.
Runs at session start — must be fast (milliseconds).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


# --- Role detection signals ---
# Each role has file patterns and dependency patterns to look for.
# Signals are checked in order; more matches = higher confidence.

ROLE_SIGNALS = {
    "frontend": {
        "files": ["*.tsx", "*.jsx", "*.vue", "*.svelte", "next.config.*",
                  "vite.config.*", "nuxt.config.*", "angular.json"],
        "deps": ["react", "vue", "angular", "svelte", "next", "nuxt",
                 "remix", "solid-js", "preact", "astro"],
        "dep_files": ["package.json"],
    },
    "backend": {
        "files": ["server.*", "app.py", "main.py", "manage.py",
                  "src/index.ts", "src/main.ts", "src/app.ts"],
        "dirs": ["src/routes", "src/controllers", "src/api",
                 "src/handlers", "routes", "controllers", "api"],
        "deps": ["express", "fastapi", "django", "flask", "spring-boot",
                 "nestjs", "hono", "koa", "gin", "fiber", "actix-web",
                 "rails", "laravel"],
        "dep_files": ["package.json", "requirements.txt", "pyproject.toml",
                      "Gemfile", "go.mod", "Cargo.toml", "pom.xml",
                      "build.gradle"],
    },
    "ios": {
        "files": ["Podfile", "*.xcworkspace", "Package.swift",
                  "Info.plist", "AppDelegate.swift"],
        "dirs": ["*.xcodeproj"],
        "deps": [],
        "dep_files": [],
    },
    "android": {
        "files": ["build.gradle", "build.gradle.kts", "AndroidManifest.xml",
                  "settings.gradle", "settings.gradle.kts"],
        "dirs": ["app/src/main"],
        "deps": [],
        "dep_files": [],
    },
    "dba": {
        "files": ["*.sql", "prisma/schema.prisma", "drizzle.config.*",
                  "knexfile.*", "sequelize.config.*", "alembic.ini"],
        "dirs": ["migrations", "prisma", "drizzle", "db"],
        "deps": ["prisma", "drizzle-orm", "knex", "sequelize", "typeorm",
                 "sqlalchemy", "django", "alembic", "kysely"],
        "dep_files": ["package.json", "requirements.txt", "pyproject.toml"],
    },
    "security": {
        "files": [".env", ".env.example", ".env.local"],
        "dirs": ["src/auth", "src/middleware", "auth"],
        "deps": ["helmet", "cors", "jsonwebtoken", "bcrypt", "argon2",
                 "passport", "lucia", "next-auth", "clerk",
                 "python-jose", "pyjwt", "cryptography"],
        "dep_files": ["package.json", "requirements.txt", "pyproject.toml"],
    },
    "infrastructure": {
        "files": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml",
                  ".github/workflows/*.yml", ".github/workflows/*.yaml",
                  "Jenkinsfile", ".gitlab-ci.yml"],
        "dirs": ["terraform", "k8s", "kubernetes", "helm",
                 "infra", ".github/workflows"],
        "deps": [],
        "dep_files": [],
    },
    "production": {
        # Production engineer is cross-cutting — activated when
        # there's something to run and verify
        "files": ["package.json", "requirements.txt", "Makefile",
                  "docker-compose.yml"],
        "dirs": ["src", "app", "lib"],
        "deps": [],
        "dep_files": [],
        "min_signals": 2,  # needs at least 2 signals to activate
    },
    "data-engineer": {
        "files": ["dags/*.py", "airflow.cfg", "dbt_project.yml"],
        "dirs": ["dags", "pipelines", "etl", "dbt"],
        "deps": ["apache-airflow", "dagster", "prefect", "dbt-core",
                 "pyspark", "kafka-python", "confluent-kafka"],
        "dep_files": ["requirements.txt", "pyproject.toml"],
    },
    "data-scientist": {
        "files": ["*.ipynb"],
        "deps": ["pandas", "numpy", "scikit-learn", "scipy",
                 "statsmodels", "matplotlib", "seaborn", "jupyter"],
        "dep_files": ["requirements.txt", "pyproject.toml"],
    },
    "ai-ml": {
        "files": ["*.pt", "*.onnx", "*.safetensors", "model_config.json"],
        "deps": ["torch", "tensorflow", "transformers", "langchain",
                 "llama-index", "openai", "anthropic", "pinecone",
                 "qdrant-client", "chromadb", "mlflow"],
        "dep_files": ["requirements.txt", "pyproject.toml", "package.json"],
    },
    "qa": {
        "files": ["cypress.config.*", "playwright.config.*", "jest.config.*",
                  "vitest.config.*", "pytest.ini", "conftest.py"],
        "dirs": ["cypress", "playwright", "__tests__", "e2e"],
        "deps": ["cypress", "playwright", "jest", "vitest", "pytest",
                 "mocha", "selenium"],
        "dep_files": ["package.json", "requirements.txt", "pyproject.toml"],
    },
    "architect": {
        "files": ["architecture/*.md", "docs/architecture*", "ADR-*.md"],
        "dirs": ["architecture", "docs/adr"],
        "deps": [],
        "dep_files": [],
    },
    "code-health": {
        "files": [".eslintrc*", ".prettierrc*", "biome.json", "ruff.toml", ".flake8"],
        "deps": ["eslint", "prettier", "biome", "ruff"],
        "dep_files": ["package.json", "pyproject.toml"],
        "min_signals": 2,
    },
    "game-dev": {
        "files": ["project.godot", "*.unity", "*.uproject"],
        "dirs": ["Assets", "Scenes", "Scripts", "Shaders"],
        "deps": ["bevy", "ggez", "macroquad", "pygame", "godot"],
        "dep_files": ["Cargo.toml", "requirements.txt"],
    },
    "embedded": {
        "files": ["platformio.ini", "*.ino"],
        "dirs": ["firmware", "drivers", "hal", "bsp"],
        "deps": ["esphome", "micropython", "circuitpython", "embassy"],
        "dep_files": ["requirements.txt", "Cargo.toml"],
    },
    "legal": {
        "files": ["LICENSE", "COPYING", "privacy-policy*", "terms-of-service*"],
        "deps": [],
        "dep_files": [],
        "min_signals": 1,
    },
    # Note: requirements-eng and research don't auto-detect — they're
    # invoked by other roles or manually. They can be added via config_add.
}


def _check_file_patterns(project_dir: Path, patterns: List[str]) -> List[str]:
    """Check which file patterns exist in the project directory."""
    found = []
    for pattern in patterns:
        if "*" in pattern or "?" in pattern:
            matches = list(project_dir.glob(pattern))
            if matches:
                found.append(pattern)
        else:
            if (project_dir / pattern).exists():
                found.append(pattern)
    return found


def _check_dir_patterns(project_dir: Path, patterns: List[str]) -> List[str]:
    """Check which directory patterns exist in the project."""
    found = []
    for pattern in patterns:
        if "*" in pattern or "?" in pattern:
            matches = list(project_dir.glob(pattern))
            if any(m.is_dir() for m in matches):
                found.append(pattern)
        else:
            if (project_dir / pattern).is_dir():
                found.append(pattern)
    return found


def _check_deps(
    project_dir: Path,
    dep_names: List[str],
    dep_files: List[str],
) -> List[str]:
    """Check which dependencies are present in dependency files."""
    if not dep_names or not dep_files:
        return []

    found = []
    for dep_file in dep_files:
        filepath = project_dir / dep_file
        if not filepath.is_file():
            continue

        content = filepath.read_text(errors="ignore")

        if dep_file == "package.json":
            try:
                pkg = json.loads(content)
                all_deps = {}
                all_deps.update(pkg.get("dependencies", {}))
                all_deps.update(pkg.get("devDependencies", {}))
                for dep in dep_names:
                    if dep in all_deps:
                        found.append(dep)
            except (json.JSONDecodeError, TypeError):
                pass
        else:
            # For requirements.txt, pyproject.toml, Gemfile, etc.
            # Simple string matching is sufficient
            content_lower = content.lower()
            for dep in dep_names:
                if dep.lower() in content_lower:
                    found.append(dep)

    return found


def _score_confidence(signals_found: int, total_possible: int) -> str:
    """Score confidence based on signal match ratio."""
    if total_possible == 0:
        return "low"
    ratio = signals_found / total_possible
    if ratio >= 0.4 or signals_found >= 4:
        return "high"
    elif ratio >= 0.2 or signals_found >= 2:
        return "medium"
    return "low"


def detect_roles(
    project_dir: Path,
    config_roles: Optional[List[str]] = None,
    config_add: Optional[List[str]] = None,
    config_exclude: Optional[List[str]] = None,
    max_roles: int = 4,
) -> List[Dict[str, Any]]:
    """Detect applicable roles from project directory signals.

    Args:
        project_dir: Path to the project root
        config_roles: If set, overrides auto-detection entirely
        config_add: Roles to add to auto-detected list
        config_exclude: Roles to remove from auto-detected list
        max_roles: Maximum number of roles to return

    Returns:
        List of dicts: [{"name": "backend", "confidence": "high", "signals": [...]}]
        Sorted by confidence (descending), then by signal count.
    """
    # If explicit roles configured, skip detection
    if config_roles is not None:
        return [
            {"name": role, "confidence": "high", "signals": ["config"]}
            for role in config_roles
        ]

    detected = []

    for role_name, signals_config in ROLE_SIGNALS.items():
        all_signals_found = []

        # Check files
        file_patterns = signals_config.get("files", [])
        all_signals_found.extend(_check_file_patterns(project_dir, file_patterns))

        # Check directories
        dir_patterns = signals_config.get("dirs", [])
        all_signals_found.extend(_check_dir_patterns(project_dir, dir_patterns))

        # Check dependencies
        dep_names = signals_config.get("deps", [])
        dep_files = signals_config.get("dep_files", [])
        all_signals_found.extend(_check_deps(project_dir, dep_names, dep_files))

        if not all_signals_found:
            continue

        min_signals = signals_config.get("min_signals", 1)
        if len(all_signals_found) < min_signals:
            continue

        total_possible = (
            len(file_patterns) + len(dir_patterns) + len(dep_names)
        )
        confidence = _score_confidence(len(all_signals_found), total_possible)

        detected.append({
            "name": role_name,
            "confidence": confidence,
            "signals": all_signals_found,
        })

    # Apply config_add
    if config_add:
        detected_names = {r["name"] for r in detected}
        for role in config_add:
            if role not in detected_names:
                detected.append({
                    "name": role,
                    "confidence": "medium",
                    "signals": ["config_add"],
                })

    # Apply config_exclude
    if config_exclude:
        detected = [r for r in detected if r["name"] not in config_exclude]

    # Sort: confidence rank (high > medium > low), then signal count
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    detected.sort(
        key=lambda r: (confidence_order.get(r["confidence"], 3), -len(r["signals"]))
    )

    # Cap at max_roles
    return detected[:max_roles]


def _parse_role_md(role_path: Path) -> str:
    """Extract the body (after YAML frontmatter) from a role.md file."""
    content = role_path.read_text()
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return content.strip()


def load_role_context(
    role_names: List[str],
    roles_dir: Optional[Path] = None,
    max_roles: int = 4,
) -> str:
    """Load role preamble text for injection into session context.

    Args:
        role_names: List of role names to load
        roles_dir: Path to roles/ directory
        max_roles: Maximum roles to include in context

    Returns:
        Combined context string with role advisories + manager principles
    """
    if not role_names:
        return ""

    if roles_dir is None:
        roles_dir = Path(__file__).resolve().parent

    # Cap roles
    active_roles = role_names[:max_roles]

    parts = [f"ACTIVE ROLES: {', '.join(active_roles)}"]

    # Load manager principles if available
    manager_path = roles_dir / "manager.md"
    if manager_path.is_file():
        manager_body = _parse_role_md(manager_path)
        if manager_body:
            parts.append("")
            parts.append(manager_body)

    # Load each role's advisory + synthesized knowledge
    for role_name in active_roles:
        role_path = roles_dir / role_name / "role.md"
        if role_path.is_file():
            body = _parse_role_md(role_path)
            if body:
                parts.append("")
                parts.append(body)

        # Load synthesized knowledge (learned from repos)
        synthesis_path = roles_dir / role_name / "knowledge" / "_synthesis.md"
        if synthesis_path.is_file():
            synthesis = _parse_role_md(synthesis_path)
            if synthesis:
                # Cap at ~2000 chars (~500 tokens) per role to keep context lean
                if len(synthesis) > 2000:
                    synthesis = synthesis[:2000] + "\n\n[... truncated — full knowledge in _synthesis.md]"
                parts.append("")
                parts.append(f"## {role_name.upper()} — Learned Knowledge")
                parts.append(synthesis)

    return "\n".join(parts)
