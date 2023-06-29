import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, validator, ConstrainedStr, Field

from app.utils.validators import trim_values


class CommentTextField(ConstrainedStr):
    """Класс строкового типа данных с ограничением по минимальной и максимальной длине"""
    min_length = 1
    max_length = 3000


class PresentationList(str, Enum):
    """Список видов отображения комментариев"""
    tree = 'tree'
    flat = 'flat'


class DataType(str, Enum):
    """Список типов данных"""
    comments = 'comments'


class Scope(str, Enum):
    """Список типов данных"""
    all = 'all'
    admin = 'admin'
    registered = 'registered'


class User(BaseModel):
    """Схема данных пользователя"""
    id: Optional[int] = Field(description="Идентификатор пользователя, в нашей БД")
    external_id: str = Field(description="Идентификатор пользователя, используемый во внешнем сервисе")
    first_name: Optional[str] = Field(description="Необязательный параметр. Имя пользователя")
    last_name: Optional[str] = Field(description="Необязательный параметр. Фамилия пользователя")
    user_group: Optional[str] = Field(description="Необязательный параметр. Группа прав доступа пользователя")

    class Config:
        orm_mode = True


class CommentIn(BaseModel):
    """Схема для принимаемых комментариев"""
    comment_text: CommentTextField
    user: User
    parent_id: Optional[int] = Field(default=None)
    scope: Optional[Scope]
    signature: str

    # validators
    _trim_values = validator('*', allow_reuse=True, pre=True)(trim_values)

    class Config:
        orm_mode = True


class CommentOut(BaseModel):
    """Схема отдаваемых комментариев"""
    id: int
    level: int
    comment_text: str
    date_created: datetime
    date_modified: datetime
    is_deleted: bool
    scope: str
    user: User

    class Config:
        orm_mode = True


class CommentUpdate(BaseModel):
    """Схема для изменяемого комментария"""
    comment_text: Optional[CommentTextField]
    scope: Optional[Scope]
    signature: str

    # validators
    _trim_values = validator('*', allow_reuse=True, pre=True)(trim_values)

    class Config:
        orm_mode = True


class SignatureDelete(BaseModel):
    signature: str


class CommentDB(BaseModel):
    """Схема для сохранения в БД"""
    id: Optional[int]
    item_id: str
    service_id: uuid.UUID
    level: int
    path: str
    data_type: str
    comment_text: str
    scope: str
    date_created: datetime
    date_modified: datetime
    is_deleted: bool
    user_id: int

    # костыль, преобразует ltree в строку, т.е. paydantic не знает что такое ltree
    @validator('path', pre=True)
    def ltree_to_str(cls, v):
        return str(v)

    class Config:
        orm_mode = True


class Service(BaseModel):
    id: uuid.UUID
    service_name: str
    token: str

    class Config:
        orm_mode = True
