import imaplib
import logging
import os
from email.header import decode_header

import pyzmail

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# 从本地txt文件读取邮箱配置
def read_config(file_path="./qqconfig.txt"):
    config = {}
    try:
        with open(file_path, "r") as f:
            for line in f:
                key, value = line.strip().split("=")
                config[key] = value
        logging.info("配置文件读取成功")
    except Exception as e:
        logging.error("读取配置文件失败: %s", e)
    return config


# 登录 QQ 邮箱
def login_to_email(username, password):
    imap_server = "imap.qq.com"
    try:
        # 连接到 IMAP 服务器
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(username, password)
        logging.info("登录成功")
        return mail
    except Exception as e:
        logging.error("登录失败: %s", e)
        return None


# 解码邮件头
def decode_header_value(header_value):
    decoded_parts = decode_header(header_value)
    result = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(encoding or "utf-8")
        else:
            result += part
    return result


# 保存邮件正文到文件
def save_email_body_to_file(email_id, body, format="txt"):
    directory = "emails"
    os.makedirs(directory, exist_ok=True)  # 创建存储邮件的目录
    file_extension = format if format == "html" else "txt"
    file_path = os.path.join(directory, f"email_{email_id.decode()}.{file_extension}")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(body)
        logging.info("邮件正文已保存到文件: %s", file_path)
    except Exception as e:
        logging.error("保存邮件正文到文件失败: %s", e)


# 获取所有邮件
def fetch_emails(mail):
    try:
        # 选择收件箱
        mail.select("INBOX")
        # 搜索所有邮件
        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()
        logging.info("共找到 %d 封邮件", len(email_ids))

        for email_id in email_ids:
            # 获取邮件数据
            res, msg_data = mail.fetch(email_id, "(RFC822)")
            for response in msg_data:
                if isinstance(response, tuple):
                    logging.info("处理邮件 ID: %s", email_id.decode())
                    raw_email = response[1]

                    # 检查是否为字节类型
                    if not isinstance(raw_email, bytes):
                        logging.warning(
                            "警告: 邮件 ID %s 数据格式异常，跳过处理", email_id.decode()
                        )
                        continue

                    # 使用 pyzmail 解析邮件
                    try:
                        msg = pyzmail.PyzMessage.factory(raw_email)
                    except Exception as e:
                        logging.error("解析邮件失败: %s", e)
                        # 保存原始邮件到文件以供分析
                        with open(f"email_{email_id.decode()}.eml", "wb") as f:
                            f.write(raw_email)
                        continue

                    # 解析邮件主题
                    subject = msg.get_subject()
                    logging.info("邮件主题: %s", subject if subject else "(无主题)")

                    # 解析发件人
                    from_ = msg.get_addresses("from")
                    logging.info("发件人: %s", from_)

                    # 获取邮件正文
                    if msg.text_part:
                        try:
                            body = msg.text_part.get_payload().decode(
                                msg.text_part.charset or "utf-8", errors="ignore"
                            )
                            logging.info(
                                "邮件正文:\n%s...", body[:200]
                            )  # 只打印部分正文
                            save_email_body_to_file(email_id, body)  # 保存正文到文件
                        except Exception as e:
                            logging.error("邮件正文解码失败: %s", e)
                    elif msg.html_part:
                        try:
                            body = msg.html_part.get_payload().decode(
                                msg.html_part.charset or "utf-8", errors="ignore"
                            )
                            logging.info(
                                "邮件正文（HTML）:\n%s...", body[:200]
                            )  # 只打印部分正文
                            save_email_body_to_file(
                                email_id, body, format="html"
                            )  # 保存HTML正文到文件
                        except Exception as e:
                            logging.error("HTML正文解码失败: %s", e)
                    else:
                        logging.warning("邮件 ID %s 没有正文内容", email_id.decode())

        mail.close()
        mail.logout()

    except Exception as e:
        logging.error("获取邮件失败: %s", e)


# 主程序
if __name__ == "__main__":
    config = read_config()
    email = config.get("email")
    password = config.get("password")

    if email and password:
        mail = login_to_email(email, password)
        if mail:
            fetch_emails(mail)
    else:
        logging.error("缺少邮箱账号或密码，程序退出")
