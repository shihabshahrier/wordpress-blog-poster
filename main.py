from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import requests
import base64
import os
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()

app = FastAPI(title="WordPress Blog Poster API", 
              description="API to post content to WordPress blogs")

# Configuration
class WordPressConfig:
    def __init__(self):
        self.wp_url = os.getenv("WP_URL", "")  # Your WordPress site URL (e.g., https://example.com)
        self.wp_username = os.getenv("WP_USERNAME", "")
        self.wp_password = os.getenv("WP_PASSWORD", "")
        self.wp_api_endpoint = f"{self.wp_url}/wp-json/wp/v2"

    def get_auth(self):
        token = base64.b64encode(f"{self.wp_username}:{self.wp_password}".encode())
        return {"Authorization": f"Basic {token.decode('utf-8')}"}

wp_config = WordPressConfig()

class BlogPost(BaseModel):
    title: str
    content: str
    excerpt: Optional[str] = None
    status: Optional[str] = "draft"
    categories: Optional[list] = None
    tags: Optional[list] = None

@app.post("/post-blog/", response_class=JSONResponse)
async def create_blog_post(
    title: str = Form(...),
    content: str = Form(...),
    excerpt: Optional[str] = Form(None),
    status: Optional[str] = Form("draft"),
    feature_image: Optional[UploadFile] = File(None),
    categories: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)
):
    # Validate config
    if not all([wp_config.wp_url, wp_config.wp_username, wp_config.wp_password]):
        raise HTTPException(500, "WordPress configuration missing. Set WP_URL, WP_USERNAME, and WP_PASSWORD.")

    # Parse categories/tags into lists of ints
    cat_ids = [int(c.strip()) for c in categories.split(",")] if categories else []
    tag_ids = [int(t.strip()) for t in tags.split(",")] if tags else []

    # Build the post payload
    post_data = {
        "title": title,
        "content": content,
        "status": status,
        "categories": cat_ids,
        "tags": tag_ids
    }
    if excerpt:
        post_data["excerpt"] = excerpt

    # ---- 1) Create the post ----
    try:
        wp_resp = requests.post(
            f"{wp_config.wp_api_endpoint}/posts",
            json=post_data,
            headers=wp_config.get_auth()
        )
    except requests.RequestException as e:
        raise HTTPException(502, f"Network error posting to WordPress: {e}")

    if not wp_resp.ok:
        body = wp_resp.text or "(no response body)"
        raise HTTPException(wp_resp.status_code, f"WP create-post error: {body}")

    post_json = wp_resp.json()
    post_id = post_json.get("id")
    if not post_id:
        raise HTTPException(500, f"Missing post ID in response: {post_json!r}")

    # ---- 2) Upload and set featured image (if provided) ----
    if feature_image:
        file_bytes = await feature_image.read()
        media_headers = {
            **wp_config.get_auth(),
            "Content-Disposition": f'attachment; filename="{feature_image.filename}"',
            "Content-Type": feature_image.content_type
        }

        # Upload media
        try:
            media_resp = requests.post(
                f"{wp_config.wp_api_endpoint}/media",
                headers=media_headers,
                data=file_bytes
            )
        except requests.RequestException as e:
            raise HTTPException(502, f"Network error uploading media: {e}")

        if not media_resp.ok:
            text = media_resp.text or "(no response body)"
            raise HTTPException(media_resp.status_code, f"WP media upload error: {text}")

        media_json = media_resp.json()
        media_id = media_json.get("id")
        if not media_id:
            raise HTTPException(500, f"Missing media ID in response: {media_json!r}")

        # Patch post to set featured image
        try:
            update_resp = requests.patch(
                f"{wp_config.wp_api_endpoint}/posts/{post_id}",
                json={"featured_media": media_id},
                headers=wp_config.get_auth()
            )
        except requests.RequestException as e:
            raise HTTPException(502, f"Network error setting featured image: {e}")

        if not update_resp.ok:
            text = update_resp.text or "(no response body)"
            raise HTTPException(update_resp.status_code, f"WP set-featured-image error: {text}")

    # ---- 3) Return success ----
    return {
        "status": "success",
        "message": f"Blog post created with ID: {post_id}",
        "post_id": post_id,
        "permalink": post_json.get("link")
    }


@app.get("/categories/", response_class=JSONResponse)
async def get_categories():
    """Get all available categories from WordPress"""
    try:
        response = requests.get(
            f"{wp_config.wp_api_endpoint}/categories",
            headers=wp_config.get_auth()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"WordPress API error: {e.response.text}"
        )

@app.get("/tags/", response_class=JSONResponse)
async def get_tags():
    """Get all available tags from WordPress"""
    try:
        response = requests.get(
            f"{wp_config.wp_api_endpoint}/tags",
            headers=wp_config.get_auth()
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"WordPress API error: {e.response.text}"
        )

@app.get("/", response_class=JSONResponse)
async def read_root():
    return {
        "app": "WordPress Blog Poster API", 
        "version": "1.0.0",
        "endpoints": [
            "/post-blog/",
            "/categories/",
            "/tags/"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)