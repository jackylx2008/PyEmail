import imaplib
import logging
import sqlite3
import uuid
from datetime import datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime

import pyzmail

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# 数据库文件路径
DB_FILE = "raw_email.db"


# 注册 datetime 适配器
def adapt_datetime(dt):
    """Convert datetime to string for SQLite storage."""
    return dt.isoformat() if dt else None


def convert_datetime(s):
    """Convert string from SQLite to datetime."""
    return datetime.fromisoformat(s) if s else None


sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("TIMESTAMP", convert_datetime)


# 初始化 SQLite 数据库
def init_database():
    """初始化 SQLite 数据库"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS emails (
            id TEXT PRIMARY KEY,
            uid TEXT UNIQUE NOT NULL,
            subject TEXT,
            sender TEXT,
            body TEXT,
            format TEXT,
            sent_at TIMESTAMP,
            saved_at TIMESTAMP
        )
    """
    )
    conn.commit()
    conn.close()
    logging.info("数据库初始化完成")


class EmailClient:
    """邮箱客户端"""

    def __init__(self, username, password, imap_server="imap.qq.com", port=993):
        self.username = username
        self.password = password
        self.imap_server = imap_server
        self.port = port
        self.mail = None

    def login(self):
        """登录邮箱"""
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server, self.port)
            self.mail.login(self.username, self.password)
            logging.info("邮箱登录成功")
        except imaplib.IMAP4.error:
            logging.error("邮箱登录失败，用户名或密码可能错误")
        except Exception as e:
            logging.error("登录邮箱时发生错误: %s", e)

    @staticmethod
    def decode_header_value(header_value):
        """解码邮件头"""
        decoded_parts = decode_header(header_value)
        return "".join(
            part.decode(encoding or "utf-8") if isinstance(part, bytes) else part
            for part, encoding in decoded_parts
        )

    @staticmethod
    def save_email_to_db(uid, subject, sender, body, is_html, sent_at):
        """保存邮件到 SQLite 数据库"""
        conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()

        email_id = str(uuid.uuid4())
        format_type = "html" if is_html else "text"
        saved_at = datetime.now()

        try:
            cursor.execute(
                """
                INSERT INTO emails (id, uid, subject, sender, body, format, sent_at, saved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (email_id, uid, subject, sender, body, format_type, sent_at, saved_at),
            )
            conn.commit()
            logging.info("邮件 UID %s 已保存到数据库，ID: %s", uid, email_id)
        except sqlite3.IntegrityError:
            logging.info("邮件 UID %s 已存在，跳过保存", uid)
        except Exception as e:
            logging.error("保存邮件到数据库失败: %s", e)
        finally:
            conn.close()

    def fetch_emails(self):
        """获取所有邮件并保存到数据库"""
        if not self.mail:
            logging.error("尚未登录邮箱，无法获取邮件")
            return

        try:
            self.mail.select("INBOX")
            _, messages = self.mail.search(None, "ALL")
            email_ids = messages[0].split()
            logging.info("共找到 %d 封邮件", len(email_ids))

            conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
            cursor = conn.cursor()

            for email_id in email_ids:
                # 使用 UID FETCH 确保获取唯一标识符
                uid_res, uid_data = self.mail.fetch(email_id, "(UID)")
                uid = uid_data[0].decode().split()[-1]

                # 检查 UID 是否已存在
                cursor.execute("SELECT 1 FROM emails WHERE uid = ?", (uid,))
                if cursor.fetchone():
                    logging.info("邮件 UID %s 已存在，跳过处理", uid)
                    continue

                # 获取邮件数据
                res, msg_data = self.mail.fetch(email_id, "(RFC822)")
                for response in msg_data:
                    if isinstance(response, tuple):
                        raw_email = response[1]
                        if not isinstance(raw_email, bytes):
                            logging.warning(
                                "邮件 ID %s 数据格式异常，跳过处理", email_id.decode()
                            )
                            continue

                        try:
                            msg = pyzmail.PyzMessage.factory(raw_email)
                        except Exception as e:
                            logging.error(
                                "解析邮件 ID %s 失败: %s", email_id.decode(), e
                            )
                            continue

                        subject = self.decode_header_value(
                            msg.get_subject() or "(无主题)"
                        )
                        from_ = msg.get_addresses("from")
                        sender = from_[0][1] if from_ else "(未知发件人)"

                        sent_at = None
                        try:
                            if msg.get("date"):
                                sent_at = parsedate_to_datetime(msg.get("date"))
                        except Exception as e:
                            logging.warning(
                                "邮件 ID %s 的发件时间解析失败: %s",
                                email_id.decode(),
                                e,
                            )

                        body = None
                        is_html = False

                        if msg.text_part:
                            body = msg.text_part.get_payload().decode(
                                msg.text_part.charset or "utf-8", errors="ignore"
                            )
                        elif msg.html_part:
                            body = msg.html_part.get_payload().decode(
                                msg.html_part.charset or "utf-8", errors="ignore"
                            )
                            is_html = True

                        if body:
                            self.save_email_to_db(
                                uid, subject, sender, body, is_html, sent_at
                            )
                        else:
                            logging.warning(
                                "邮件 ID %s 没有正文内容", email_id.decode()
                            )

            conn.close()
            self.mail.close()
            self.mail.logout()

        except Exception as e:
            logging.error("获取邮件失败: %s", e)


# 从本地txt文件读取邮箱配置
def read_config(file_path="./qqconfig.txt"):
    """读取邮箱配置文件"""
    config = {}
    try:
        with open(file_path, "r") as f:
            for line in f:
                key, value = line.strip().split("=")
                config[key] = value
        logging.info("配置文件读取成功")
    except FileNotFoundError:
        logging.error("配置文件未找到: %s", file_path)
    except ValueError:
        logging.error("配置文件格式错误，应为 key=value")
    except Exception as e:
        logging.error("读取配置文件失败: %s", e)
    return config


if __name__ == "__main__":
    init_database()
    config = read_config()
    email = config.get("email")
    password = config.get("password")

    if email and password:
        client = EmailClient(email, password)
        client.login()
        client.fetch_emails()
    else:
        logging.error("缺少邮箱账号或密码，程序退出")
