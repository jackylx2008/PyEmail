import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    create_engine,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

# 创建基础模型
Base = declarative_base()


class Email(Base):
    """
    邮件表模型
    """

    __tablename__ = "emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    sender = Column(String, nullable=False)
    recipients = Column(Text, nullable=False)  # 存储 JSON 格式的收件人列表
    cc = Column(Text, default="[]")  # 存储 JSON 格式的抄送列表
    bcc = Column(Text, default="[]")  # 存储 JSON 格式的密件抄送列表
    subject = Column(String, nullable=False)
    text_content = Column(Text, nullable=True)
    html_content = Column(Text, nullable=True)
    tags = Column(Text, default="[]")  # 存储 JSON 格式的标签
    sent_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    headers = Column(Text, nullable=True)  # 邮件头信息存储为 JSON 格式
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

    # 关联关系
    attachments = relationship(
        "Attachment", back_populates="email", cascade="all, delete-orphan"
    )


class Attachment(Base):
    """
    附件表模型
    """

    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(UUID(as_uuid=True), ForeignKey("emails.id"), nullable=False)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # 关联关系
    email = relationship("Email", back_populates="attachments")


# 如果需要手动运行表的创建
if __name__ == "__main__":
    # 数据库引擎（使用 SQLite 示例，可以替换为实际数据库 URL）
    DATABASE_URL = "sqlite:///./database.db"
    engine = create_engine(DATABASE_URL)

    # 创建所有表
    Base.metadata.create_all(engine)
    print("All tables created successfully.")
