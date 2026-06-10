"""用户资料 + 相册 + 风格画像模型"""

import uuid
from datetime import datetime, date
from sqlalchemy import String, Float, Date, DateTime, JSON, Boolean, Integer, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class UserProfile(Base):
    __tablename__ = "user_profile"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nickname: Mapped[str] = mapped_column(String(50), default="用户")
    avatar_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gender: Mapped[str] = mapped_column(String(10), default="未设置")
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    city: Mapped[str] = mapped_column(String(50), default="北京")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class GalleryImage(Base):
    __tablename__ = "gallery_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255))
    filepath: Mapped[str] = mapped_column(String(500))
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    width: Mapped[int | None] = mapped_column(nullable=True)
    height: Mapped[int | None] = mapped_column(nullable=True)
    tag: Mapped[str] = mapped_column(String(50), default="portrait")  # portrait / outfit
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class GalleryImageAnalysis(Base):
    """每张相册照片的端侧分析结果"""
    __tablename__ = "gallery_image_analysis"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    gallery_image_id: Mapped[str] = mapped_column(String(36), ForeignKey("gallery_images.id", ondelete="CASCADE"), unique=True)
    has_person: Mapped[bool] = mapped_column(Boolean, default=False)
    person_count: Mapped[int] = mapped_column(Integer, default=0)
    clothing_colors: Mapped[dict | None] = mapped_column(JSON, nullable=True)       # [{"name":"黑色","hex":"#1a1a2e","ratio":0.45}, ...]
    clothing_categories: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # ["上装","下装","全身"]
    dominant_pattern: Mapped[str | None] = mapped_column(String(50), nullable=True) # 纯色/条纹/格子/印花
    face_crop_base64: Mapped[str | None] = mapped_column(Text, nullable=True)       # 人脸裁剪图(供创意生成)
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False)
    analyze_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UserStyleProfile(Base):
    """用户风格画像（聚合所有数据源）"""
    __tablename__ = "user_style_profile"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # 颜色偏好 — 基于相册+衣橱统计
    color_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    #   [{"color":"黑色","ratio":0.35,"hex":"#1a1a2e"}, {"color":"深蓝色","ratio":0.22,"hex":"#2d4a7a"}, ...]
    # 图案偏好 — 统计占比
    pattern_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    #   {"纯色":0.65,"条纹":0.15,"格子":0.10,"印花":0.10}
    # 品类型偏好 — 统计占比
    category_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    #   {"上装":0.40,"下装":0.30,"全身":0.20,"鞋履":0.10}
    # 风格倾向 — 基于颜色+图案+品类综合推断
    style_tendency: Mapped[str | None] = mapped_column(String(100), nullable=True)   # "简约都市风"/"休闲运动风"/"优雅知性风"
    # 主导色系 HEX 列表
    dominant_colors_hex: Mapped[dict | None] = mapped_column(JSON, nullable=True)    # ["#1a1a2e","#2d4a7a","#808080"]
    # 统计元数据
    gallery_photo_count: Mapped[int] = mapped_column(Integer, default=0)
    wardrobe_item_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 置信度(样本量越大越高)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
