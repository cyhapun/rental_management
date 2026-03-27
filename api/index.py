import os
import sys

# Lấy đường dẫn thư mục hiện tại (thư mục api)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Lấy đường dẫn thư mục cha (thư mục gốc chứa main.py)
parent_dir = os.path.dirname(current_dir)

# Thêm thư mục gốc vào hệ thống để Python tìm thấy main.py
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from main import app  # Import trực tiếp từ main.py
from mangum import Mangum

# Handler cho Vercel
handler = Mangum(app)