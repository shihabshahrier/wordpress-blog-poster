import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

WP_URL = os.getenv("WP_URL", "").rstrip('/')
WORDPRESS_USER = os.getenv("WP_USERNAME", "")
WORDPRESS_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")

print(f"WordPress URL: {WP_URL}")
print(f"WordPress User: {WORDPRESS_USER}")
# print(f"WordPress App Password: {WORDPRESS_APP_PASSWORD}")

def post_to_wordpress(title, content):
    post_url = f"{WP_URL}/wp-json/wp/v2/posts"
    
    data = {
        "title": title,
        "content": content,
        "status": "publish"  # or "draft" if you don't want to publish immediately
    }

    response = requests.post(post_url, json=data, auth=(WORDPRESS_USER, WORDPRESS_APP_PASSWORD))

    if response.status_code == 201:
        print("✅ Post created successfully!")
        print(response.json())
    else:
        print(f"❌ Failed to create post: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    post_to_wordpress(
        title="Test Blog Post",
        content="This is a test post created via REST API."
    )
