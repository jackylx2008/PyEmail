import csv
import logging
import re
import sqlite3
from typing import List, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,  # 设置日志级别
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler("./process_emails.log", encoding="utf-8"),  # 输出到文件
    ],
)

# 正则表达式，匹配表格中的记录行
PATTERN = re.compile(
    r"\|\s*(\d+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|"
)


def sanitize_field(field: str) -> str:
    """
    清理字段值，去掉多余的空格。
    :param field: 待清理的字段值
    :return: 清理后的字段值
    """
    return field.strip() if field else ""


def process_email_body(body: Optional[str]) -> List[Tuple[str, ...]]:
    """
    处理邮件正文，逐行匹配记录。
    :param body: 邮件正文内容
    :return: 匹配成功的记录列表
    """
    if not body:
        logging.warning("邮件正文为空，跳过处理。")
        return []

    matches = []
    for line in body.splitlines():
        match = PATTERN.match(line)
        if match:
            # 提取匹配的字段并清理
            record = tuple(sanitize_field(field) for field in match.groups())
            matches.append(record)
    return matches


def write_to_csv(
    file_path: str, headers: List[str], rows: List[Tuple[str, ...]]
) -> None:
    """
    将数据写入 CSV 文件。
    :param file_path: CSV 文件路径
    :param headers: 表头
    :param rows: 数据行
    """
    try:
        with open(file_path, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(rows)
        logging.info(f"数据已成功写入 {file_path}")
    except IOError as e:
        logging.error(f"写入 CSV 文件时出错: {e}")
        raise


def main(db_path: str, output_path: str) -> None:
    """
    主函数，处理数据库中的邮件内容并导出到 CSV 文件。
    :param db_path: SQLite 数据库路径
    :param output_path: 导出 CSV 文件路径
    """
    conn = None
    matches_found = False

    try:
        logging.info(f"连接到数据库: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT body FROM emails")
        logging.info("成功读取 emails 表的 body 列数据。")

        all_matches = []
        for row in cursor.fetchall():
            matches = process_email_body(row[0])
            if matches:
                matches_found = True
                all_matches.extend(matches)

        if matches_found:
            headers = [
                "卡号后四位",
                "交易日",
                "记账日",
                "交易类型",
                "商户名称/城市",
                "交易金额/币种",
                "记账金额/币种",
            ]
            write_to_csv(output_path, headers, all_matches)
        else:
            logging.warning("未提取到有效数据，请检查数据库内容或正则表达式。")

    except sqlite3.Error as e:
        logging.error(f"数据库操作出错: {e}")
    except Exception as e:
        logging.error(f"程序运行时发生未预期的错误: {e}")
    finally:
        if conn:
            conn.close()
            logging.info("数据库连接已关闭。")


if __name__ == "__main__":
    main("./raw_email.db", "./temp.csv")
