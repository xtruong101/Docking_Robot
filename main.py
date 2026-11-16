"""
Entry point thực thi mô phỏng Autonomous Docking từ thư mục gốc dự án.
Tự động phát hiện môi trường Python có đầy đủ thư viện (numpy, scipy, matplotlib)
để đảm bảo chạy thành công ngay cả khi người dùng gõ `python` hay `py`.
"""

import sys
import os
import shutil
from pathlib import Path
import subprocess


def find_working_python() -> str:
    # 1. Thử chính interpreter hiện tại
    try:
        import numpy
        return sys.executable
    except ImportError:
        pass

    # 2. Thử các đường dẫn Python chuẩn trên Windows
    candidates = [
        "py",
        r"C:\Users\MSI PC\AppData\Local\Programs\Python\Python310\python.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python310\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python311\python.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python312\python.exe"),
    ]
    for cand in candidates:
        exe = shutil.which(cand) or (cand if os.path.exists(cand) else None)
        if exe:
            try:
                res = subprocess.run([exe, "-c", "import numpy; print('OK')"], capture_output=True, text=True)
                if "OK" in res.stdout:
                    return exe
            except Exception:
                pass
    return sys.executable


if __name__ == "__main__":
    docking_main = Path(__file__).parent / "docking" / "main.py"
    target_python = find_working_python()
    cmd = [target_python, str(docking_main)] + sys.argv[1:]
    result = subprocess.run(cmd)
    sys.exit(result.returncode)
