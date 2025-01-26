import logging
import os
import tempfile
import zipfile
from email import policy
from email.parser import BytesParser

import html2text  # 用于将 HTML 转换为纯文本


# 配置日志
def setup_logging():
    # 创建一个自定义的日志处理器，确保使用 UTF-8 编码
    class UTF8FileHandler(logging.FileHandler):
        def __init__(self, filename, mode="a", encoding="utf-8", delay=False):
            super().__init__(filename, mode, encoding, delay)

        def emit(self, record):
            try:
                msg = self.format(record)
                stream = self.stream
                stream.write(msg + self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,  # 日志级别
        format="%(asctime)s - %(levelname)s - %(message)s",  # 日志格式
        handlers=[
            UTF8FileHandler(
                "eml_processor.log", encoding="utf-8"
            ),  # 输出到文件，使用 UTF-8 编码
            logging.StreamHandler(),  # 输出到控制台
        ],
    )


def extract_eml_from_zip(zip_path, extract_to):
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for file_info in zip_ref.infolist():
                # 尝试使用 cp437 或 gbk 解码文件名
                try:
                    file_name = file_info.filename.encode("cp437").decode("gbk")
                except UnicodeDecodeError:
                    file_name = file_info.filename  # 如果解码失败，使用原始文件名

                # 构建目标文件路径
                target_path = os.path.join(extract_to, file_name)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)

                # 解压文件
                with zip_ref.open(file_info) as source, open(
                    target_path, "wb"
                ) as target:
                    target.write(source.read())

        logging.info(f"成功解压ZIP文件: {os.path.basename(zip_path)}")
    except zipfile.BadZipFile:
        logging.error(f"错误: {os.path.basename(zip_path)} 不是一个有效的ZIP文件。")
    except FileNotFoundError:
        logging.error(f"错误: ZIP文件 {os.path.basename(zip_path)} 未找到。")
    except Exception as e:
        logging.error(f"解压ZIP文件 {os.path.basename(zip_path)} 时发生未知错误: {e}")


def parse_eml_file(eml_path, max_lines=20):
    try:
        with open(eml_path, "rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)

        subject = msg["subject"]
        date = msg["date"]

        # 提取邮件内容
        content = ""
        if msg.is_multipart():
            # 如果是多部分邮件，遍历所有部分
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type in ["text/plain", "text/html"]:
                    # 提取纯文本或HTML内容
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            # 如果是 HTML 内容，转换为纯文本
                            if content_type == "text/html":
                                # 获取邮件内容的编码
                                charset = part.get_content_charset() or "utf-8"
                                html_content = payload.decode(charset, errors="ignore")
                                content = html2text.html2text(
                                    html_content
                                )  # 转换为纯文本
                            else:
                                charset = part.get_content_charset() or "utf-8"
                                content = payload.decode(charset, errors="ignore")
                            break
                    except Exception as e:
                        logging.warning(
                            f"无法解码 {eml_path} 的 {content_type} 部分: {e}"
                        )
        else:
            # 如果是单部分邮件，直接提取内容
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    # 如果是 HTML 内容，转换为纯文本
                    if msg.get_content_type() == "text/html":
                        charset = msg.get_content_charset() or "utf-8"
                        html_content = payload.decode(charset, errors="ignore")
                        content = html2text.html2text(html_content)  # 转换为纯文本
                    else:
                        charset = msg.get_content_charset() or "utf-8"
                        content = payload.decode(charset, errors="ignore")
            except Exception as e:
                logging.warning(f"无法解码 {eml_path} 的内容: {e}")

        # 获取前 max_lines 行
        content_lines = content.splitlines()[:max_lines]
        content_preview = "\n".join(content_lines)

        return date, subject, content_preview
    except Exception as e:
        logging.error(f"解析 {os.path.basename(eml_path)} 时发生错误: {e}")
        return None, None, None


def process_eml_folder(eml_folder, zip_path, max_lines=20):
    try:
        for root, _, files in os.walk(eml_folder):
            for file in files:
                if file.endswith(".eml"):
                    eml_path = os.path.join(root, file)
                    date, subject, content_preview = parse_eml_file(eml_path, max_lines)
                    if date and subject:
                        # 合并ZIP文件和EML文件的信息到一行
                        logging.info(
                            f"ZIP文件: {os.path.basename(zip_path)}, EML文件: {file}"
                        )
                        # Date 和 Subject 独立一行显示
                        logging.info(f"Date: {date}")
                        logging.info(f"Subject: {subject}")
                        # 显示邮件内容的前 max_lines 行
                        if content_preview:
                            logging.info(f"邮件内容前{max_lines}行:")
                            logging.info(content_preview)
                        else:
                            logging.info(f"邮件内容前{max_lines}行: 无内容或无法解析")
                        logging.info("-" * 40)  # 分隔线
    except Exception as e:
        logging.error(f"处理文件夹 {eml_folder} 时发生错误: {e}")


def process_all_zips_in_folder(folder_path, max_lines=20):
    try:
        # 遍历文件夹中的所有ZIP文件
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.endswith(".zip"):
                    zip_path = os.path.join(root, file)
                    logging.info(f"正在处理ZIP文件: {os.path.basename(zip_path)}")

                    # 创建临时文件夹
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # 解压ZIP文件到临时文件夹
                        extract_eml_from_zip(zip_path, temp_dir)

                        # 处理解压后的.eml文件
                        process_eml_folder(temp_dir, zip_path, max_lines)
    except Exception as e:
        logging.error(f"遍历文件夹 {folder_path} 时发生错误: {e}")


def main():
    eml_folder = "./eml"  # 替换为你的eml文件夹路径
    max_lines = 100  # 提取邮件内容的前 20 行

    try:
        # 处理/eml文件夹下的所有ZIP文件
        process_all_zips_in_folder(eml_folder, max_lines)
    except Exception as e:
        logging.error(f"程序运行过程中发生错误: {e}")
    finally:
        logging.info("程序运行结束。")


if __name__ == "__main__":
    setup_logging()  # 初始化日志配置
    main()
