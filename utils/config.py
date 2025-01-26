import json
import os
import sys

# 动态添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


def load_config(config_file="config.json"):
    """加载公共配置"""
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading config file: {e}")
        return {}


def get_email_credentials():
    """从环境变量中获取邮箱凭据"""
    return {
        "126": {
            "username": os.getenv("EMAIL_126_USERNAME"),
            "password": os.getenv("EMAIL_126_PASSWORD"),
            "smtp_server": os.getenv("EMAIL_126_SMTP_SERVER"),
            "smtp_port": int(os.getenv("EMAIL_126_SMTP_PORT")),
            "imap_server": os.getenv("EMAIL_126_IMAP_SERVER"),
            "imap_port": int(os.getenv("EMAIL_126_IMAP_PORT")),
        },
        "qq": {
            "username": os.getenv("EMAIL_QQ_USERNAME"),
            "password": os.getenv("EMAIL_QQ_PASSWORD"),
            "smtp_server": os.getenv("EMAIL_QQ_SMTP_SERVER"),
            "smtp_port": int(os.getenv("EMAIL_QQ_SMTP_PORT")),
            "imap_server": os.getenv("EMAIL_QQ_IMAP_SERVER"),
            "imap_port": int(os.getenv("EMAIL_QQ_IMAP_PORT")),
        },
    }
