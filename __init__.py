# 可选的包级别初始化
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 可以添加一些全局配置或导入
# 例如：
# from utils.config import load_config
# CONFIG = load_config()
