"""衣物数据模型"""

import uuid
from datetime import datetime
from sqlalchemy import String, Float, Boolean, DateTime, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class Clothing(Base):
    __tablename__ = "clothing"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    zone: Mapped[str] = mapped_column(String(20), default="single_garment")
    category: Mapped[str] = mapped_column(String(50), default="未知")
    subcategory: Mapped[str] = mapped_column(String(100), default="pending_cloud")

    # 颜色
    primary_color_hex: Mapped[str] = mapped_column(String(9), default="#808080")
    primary_color_name: Mapped[str] = mapped_column(String(50), default="未知")
    primary_color_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    secondary_color_hex: Mapped[str | None] = mapped_column(String(9), nullable=True)
    secondary_color_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    secondary_color_ratio: Mapped[float] = mapped_column(Float, default=0.0)

    # 图案
    pattern: Mapped[str] = mapped_column(String(50), default="未知")
    pattern_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # 款式细分类字段
    neckline: Mapped[str] = mapped_column(String(50), default="pending_cloud")
    sleeve: Mapped[str] = mapped_column(String(50), default="pending_cloud")
    fit: Mapped[str] = mapped_column(String(50), default="pending_cloud")

    # 长度
    length_category: Mapped[str] = mapped_column(String(30), default="未知")

    # 材质
    fabric: Mapped[str] = mapped_column(String(50), default="未知")
    fabric_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # 其他
    crop_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_person: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_cloud: Mapped[bool] = mapped_column(Boolean, default=True)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
