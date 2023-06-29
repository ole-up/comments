import uuid
from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status, HTTPException, Query, Response


from app.db.session import SessionLocal
from app.comment import schemas, crud
from app.utils import convertors, signer


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter()

# публикация комментария
@router.post("/{service_id}/{data_type}/{item_id}/", response_model=schemas.CommentOut, tags=["comments"])
def create_comment(new_comment: schemas.CommentIn,
                   service_id: uuid.UUID,
                   data_type: schemas.DataType,
                   item_id: str = Query(..., regex="^.*$"),
                   db: Session = Depends(get_db)):
    """
    Публикация комментария в БД
    ======================

    Параметры строки запроса:

    - **service_id**: Идентификатор сервиса, который запрашивает комментарии. При отсутствии сервиса в БД будет получена
                        ошибка. Сервис должен быть предварительно зарегистрирован в БД.
    - **data_type**: Определяет тип запрашиваемых данных
    - **item_id**: Идентификатор страницы, для которой запрашиваются комментарии

    Тело запроса:

    - **comment_text**: Текст комментария
    - **user**: Данные пользователя (см. схему User). Пользователь отдельной регистрации в БД не требует,
                при его отсутствии, он будет автоматически зарегистрирован в БД.
    - **parent_id**: Идентификатор родительского комментария (необязательный, указывается только при наличии
                    родительского комментария)
    - **scope**: Область видимости комментариев, если не указана, по умолчанию все.
    - **signature**: - Подпись данных на основе токена сервиса
    """

    # проверяем совпадают ли с присланной, если нет, возвращаем ошибку
    if signer.check_signs(db=db,
                          received_signature=new_comment.signature,
                          service_id=service_id,
                          data_type=data_type,
                          item_id=item_id):
        # проверяем наличие пользователя в БД, если нет, создаем
        if not crud.check_user(db=db, service_id=service_id, user_id=new_comment.user.dict()['external_id']):
            user = crud.create_user(db=db, service_id=service_id, user=new_comment.user)
        else:
            user = crud.get_user(db=db, service_id=service_id, user_id=new_comment.user.dict()['external_id'])
        # если указан идентификатор родителя, получаем путь родителя
        if new_comment.parent_id:
            parent_path = crud.get_path(db=db, id=new_comment.parent_id)
        else:
            parent_path = None
        #Проверяем наличие scope, если нет, присваиваем по умолчанию all
        if new_comment.scope:
            scope = new_comment.scope
        else:
            scope = schemas.Scope.all
        try:
            comment_row = crud.create_comment(db=db,
                                            service_id=service_id,
                                            data_type=data_type,
                                            item_id=item_id,
                                            parent_path=parent_path,
                                            user=user,
                                            comment_text=new_comment.comment_text,
                                            scope=scope)
        except NoResultFound as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='service not found ')
        except SQLAlchemyError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err.__dict__['orig']))
        return convertors.comment_db_2_out(comment_row, user)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='incorrect signature')

# получение комментариев
@router.get("/{service_id}/{data_type}/{item_id}/", response_model=List[schemas.CommentOut], tags=["comments"])
def get_comments(service_id: uuid.UUID,
                 data_type: schemas.DataType,
                 item_id: str,
                 signature: str,
                 presentation: Optional[schemas.PresentationList] = schemas.PresentationList.tree,
                 scope: Optional[schemas.Scope] = schemas.Scope.all,
                 parent_id: Optional[int] = None,
                 db: Session = Depends(get_db)):
    """
    Запрос комментариев
    ====================

    Можно запросить как все комментарии для страницы,
    так и только дочерние для конкретного комментария.

    Параметры строки запроса:

    - **service_id**: Идентификатор сервиса, который запрашивает комментарии. При отсутствии сервиса в БД будет получена
                        ошибка. Сервис должен быть предварительно зарегистрирован в БД.
    - **data_type**: Определяет тип запрашиваемых данных
    - **item_id**: Идентификатор страницы, для которой запрашиваются комментарии

    Опции запроса:

    - **signature**: Подпись данных на основе токена сервиса
    - **presentation**: Определяет вид отображения комментариев (древовидный или плоский), влияет на сортировку
                      отдаваемых комментариев, если не указан, по умолчанию древовидный.
    - **scope**: Область видимости комментариев, если не указана, по умолчанию все.
    - **parent_id**: идентификатор родительского комментария (необязательный, если указан, выведутся дочерние
                   комментарии)
    """

    if signer.check_signs(db=db,
                          received_signature=signature,
                          service_id=service_id,
                          data_type=data_type,
                          item_id=item_id):
        comments_list = []
        try:
            comments = crud.get_comments(db=db,
                                 service_id=service_id,
                                 data_type=data_type,
                                 item_id=item_id,
                                 presentation=presentation,
                                 parent_id=parent_id,
                                 scope=scope)
        except NoResultFound:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no data found with these parameters")
        except SQLAlchemyError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err.__dict__['orig']))
        for comment in comments:
            # в ответе от crud.get_comments объект, где в каждом элементе два объекта,
            # первый это models.Comments, а второй models.User
            comment_out = convertors.comment_db_2_out(comment[0], comment[1])
            comments_list.append(comment_out)
        return comments_list
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='incorrect signature')


