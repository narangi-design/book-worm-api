from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from db import get_connection, get_data
from auth import hash_password, create_access_token, get_current_user

load_dotenv()

app = FastAPI()

origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173').split(',')

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=['GET', 'POST', 'PUT'],
    allow_headers=['*'],
)


# --- Public endpoints ---

@app.get('/api/books')
def get_books():
    return get_data('books')

@app.get('/api/authors')
def get_authors():
    return get_data('authors')

@app.get('/api/polls')
def get_polls():
    return get_data('polls')

@app.get('/api/poll-votes')
def get_poll_votes():
    return get_data('poll_votes')

@app.get('/api/award-votes')
def get_award_votes():
    return get_data('award_votes')


# --- Protected endpoints ---

@app.get('/api/members')
def get_members(current_user: dict = Depends(get_current_user)):
    return get_data('members')


# --- Auth ---

class LoginData(BaseModel):
    username: str
    password: str

@app.post('/api/auth/login')
def login(data: LoginData):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, username FROM users WHERE username = %s AND password_hash = %s',
        (data.username, hash_password(data.password))
    )
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail='Неверный логин или пароль')

    token = create_access_token(user[0], user[1])
    return {'access_token': token, 'token_type': 'bearer', 'user_id': user[0], 'name': user[1]}

@app.get('/api/auth/me')
def get_me(current_user: dict = Depends(get_current_user)):
    return {'user_id': current_user['user_id'], 'name': current_user['name']}


class UpdateAccountData(BaseModel):
    current_password: str
    new_username: str | None = None
    new_password: str | None = None

@app.put('/api/auth/me')
def update_account(data: UpdateAccountData, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        'SELECT id FROM users WHERE id = %s AND password_hash = %s',
        (current_user['user_id'], hash_password(data.current_password))
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=401, detail='Неверный пароль')

    updates = []
    params = []
    if data.new_username:
        updates.append('username = %s')
        params.append(data.new_username)
    if data.new_password:
        updates.append('password_hash = %s')
        params.append(hash_password(data.new_password))

    if updates:
        params.append(current_user['user_id'])
        cursor.execute(f'UPDATE users SET {", ".join(updates)} WHERE id = %s', params)
        conn.commit()

    cursor.execute('SELECT id, username FROM users WHERE id = %s', (current_user['user_id'],))
    updated = cursor.fetchone()
    conn.close()
    return {'ok': True, 'user_id': updated[0], 'name': updated[1]}
