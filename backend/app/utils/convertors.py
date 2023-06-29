import base64

from app.comment import models
from app.comment import schemas

# Функция получения комментария согласно схеме CommentOut из ответов БД
def comment_db_2_out(comment_db: models.Comment,
                     user: models.User):
    comment_out = schemas.CommentDB.from_orm(comment_db).dict()
    if comment_out['is_deleted']:
        comment_out['comment_text'] = 'Комментарий удален'
    comment_out.pop('user_id')
    comment_out['user'] = schemas.User.from_orm(user)
    return schemas.CommentOut(**comment_out)


# энкодер json объекта в строку
def json_2_str(json_obj):
    schema_bytes = str(json_obj).encode('utf-8')
    encoded = base64.b64encode(schema_bytes)
    return encoded.decode('utf-8')
