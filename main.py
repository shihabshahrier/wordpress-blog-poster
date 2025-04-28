from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List, Tuple
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Logging Configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# FastAPI instance
app = FastAPI(
    title="WordPress Blog Poster API",
    description="API for posting to WordPress blogs via REST",
    version="1.0.0"
)

# WordPress Configuration
class WordPressConfig:
    @property
    def wp_url(self) -> str:
        return os.getenv("WP_URL", "").rstrip('/')

    @property
    def username(self) -> str:
        return os.getenv("WP_USERNAME", "")

    @property
    def app_password(self) -> str:
        return os.getenv("WP_APP_PASSWORD", "")

    @property
    def api_base(self) -> str:
        return f"{self.wp_url}/wp-json/wp/v2"

    def get_auth(self) -> Tuple[str, str]:
        return self.username, self.app_password

    def get_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (compatible; FastAPI-Bot/1.0)",
            "Accept": "application/json"
        }

wp_config = WordPressConfig()

# Request model for Blog Post
class BlogPost(BaseModel):
    title: str
    content: str
    excerpt: Optional[str] = None
    status: Optional[str] = "draft"
    categories: Optional[List[int]] = None
    tags: Optional[List[int]] = None


@app.get("/", response_class=JSONResponse)
async def root():
    return {
        "app": "WordPress Blog Poster API",
        "version": "1.0.0",
        "routes": ["/post-blog/", "/test-connection/"]
    }


@app.get("/test-connection/", response_class=JSONResponse)
async def test_wordpress_connection():
    try:
        test_url = f"{wp_config.api_base}/posts"
        logger.info(f"Testing WordPress connection at: {test_url}")

        resp = requests.get(
            test_url,
            auth=wp_config.get_auth(),
            headers=wp_config.get_headers(),
            params={"per_page": 1}
        )

        try:
            data = resp.json()
            is_json = True
        except ValueError:
            data = resp.text[:500]
            is_json = False

        return {
            "status": "ok" if resp.status_code < 400 else "error",
            "status_code": resp.status_code,
            "is_json": is_json,
            "data": data
        }

    except requests.RequestException as e:
        logger.error(f"Connection test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    # Validate environment variables
    if not all([wp_config.wp_url, wp_config.username, wp_config.app_password]):
        raise HTTPException(status_code=500, detail="Missing WP_URL, WP_USERNAME, or WP_APP_PASSWORD in environment variables")

    def parse_comma_separated_ids(input_str: Optional[str]) -> Optional[List[int]]:
        return [int(x.strip()) for x in input_str.split(',') if x.strip().isdigit()] if input_str else None

    post_data = {
        "title": title,
        "content": content,
        "status": status
    }

    if excerpt:
        post_data["excerpt"] = excerpt
    if categories := parse_comma_separated_ids(categories):
        post_data["categories"] = categories
    if tags := parse_comma_separated_ids(tags):
        post_data["tags"] = tags

    try:
        # Check WordPress connection before posting
        logger.info("Testing WordPress connection before posting...")
        test_response = requests.get(
            f"{wp_config.api_base}/posts",
            auth=wp_config.get_auth(),
            headers=wp_config.get_headers(),
            params={"per_page": 1}
        )

        if test_response.status_code >= 400:
            logger.error(f"Connection failed: {test_response.status_code} {test_response.text}")
            raise HTTPException(status_code=test_response.status_code, detail="WordPress connection failed")

        # Handle feature image upload if provided
        media_id = None
        if feature_image:
            logger.info("Uploading feature image...")
            media_data = {
                'file': (feature_image.filename, await feature_image.read(), feature_image.content_type)
            }
            media_response = requests.post(
                f"{wp_config.api_base}/media",
                auth=wp_config.get_auth(),
                headers=wp_config.get_headers(),
                files=media_data
            )

            if media_response.status_code >= 400:
                logger.error(f"Feature image upload failed: {media_response.status_code} {media_response.text}")
                raise HTTPException(status_code=media_response.status_code, detail="Failed to upload feature image")

            media_json = media_response.json()
            media_id = media_json.get('id')

        # Add feature image to post data if it was uploaded
        if media_id:
            post_data['featured_media'] = media_id

        # Create post
        logger.info(f"Posting blog: {title}")
        post_response = requests.post(
            f"{wp_config.api_base}/posts",
            auth=wp_config.get_auth(),
            headers=wp_config.get_headers(),
            json=post_data
        )

        if post_response.status_code >= 400:
            logger.error(f"Post creation failed: {post_response.status_code} {post_response.text}")
            raise HTTPException(status_code=post_response.status_code, detail=post_response.text)

        post_json = post_response.json()
        return {
            "status": "success",
            "post_id": post_json.get("id"),
            "link": post_json.get("link")
        }

    except requests.RequestException as e:
        logger.error(f"Post request error: {e}")
        raise HTTPException(status_code=500, detail="Failed to communicate with WordPress")
