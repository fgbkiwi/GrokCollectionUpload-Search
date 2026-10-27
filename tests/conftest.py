import os
import tempfile

os.environ.setdefault("SARAH_LOG_DIR", tempfile.mkdtemp(prefix="sarah_logs_teste_"))
os.environ.setdefault("SARAH_LOG_CONSOLE", "0")
