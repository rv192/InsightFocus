import requests
import json

BASE_URL = 'your-pocketbase url' #  http://192.168.5.185:8090'
ADMIN_EMAIL = 'your-admin-email@example.com'
ADMIN_PASSWORD = 'your-admin-password'

def login():
    response = requests.post(f"{BASE_URL}/api/admins/auth-with-password", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    response.raise_for_status()
    return response.json()['token']

def create_collection(token, name, schema):
    headers = {
        'Authorization': token,
        'Content-Type': 'application/json'
    }
    data = {
        "name": name,
        "schema": schema
    }
    response = requests.post(f"{BASE_URL}/api/collections", headers=headers, json=data)
    if response.status_code == 200:
        print(f"Collection '{name}' created successfully")
    else:
        print(f"Failed to create collection '{name}': {response.text}")

def main():
    token = login()

    # Users collection
    create_collection(token, 'users', [
        {"name": "username", "type": "text", "required": True},
        {"name": "email", "type": "email", "required": True},
        {"name": "created_at", "type": "date"},
        {"name": "last_login_at", "type": "date"}
    ])

    # RssSources collection
    create_collection(token, 'rssSources', [
        {"name": "url", "type": "url", "required": True},
        {"name": "name", "type": "text", "required": True},
        {"name": "description", "type": "text"},
        {"name": "last_fetched_at", "type": "date"}
    ])

    # Articles collection
    create_collection(token, 'articles', [
        {"name": "source_id", "type": "relation", "required": True, "options": {"collectionId": "rssSources"}},
        {"name": "url", "type": "url", "required": True},
        {"name": "url_hash", "type": "text", "required": True},
        {"name": "title", "type": "text", "required": True},
        {"name": "content", "type": "text"},
        {"name": "plain_content", "type": "text"},
        {"name": "content_hash", "type": "text"},
        {"name": "published_at", "type": "date"},
        {"name": "fetched_at", "type": "date"},
        {"name": "summary", "type": "text"},
        {"name": "language", "type": "text"},
        {"name": "read_time", "type": "number"},
        {"name": "last_updated_at", "type": "date"}
    ])

    # UserRssSources collection
    create_collection(token, 'userRssSources', [
        {"name": "user_id", "type": "relation", "required": True, "options": {"collectionId": "users"}},
        {"name": "source_id", "type": "relation", "required": True, "options": {"collectionId": "rssSources"}}
    ])

    # UserFocuses collection
    create_collection(token, 'userFocuses', [
        {"name": "user_id", "type": "relation", "required": True, "options": {"collectionId": "users"}},
        {"name": "type", "type": "select", "required": True, "options": {"values": ["tag", "content"]}},
        {"name": "content", "type": "text", "required": True}
    ])

    # FocusedContents collection
    create_collection(token, 'focusedContents', [
        {"name": "user_id", "type": "relation", "required": True, "options": {"collectionId": "users"}},
        {"name": "article_id", "type": "relation", "required": True, "options": {"collectionId": "articles"}},
        {"name": "focus_id", "type": "relation", "required": True, "options": {"collectionId": "userFocuses"}},
        {"name": "created_at", "type": "date"}
    ])

    # UserArticleStatus collection
    create_collection(token, 'userArticleStatus', [
        {"name": "user_id", "type": "relation", "required": True, "options": {"collectionId": "users"}},
        {"name": "article_id", "type": "relation", "required": True, "options": {"collectionId": "articles"}},
        {"name": "status", "type": "select", "required": True, "options": {"values": ["unread", "read", "read_later"]}},
        {"name": "updated_at", "type": "date"}
    ])

if __name__ == "__main__":
    main()
