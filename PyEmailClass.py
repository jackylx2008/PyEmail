import imaplib
import logging
import os
from email.header import decode_header

import pyzmail

# 配置日志
logging.basicConfig(
    level=logging.INFO,  # 设置日志级别
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        # logging.FileHandler("process_emails.log", encoding="utf-8"),  # 输出到文件
    ],
)


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
    def save_email_body(email_id, body, is_html=False):
        """保存邮件正文到文件"""
        directory = "emails"
        os.makedirs(directory, exist_ok=True)
        file_extension = "html" if is_html else "txt"
        file_path = os.path.join(
            directory, f"email_{email_id.decode()}.{file_extension}"
        )
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(body)
            logging.info("邮件正文已保存到文件: %s", file_path)
        except Exception as e:
            logging.error("保存邮件正文失败: %s", e)

    def fetch_emails(self):
        """获取所有邮件并保存正文"""
        if not self.mail:
            logging.error("尚未登录邮箱，无法获取邮件")
            return

        try:
            self.mail.select("INBOX")
            _, messages = self.mail.search(None, "ALL")
            email_ids = messages[0].split()
            logging.info("共找到 %d 封邮件", len(email_ids))

            for email_id in email_ids:
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
                        logging.info("邮件主题: %s", subject)

                        from_ = msg.get_addresses("from")
                        logging.info("发件人: %s", from_)

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
                            logging.info("邮件正文（前200字符）:\n%s", body[:200])
                            self.save_email_body(email_id, body, is_html)
                        else:
                            logging.warning(
                                "邮件 ID %s 没有正文内容", email_id.decode()
                            )

            self.mail.close()
            self.mail.logout()

        except Exception as e:
            logging.error("获取邮件失败: %s", e)


# 主程序
if __name__ == "__main__":
    config = read_config()
    email = config.get("email")
    password = config.get("password")

    if email and password:
        client = EmailClient(email, password)
        client.login()
        client.fetch_emails()
    else:
        logging.error("缺少邮箱账号或密码，程序退出")
