from _bootstrap import ensure_repo_root

ensure_repo_root()

import api
import kg
import llm
import logger
import rag
import router


print("Core module imports successful.")
print(f"API status snapshot: {api.get_status()}")
