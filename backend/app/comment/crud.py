import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.comment import models
from app.comment import schemas


# создание комментария в БД
def create_comment(db: Session,
                   service_id: uuid.UUID,
                   data_type: str,
                   item_id: str,
                   parent_path,
                   user: schemas.User,
                   comment_text: str,
                   scope: schemas.Scope):
    """
    Функция сохранения комментария в БД
    """
    comment_row = models.Comment(item_id=item_id,
                                 comment_text=comment_text,
                                 user_id=user.id,
                                 service_id=service_id,
                                 parent_path=parent_path,
                                 data_type=data_type,
                                 scope=scope)

    db.add(comment_row)
    db.commit()
    return comment_row

# получение комментариев из БД
def get_comments(db: Session,
                 service_id: uuid.UUID,
                 data_type: schemas.DataType,
                 item_id: str,
                 scope: schemas.Scope,
                 presentation: schemas.PresentationList = schemas.PresentationList.tree,
                 parent_id: int = None):
    """Функция получения из БД комментариев для конкретной страницы"""
    comments = None
    if parent_id:
        parent_path = db.query(models.Comment.path).filter(models.Comment.service_id == service_id,
                                                           models.Comment.data_type == data_type,
                                                           models.Comment.item_id == item_id,
                                                           models.Comment.id == parent_id).one()
        # приходится ltree конвертировать в строку, т.к. библиотека psycopg2 не умеет работать с ltree
        parent_path = str(parent_path.path)

        if presentation == schemas.PresentationList.tree:
            # в запросе используем встроенные функции для ltree.subpath(models.Comment.path, 0, 1) возвращает
            # самого верхнего родителя, ltree2text конвертирует путь ltree в текст, т.к. у самого родителя может быть
            # путь самого верхнего уровня, делаем отбор всех с level больше 1.
            comments = db.query(models.Comment, models.User)\
                .join(models.User,models.User.id == models.Comment.user_id)\
                .filter(models.Comment.service_id == service_id,
                        models.Comment.data_type == data_type,
                        models.Comment.item_id == item_id,
                        models.Comment.scope == scope,
                        func.ltree2text(func.subpath(models.Comment.path, 0, 1)) == parent_path,
                        models.Comment.level > 1)\
                .order_by(models.Comment.path).all()
        elif presentation == schemas.PresentationList.flat:
            comments = db.query(models.Comment, models.User)\
                .join(models.User, models.User.id == models.Comment.user_id)\
                .filter(models.Comment.service_id == service_id,
                        models.Comment.data_type == data_type,
                        models.Comment.item_id == item_id,
                        models.Comment.scope == scope,
                        func.ltree2text(func.subpath(models.Comment.path, 0, 1)) == parent_path,
                        models.Comment.level > 1)\
                .order_by(models.Comment.date_created).all()
    else:
        if presentation == schemas.PresentationList.tree:
            comments = db.query(models.Comment, models.User)\
                .join(models.User, models.User.id == models.Comment.user_id)\
                .filter(models.Comment.service_id == service_id,
                        models.Comment.data_type == data_type,
                        models.Comment.item_id == item_id,
                        models.Comment.scope == scope)\
                .order_by(models.Comment.path).all()
        elif presentation == schemas.PresentationList.flat:
            comments = db.query(models.Comment, models.User)\
                .join(models.User, models.User.id == models.Comment.user_id)\
                .filter( models.Comment.service_id == service_id,
                         models.Comment.data_type == data_type,
                         models.Comment.item_id == item_id,
                         models.Comment.scope == scope)\
                .order_by(models.Comment.date_created).all()
    return comments

# изменение комменатрия
def update_comment(db: Session,
                   id: int,
                   service_id: uuid.UUID,
                   item_id: str,
                   data_type: str,
                   updated_comment: dict):
    """Функция сохранения в БД измененного комментария"""
    db.query(models.Comment).filter(models.Comment.id == id,
                                    models.Comment.service_id == service_id,
                                    models.Comment.item_id == item_id,
                                    models.Comment.data_type == data_type
                                    ).update(updated_comment, synchronize_session="fetch")
    db.commit()
    return db.query(models.Comment).filter(models.Comment.id == id).one()

# удаление комментария, физически не удаляет, а меняет флаг
def delete_comment(db: Session,
                   id: int,
                   service_id: uuid.UUID,
                   item_id: str,
                   data_type: str):
    """Функция удаления комментария из БД"""
    db.query(models.Comment).filter(models.Comment.id == id,
                                    models.Comment.service_id == service_id,
                                    models.Comment.item_id == item_id,
                                    models.Comment.data_type == data_type
                                    ).update({'is_deleted': True}, synchronize_session="fetch")
    db.commit()
    return db.query(models.Comment).filter(models.Comment.id == id).one()

# проверка наличия пользователя в базе
def check_user(db: Session, service_id: uuid.UUID, user_id: str):
    """Функция проверки наличия пользователя в базе"""
    if db.query(models.User).filter(models.User.service_id == service_id, models.User.external_id == user_id).count():
        return True
    else:
        return False

# получение пользователя из базы
def get_user(db: Session, service_id: uuid.UUID, user_id: str):
    """Функция получения пользователя из базы"""
    return db.query(models.User).filter(models.User.service_id == service_id, models.User.external_id == user_id).one()

# создание пользователя
def create_user(db: Session, service_id: uuid.UUID, user: schemas.User):
    """Функция сохранения пользователя в БД"""
    user_dict = user.dict()
    user_group = user_dict.pop('user_group')
    user_dict['service_id'] = service_id
    user_dict['user_group'] = user_group
    user_row = models.User(**user_dict)
    db.add(user_row)
    db.commit()
    return user_row

# получение пути по идентификатору
def get_path(db: Session, id: int):
    """Функция получение пути комментария по его id"""
    if id:
        comment = db.query(models.Comment).filter(models.Comment.id == id).one()
        return str(comment.path)

# создание сервиса
def create_service(db: Session, service_name: str):
    service_row = models.Service(service_name=service_name)
    db.add(service_row)
    db.commit()
    return service_row

# получение данных сервиса по его названию
def get_service_by_name(db: Session, service_name: str):
    return db.query(models.Service).filter(models.Service.service_name == service_name).one()

# получения токена сервиса по его id
def get_token_by_service_id(db: Session, service_id: uuid.UUID):
    return db.query(models.Service.token).filter(models.Service.id == service_id).one()[0]
#
# if __name__ == '__main__':
#     from app.db.session import SessionLocal
#
#     db = SessionLocal()
#     comments = get_comments(db=db, presentation=schemas.PresentationList.tree, service_id=uuid.UUID('15597d03-2868-4224-a219-e524bf259080'),
#                  item_id='page123')
#     for comment in comments:
#         # comment = schemas.CommentOut(**comment)
#         print(comment)
