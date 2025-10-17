import os
from pathlib import Path


def load_env(env_path: str = ".env") -> None:
	path = Path(env_path)
	if not path.exists():
		return

	for line in path.read_text(encoding="utf-8").splitlines():
		line = line.strip()
		if not line or line.startswith("#"):
			continue

		if "=" not in line:
			continue

		key, value = line.split("=", 1)
		key = key.strip()
		if not key:
			continue

		value = value.strip().strip("'").strip('"')
		if key not in os.environ:
			os.environ[key] = value
