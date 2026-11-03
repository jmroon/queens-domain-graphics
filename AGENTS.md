# Repository guidance

For game updates, compatibility investigations, or release validation, use
[$queens-domain-compatibility](.agents/skills/queens-domain-compatibility/SKILL.md).
Build commands and fragile implementation details are in [docs/MAINTENANCE.md](docs/MAINTENANCE.md).

Keep the user-facing README/install notes concise. Preserve tested behavior and
existing settings, including the legacy Enhanced alias for Modern. Keep extracted
originals, tools, game saves, preferences, logs, and machine-specific paths out of
Git. Record untested behavior honestly; a successful source build does not prove
in-game compatibility. No polling timer or per-frame scan should be introduced.
