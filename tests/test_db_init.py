# ./test_db_init.py
import logging
import os
import sys

# 动态添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import sessionmaker

from database.db_init import initialize_database  # 正常导入
from database.models import Attachment, Base, Email
from utils.logger import setup_logger  # 引入日志配置函数

# 初始化日志记录器
logger = setup_logger(log_level=logging.INFO, log_file="./logs/test_db_init.log")
logger.info("Starting pytest test with logging.")

DATABASE_URL = "sqlite:///./test_database.db"  # 测试数据库路径


@pytest.fixture(scope="module")
def setup_database():
    """
    测试数据库环境配置。
    """
    # 创建测试数据库
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    logger.info("Test database setup complete.")

    yield session  # 返回会话供测试使用

    # 测试完成后清理环境
    session.close()  # 关闭数据库会话
    engine.dispose()  # 释放数据库连接


def test_initialize_database(setup_database):
    """
    测试数据库初始化是否成功。
    """
    logger.info("Starting test for database initialization...")
    # 调用初始化方法
    initialize_database(DATABASE_URL)

    # 验证表是否存在
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)  # 使用 inspect() 方法获取表信息
    tables = inspector.get_table_names()

    assert "emails" in tables, "Table 'emails' not found in the database."
    assert "attachments" in tables, "Table 'attachments' not found in the database."

    logger.info("Database initialization test passed.")


def test_sample_data_inserted(setup_database):
    """
    测试示例数据是否插入成功。
    """
    logger.info("Starting test for sample data insertion...")
    session = setup_database

    # 验证邮件表数据
    emails = session.query(Email).all()
    assert len(emails) > 0, "No emails found in the database."
    assert (
        emails[0].sender == "test@example.com"
    ), "Unexpected sender in the emails table."

    # 验证附件表数据
    attachments = session.query(Attachment).all()
    assert len(attachments) > 0, "No attachments found in the database."
    assert (
        attachments[0].filename == "example.txt"
    ), "Unexpected filename in the attachments table."

    logger.info("Sample data insertion test passed.")


if os.path.exists("./test_database.db"):
    # os.remove("./test_database.db")  # 删除测试数据库文件
    logger.info("Test database cleaned up.")