# изменение комментария
@router.put("/{service_id}/{data_type}/{item_id}/{comment_id}/", status_code=status.HTTP_200_OK, tags=["comments"])
def update_comment(updated_comment: schemas.CommentUpdate,
                    service_id: uuid.UUID,
                    data_type: schemas.DataType,
                    comment_id: int,
                    item_id: str = Query(..., regex="^.*$"),
                    db: Session = Depends(get_db)):
    """
        Изменение комментария
        ====================

        Изменение текста комментария и/или его области видимости

        Параметры строки запроса:

        - **service_id**: Идентификатор сервиса, который запрашивает комментарии. При отсутствии сервиса в БД будет получена
                            ошибка. Сервис должен быть предварительно зарегистрирован в БД.
        - **data_type**: Определяет тип запрашиваемых данных
        - **item_id**: Идентификатор страницы, для которой запрашиваются комментарии
        - **comment_id**: Идентификатор изменяемого комментария

        Тело запроса:

        - **comment_text**: Опционально. Текст изменяемого комментария
        - **scope**: Опционально. Область видимости комментариев
        - **signature**: Подпись данных на основе токена сервиса
        """

    if signer.check_signs(db=db,
                          received_signature=updated_comment.signature,
                          service_id=service_id,
                          data_type=data_type,
                          item_id=item_id):

        updated_comment_dict = updated_comment.dict()
        if not updated_comment_dict['comment_text']:
            updated_comment_dict.pop('comment_text')
        elif not updated_comment_dict['scope']:
            updated_comment_dict.pop('scope')
        try:
            crud.update_comment(db=db,
                                service_id=service_id,
                                data_type=data_type,
                                item_id=item_id,
                                id=comment_id,
                                updated_comment=updated_comment_dict)

        except SQLAlchemyError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err.__dict__['orig']))
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='incorrect signature')

# удаление комментария
@router.delete("/{service_id}/{data_type}/{item_id}/{comment_id}/", status_code=status.HTTP_204_NO_CONTENT, tags=["comments"])
def delete_comment(service_id: uuid.UUID,
                   data_type: schemas.DataType,
                   comment_id: int,
                   signature: schemas.SignatureDelete,
                   item_id: str = Query(..., regex="^.*$"),
                   db: Session = Depends(get_db)):
    """
            Удаление комментария
            ====================

              Параметры строки запроса:

            - **service_id**: Идентификатор сервиса, который запрашивает комментарии. При отсутствии сервиса в БД будет получена
                                ошибка. Сервис должен быть предварительно зарегистрирован в БД.
            - **data_type**: Определяет тип запрашиваемых данных
            - **item_id**: Идентификатор страницы, для которой запрашиваются комментарии
            - **comment_id**: Идентификатор удаляемого комментария

            Тело запроса:

            - **signature**: Подпись данных на основе токена сервиса
            """
    if signer.check_signs(db=db,
                          received_signature=signature.signature,
                          service_id=service_id,
                          data_type=data_type,
                          item_id=item_id):
        try:
            crud.delete_comment(db=db,
                                service_id=service_id,
                                data_type=data_type,
                                item_id=item_id,
                                id=comment_id)
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        except NoResultFound as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='no data found with these parameters')
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='incorrect signature')


# временно для отладки для регистрации сервиса и для получения данных по названию сервиса
# =======================================================================================
# регистрация сервиса
@router.post("/service/", response_model=schemas.Service, tags=["service"])
def create_service(service_name: str, db: Session = Depends(get_db)):
    if service_name.strip() == '':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='invalid service name')
    try:
        service_row =  crud.create_service(service_name=service_name, db=db)
    except SQLAlchemyError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err.__dict__['orig']))
    return service_row

# получение данных сервиса по названию
@router.get("/service/", response_model=schemas.Service, tags=["service"])
def get_service_by_name(service_name: str, db: Session = Depends(get_db)):
    try:
        service_row = crud.get_service_by_name(service_name=service_name, db=db)
    except NoResultFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'service with name {service_name} not found')
    return service_row
