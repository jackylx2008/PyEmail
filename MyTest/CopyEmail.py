import configparser
import email
import imaplib
import logging
import smtplib
from email.header import decode_header
from email.mime.text import MIMEText

import chardet

# 配置日志
logging.basicConfig(
    level=logging.INFO,  # 设置日志级别
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler("process_emails.log", encoding="utf-8"),  # 输出到文件
    ],
)


class EmailForwarder:
    def __init__(self, config_file, keyword):
        self.config_file = config_file
        self.keyword = keyword  # 搜索关键词
        self.conf = self.load_config()
        self.conn = None

    # 从配置文件加载配置
    def load_config(self):
        try:
            config = configparser.ConfigParser()
            config.read(self.config_file, encoding="utf-8")
            conf = {
                "imap_server": config.get("email", "imap_server"),
                "imap_ssl_port": config.getint("email", "imap_ssl_port"),
                "imap_user": config.get("email", "imap_user"),
                "imap_pwd": config.get("email", "imap_pwd"),
                "smtp_server": config.get("email", "smtp_server"),
                "smtp_ssl_port": config.getint("email", "smtp_ssl_port"),
                "smtp_user": config.get("email", "smtp_user"),
                "smtp_pwd": config.get("email", "smtp_pwd"),
                "target_email": config.get("email", "target_email"),
            }
            logging.info("成功加载配置文件")
            return conf
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
            raise

    # 连接到IMAP服务器
    def connect_to_imap(self):
        try:
            self.conn = imaplib.IMAP4_SSL(
                self.conf["imap_server"], self.conf["imap_ssl_port"]
            )
            self.conn.login(self.conf["imap_user"], self.conf["imap_pwd"])
            logging.info("成功连接到IMAP服务器")

            # 发送IMAP ID命令（126邮箱可能需要）
            imap_id = ("name", "YourAppName", "version", "1.0", "vendor", "YourCompany")
            typ, data = self.conn.xatom("ID", '("' + '" "'.join(imap_id) + '")')
            logging.info(f"IMAP ID 响应: typ={typ}, data={data}")

            # 列出所有文件夹
            # status, folders = self.conn.list()
            # if status == "OK":
            #     for folder in folders:
            #         logging.info(f"文件夹: {folder.decode()}")

            # 选择收件箱
            result, message = self.conn.select("INBOX")  # 确保选择的是 INBOX
            if result == "OK":
                logging.info(f"成功选择收件箱，共有 {message[0].decode()} 封邮件")

                # 获取所有邮件的 ID
                status, email_ids = self.conn.search(None, "ALL")
                if status == "OK":
                    email_ids = email_ids[0].split()
                    logging.info(f"找到 {len(email_ids)} 封邮件")
                    for email_id in email_ids:
                        # 获取每封邮件的标题
                        status, msg_data = self.conn.fetch(email_id, "(RFC822)")
                        if status == "OK":
                            email_msg = email.message_from_bytes(msg_data[0][1])
                            subject, encoding = decode_header(email_msg["Subject"])[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(
                                    encoding if encoding else "utf-8"
                                )
                            logging.info(
                                f"邮件 ID: {email_id.decode()}, 标题: {subject}"
                            )
                        else:
                            logging.warning(f"无法获取邮件内容: {email_id}")
                else:
                    logging.warning("未找到邮件")
            else:
                raise Exception("无法选择收件箱")
        except Exception as e:
            logging.error(f"连接IMAP服务器失败: {e}")
            raise

    # 检测并解码邮件内容
    def decode_email_body(self, body):
        try:
            # 使用 chardet 检测编码
            detected = chardet.detect(body)
            encoding = detected.get("encoding", "utf-8")
            logging.info(f"检测到邮件内容编码: {encoding}")

            # 尝试解码
            return body.decode(
                encoding, errors="replace"
            )  # 使用 errors='replace' 替换无法解码的字符
        except Exception as e:
            logging.warning(f"解码邮件内容失败: {e}")
            # 如果检测失败，尝试使用常见编码
            for enc in ["gbk", "iso-8859-1", "utf-8", "ascii"]:
                try:
                    return body.decode(enc, errors="replace")
                except Exception:
                    continue
            raise ValueError("无法解码邮件内容")

    # 获取邮件内容
    def fetch_email(self, email_id):
        try:
            status, msg_data = self.conn.fetch(email_id, "(RFC822)")
            if status == "OK":
                email_msg = email.message_from_bytes(msg_data[0][1])
                subject, encoding = decode_header(email_msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")
                logging.info(f"成功获取邮件: {subject}")

                # 提取邮件正文
                body = None
                if email_msg.is_multipart():
                    # 如果是多部分邮件，遍历所有部分
                    for part in email_msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain" or content_type == "text/html":
                            body = part.get_payload(decode=True)
                            if body:
                                try:
                                    body = self.decode_email_body(body)
                                except ValueError as e:
                                    logging.error(f"无法解码邮件内容: {e}")
                                    body = None
                            break
                else:
                    # 如果是单部分邮件，直接提取内容
                    body = email_msg.get_payload(decode=True)
                    if body:
                        try:
                            body = self.decode_email_body(body)
                        except ValueError as e:
                            logging.error(f"无法解码邮件内容: {e}")
                            body = None

                if body:
                    email_msg._payload = body  # 将解码后的内容保存到邮件对象中
                else:
                    logging.warning(f"邮件内容为空: {email_id}")

                return email_msg
            else:
                logging.warning(f"无法获取邮件内容: {email_id}")
                return None
        except Exception as e:
            logging.error(f"获取邮件内容失败: {e}")
            raise

    # 发送邮件到目标邮箱
    def send_to_target(self, email_msg):
        try:
            # 检查邮件内容是否为空
            body = email_msg.get_payload(decode=True)
            if not body:
                logging.warning(f"邮件内容为空，跳过发送: {email_msg['Subject']}")
                return

            # 创建 MIMEText 对象
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = email_msg["Subject"]
            msg["From"] = self.conf["imap_user"]
            msg["To"] = self.conf["target_email"]

            # 发送邮件
            with smtplib.SMTP_SSL(
                self.conf["smtp_server"], self.conf["smtp_ssl_port"]
            ) as server:
                server.login(self.conf["smtp_user"], self.conf["smtp_pwd"])
                server.sendmail(
                    self.conf["imap_user"], self.conf["target_email"], msg.as_string()
                )
                logging.info(f"已发送邮件: {email_msg['Subject']}")
        except Exception as e:
            logging.error(f"发送邮件失败: {e}")
            raise

    # 主逻辑
    def run(self):
        try:
            # 连接到IMAP服务器
            self.connect_to_imap()

            # 搜索符合条件的邮件
            email_ids = self.search_emails()

            # 遍历邮件并发送到目标邮箱
            for email_id in email_ids:
                email_msg = self.fetch_email(email_id)
                if email_msg:
                    self.send_to_target(email_msg)

        except Exception as e:
            logging.error(f"程序运行出错: {e}")
        finally:
            # 关闭连接
            if self.conn:
                self.conn.logout()
                logging.info("已断开与IMAP服务器的连接")


# 运行程序
if __name__ == "__main__":
    # 从命令行参数或直接传入关键词
    keyword = "工商"  # 可以修改为从命令行参数获取
    forwarder = EmailForwarder("config.ini", keyword)
    forwarder.run()
