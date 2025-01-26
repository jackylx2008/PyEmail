import logging
import os
import sys

# 动态添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Attachment, Base, Email
from utils.logger import setup_logger  # 引入日志配置函数

# 将项目根目录添加到 Python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# 初始化日志记录器
logger = setup_logger(log_level=logging.INFO, log_file="./logs/db_init.log")


def initialize_database(db_url):
    """
    初始化数据库，包括表的创建和示例数据的插入。
    """
    try:
        logger.info("Starting database initialization...")

        # 创建数据库引擎
        engine = create_engine(db_url)
        logger.info(f"Database engine created with URL: {db_url}")

        # 创建所有表
        Base.metadata.create_all(engine)
        logger.info("All tables created successfully.")

        # 创建会话工厂
        Session = sessionmaker(bind=engine)
        session = Session()
        logger.info("Database session initialized.")

        # 插入示例数据
        insert_sample_data(session)

    except Exception as e:
        logger.error(
            f"An error occurred during database initialization: {e}", exc_info=True
        )
        raise
    finally:
        logger.info("Database initialization completed.")


def insert_sample_data(session):
    """
    插入示例数据到数据库中。
    """
    try:
        logger.info("Inserting sample data into the database...")

        # 示例邮件
        email = Email(
            sender="test@example.com",
            recipients='["recipient1@example.com", "recipient2@example.com"]',
            cc='["cc@example.com"]',
            bcc="[]",
            subject="Sample Email",
            text_content="This is a plain text email content.",
            html_content="<p>This is an HTML email content.</p>",
            headers='{"Message-ID": "123456@example.com", "Content-Type": "text/html"}',
        )
        session.add(email)
        session.flush()  # 确保 email.id 被分配

        logger.info(f"Sample email added with ID: {email.id}")

        # 示例附件
        attachment = Attachment(
            email_id=email.id,
            filename="example.txt",
            filepath="./attachments/example.txt",
        )
        session.add(attachment)
        logger.info(f"Sample attachment added with filename: {attachment.filename}")

        # 提交事务
        session.commit()
        logger.info("Sample data inserted successfully.")

    except Exception as e:
        session.rollback()
        logger.error(f"Failed to insert sample data: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # 数据库URL（根据实际数据库类型和配置修改）
    DATABASE_URL = "sqlite:///./database.db"  # 使用 SQLite 作为示例

    # 初始化数据库
    initialize_database(DATABASE_URL)
