import hashlib
import hmac
import uuid

from sqlalchemy.orm import Session

from app.comment import crud, schemas


# генерация подписи
def create_sign(key: str, message):
    key = key.encode()
    message = message.encode()
    signing = hmac.new(key, message, hashlib.sha1)
    return signing.hexdigest()


# проверка подписи
def check_signs(db: Session, received_signature: str, service_id: uuid.UUID, data_type: schemas.DataType, item_id: str):
    message = str(service_id) + data_type + item_id
    token = crud.get_token_by_service_id(db=db, service_id=service_id)
    signature = create_sign(token, message)
    return hmac.compare_digest(received_signature, signature)


if __name__ == '__main__':
    import json
    from app.utils import convertors

    test_message = 'f9f82528-6146-4f75-8780-c9f2f4b0da68' + 'comments' + '123' + 'all'
    test_key = '84867699caf142072866faf2e75b7f6b'
    comment_post = {
        "comment_text": "string",
        "user": {
            "id": 1,
            "external_id": "string",
            "first_name": "string",
            "last_name": "string",
            "user_group": "string"
        },
        "parent_id": 0,
        "scope": "all"
    }
    comment_put = {
        "comment_text": "string2"
    }
    comment_post = json.dumps(comment_post)
    comment_put = json.dumps(comment_put)
    print('POST:', create_sign(test_key, (
                'f9f82528-6146-4f75-8780-c9f2f4b0da68' + 'comments' + '123' + convertors.json_2_str(comment_post))))
    print('GET:', create_sign(test_key, ('f9f82528-6146-4f75-8780-c9f2f4b0da68' + 'comments' + '123' + 'admin')))
    print('PUT:', create_sign(test_key, (
                'f9f82528-6146-4f75-8780-c9f2f4b0da68' + 'comments' + '123' + '138' + convertors.json_2_str(
            comment_put))))
