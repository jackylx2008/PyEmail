import configparser
import email
import imaplib
import logging
from email.header import decode_header
from email.mime.text import MIMEText

# 配置日志
logging.basicConfig(
    level=logging.INFO,  # 设置日志级别
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler("imap_client_check.log", encoding="utf-8"),  # 输出到文件
    ],
)


def load_config(config_file):
    """从配置文件加载 IMAP 配置"""
    try:
        config = configparser.ConfigParser()
        config.read(config_file, encoding="utf-8")
        conf = {
            "imap_server": config.get("email", "imap_server"),
            "imap_ssl_port": config.getint("email", "imap_ssl_port"),
            "imap_user": config.get("email", "imap_user"),
            "imap_pwd": config.get("email", "imap_pwd"),
        }
        logging.info("成功加载配置文件")
        return conf
    except Exception as e:
        logging.error(f"加载配置文件失败: {e}")
        raise


def check_imap_client(config):
    """检查 IMAP 客户端的配置"""
    try:
        # 连接到 IMAP 服务器
        conn = imaplib.IMAP4_SSL(config["imap_server"], config["imap_ssl_port"])
        conn.login(config["imap_user"], config["imap_pwd"])
        logging.info("成功连接到 IMAP 服务器")

        # 发送IMAP ID命令（126邮箱可能需要）
        imap_id = ("name", "YourAppName", "version", "1.0", "vendor", "YourCompany")
        typ, data = conn.xatom("ID", '("' + '" "'.join(imap_id) + '")')
        logging.info(f"IMAP ID 响应: typ={typ}, data={data}")

        # 检查 IMAP 服务器的能力
        status, capabilities = conn.capability()
        if status == "OK":
            logging.info(f"IMAP 服务器支持的功能: {capabilities}")
        else:
            logging.warning("无法获取 IMAP 服务器的能力")

        # 检查 IMAP 服务器的分页设置
        check_imap_paging(conn)

        # 关闭连接
        conn.logout()
        logging.info("已断开与 IMAP 服务器的连接")

    except Exception as e:
        logging.error(f"检查 IMAP 客户端配置失败: {e}")


def check_imap_paging(conn):
    """检查 IMAP 服务器的分页设置"""
    try:
        # 选择一个邮箱（例如收件箱）
        status, _ = conn.select("INBOX")
        if status != "OK":
            logging.error("无法选择邮箱")
            return

        # 测试分页功能：获取前 10 封邮件
        status, msg_data = conn.fetch("1:10", "(RFC822)")
        if status == "OK" and msg_data:
            print(msg_data)
            logging.info("IMAP 服务器支持分页功能：成功获取前 10 封邮件")
        else:
            logging.warning("IMAP 服务器不支持分页功能：无法获取前 10 封邮件")

        # 测试分页功能：获取第 21 到 30 封邮件
        status, msg_data = conn.fetch("21:30", "(RFC822)")
        if status == "OK" and msg_data:
            logging.info("IMAP 服务器支持分页功能：成功获取第 21 到 30 封邮件")
            print(msg_data)
            # 解析邮件内容
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    email_msg = email.message_from_bytes(response_part[1])
                    # 解析邮件标题
                    subject = email_msg.get("Subject", "无标题")
                    if subject:
                        subject, encoding = decode_header(subject)[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        logging.info(f"邮件标题: {subject}")
                    else:
                        logging.info("邮件标题: 无标题")
        else:
            logging.warning("IMAP 服务器不支持分页功能：无法获取第 21 到 30 封邮件")

    except Exception as e:
        logging.error(f"检查 IMAP 服务器分页设置失败: {e}")


# 主逻辑
if __name__ == "__main__":
    # 加载配置文件
    config_file = "config.ini"  # 配置文件路径
    config = load_config(config_file)

    # 检查 IMAP 客户端配置
    check_imap_client(config)
