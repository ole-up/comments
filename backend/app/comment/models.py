import secrets
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Sequence, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, remote, foreign
from sqlalchemy_utils import Ltree, LtreeType

from app.db.session import Base, engine

comments_id_seq = Sequence('comments_id_seq')


class User(Base):
    """Класс таблицы БД для хранения пользователей"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    external_id = Column(String)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.id'))
    first_name = Column(String)
    last_name = Column(String)
    user_group = Column(String)


class Service(Base):
    __tablename__ = "services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name = Column(String, nullable=False, unique=True)
    # login = Column(String)
    # pass_hash = Column(String)
    token = Column(String, default=secrets.token_hex(16))


class Comment(Base):
    """
    Класс таблицы БД для хранения комментариев.
    Для хранения путей используется тип данных ltree
    https://www.postgresql.org/docs/current/ltree.html#id-1.11.7.30.10
    Для того чтобы postgree его понимал, необходимо
    в базе включить расширение командой CREATE EXTENSION IF NOT EXISTS ltree;
    Сделать это необходимо один раз после создания БД.
    """
    __tablename__ = "comments"

    id = Column(Integer, comments_id_seq, primary_key=True)
    path = Column(LtreeType, nullable=False)
    level = Column(Integer, nullable=False)
    item_id = Column(String, nullable=False)
    data_type = Column(String, nullable=False)
    comment_text = Column(String(3000), nullable=False)
    is_deleted = Column(Boolean, default=False)
    date_created = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    date_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
    user_id = Column(Integer, ForeignKey('users.id'))
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.id'))
    scope = Column(String, default="all")

    parent = relationship(
        'Comment',
        primaryjoin=remote(path) == foreign(func.subpath(path, 0, -1)),
        backref='children',
        viewonly=True,
    )

    def __init__(self, item_id, comment_text, scope, user_id, service_id, data_type, parent_path=None):
        _id = engine.execute(comments_id_seq)
        self.id = _id
        ltree_id = Ltree(str(_id).zfill(9))
        ltree_parent = Ltree(str(parent_path).zfill(9))
        self.path = ltree_id if parent_path is None else ltree_parent + ltree_id
        self.level = func.nlevel(str(self.path))
        self.item_id = item_id
        self.comment_text = comment_text
        self.scope = scope
        self.user_id = user_id
        self.service_id = service_id
        self.data_type = data_type

    __table_args__ = (
        Index('ix_comments_path', path, postgresql_using="gist"),
    )
