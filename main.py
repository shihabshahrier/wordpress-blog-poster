# main.py
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, List, Tuple
from pydantic import BaseModel
import requests
import logging
from dotenv import load_dotenv
import json
from openai import OpenAI
import time

# Load environment variables
load_dotenv()

# Logging Configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# FastAPI instance
app = FastAPI(
    title="WordPress SEO Content Generator and Poster",
    description="Generate SEO content and post to WordPress blogs via REST",
    version="1.0.0"
)

# Set up templates directory
templates = Jinja2Templates(directory="templates")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Request model for Blog Post
class BlogPost(BaseModel):
    title: str
    content: str
    excerpt: Optional[str] = None
    status: Optional[str] = "draft"
    categories: Optional[List[int]] = None
    tags: Optional[List[int]] = None

# WordPress Configuration Class
class WordPressConfig:
    def __init__(self, wp_url=None, username=None, app_password=None):
        self.wp_url = wp_url or os.getenv("WP_URL", "").rstrip('/')
        self.username = username or os.getenv("WP_USERNAME", "")
        self.app_password = app_password or os.getenv("WP_APP_PASSWORD", "")
    
    @property
    def api_base(self) -> str:
        return f"{self.wp_url}/wp-json/wp/v2"

    def get_auth(self) -> Tuple[str, str]:
        return self.username, self.app_password

    def get_headers(self) -> dict:
        return {
            "User-Agent": "MyCustomBot/1.0",
            "Accept": "application/json"
        }

# Initialize OpenAI client for content generation
def get_openai_client(api_key=None):
    return OpenAI(
        base_url="https://api.studio.nebius.com/v1/",
        api_key=api_key or os.environ.get("NEBIUS_API_KEY")
    )

# SEO Content Generator Function
def generate_seo_blog_content(
    client,
    main_topic: str,
    keywords: List[str],
    tone: str = "informative",
    post_type: str = "article",
    word_count: int = 800,
    max_retries: int = 3,
    retry_delay: int = 2
) -> dict:
    """
    Generate SEO-optimized blog content with title, excerpt, and body
    """
    # Construct a detailed prompt
    prompt = f"""
    Generate SEO-optimized content for a WordPress blog post with the following components:

    MAIN TOPIC: {main_topic}
    
    KEY SEO KEYWORDS: {', '.join(keywords)}
    
    REQUIRED FORMAT (output as JSON):
    {{
        "title": "SEO-optimized title (60-70 characters, include 1-2 primary keywords, compelling and clickable)",
        "excerpt": "SEO-optimized meta description / excerpt (150-160 characters, include 1-2 keywords, entice clicks)",
        "content": "Full blog post content (formatted with proper HTML tags)"
    }}
    
    CONTENT REQUIREMENTS:
    - Title: Must be attention-grabbing and under 70 characters
    - Excerpt: Must summarize value proposition in under 160 characters
    - Content Structure: Use proper HTML tags (<h2>, <h3>, <p>, <ul>, <ol>, <li>)
    - Strategically place keywords in title, headings, first paragraph, and throughout content
    - Maintain keyword density of 1-2% for primary keywords
    - Include at least one call-to-action
    - Content should be {tone} in tone
    - Format as a {post_type}
    - Approximately {word_count} words for the main content
    
    IMPORTANT: Respond ONLY with the JSON. Do not include any other text.
    """
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Generating SEO content for topic: {main_topic}")
            
            response = client.chat.completions.create(
                model="deepseek-ai/DeepSeek-V3",
                messages=[
                    {"role": "system", "content": "You are an expert SEO content writer specializing in creating high-quality, optimized blog content."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7,
                top_p=0.95,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON response
            try:
                result = json.loads(content)
                
                # Validate the result has required fields
                if not all(k in result for k in ["title", "excerpt", "content"]):
                    raise ValueError("Response missing required fields")
                
                logger.info(f"Successfully generated SEO content. Title: {result['title']}")
                return result
                
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON response")
                if attempt == max_retries - 1:
                    return {
                        "title": f"Article about {main_topic}",
                        "excerpt": f"Learn more about {main_topic} and {', '.join(keywords[:2])}.",
                        "content": "Error generating content. Please try again."
                    }
            
        except Exception as e:
            logger.error(f"Error generating SEO content (attempt {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return {
                    "title": f"Article about {main_topic}",
                    "excerpt": f"Learn more about {main_topic} and {', '.join(keywords[:2])}.",
                    "content": "Error generating content. Please try again."
                }

# WordPress Connection Test
async def test_wordpress_connection(wp_config):
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
        return {"status": "error", "error": str(e)}

# Post to WordPress Function
async def post_to_wordpress(
    wp_config,
    title: str,
    content: str,
    excerpt: Optional[str] = None,
    status: str = "draft",
    feature_image_file = None,
    categories: Optional[str] = None,
    tags: Optional[str] = None
):
    # Validate WordPress configuration
    if not all([wp_config.wp_url, wp_config.username, wp_config.app_password]):
        raise HTTPException(status_code=500, detail="Missing WordPress credentials")

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
            return {"status": "error", "message": "WordPress connection failed", "code": test_response.status_code}

        # Handle feature image upload if provided
        media_id = None
        if feature_image_file:
            logger.info("Uploading feature image...")
            file_content = await feature_image_file.read()
            media_data = {
                'file': (feature_image_file.filename, file_content, feature_image_file.content_type)
            }
            media_response = requests.post(
                f"{wp_config.api_base}/media",
                auth=wp_config.get_auth(),
                headers=wp_config.get_headers(),
                files=media_data
            )

            if media_response.status_code >= 400:
                logger.error(f"Feature image upload failed: {media_response.status_code} {media_response.text}")
                return {"status": "error", "message": "Failed to upload feature image", "code": media_response.status_code}

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
            return {"status": "error", "message": post_response.text, "code": post_response.status_code}

        post_json = post_response.json()
        return {
            "status": "success",
            "post_id": post_json.get("id"),
            "link": post_json.get("link")
        }

    except requests.RequestException as e:
        logger.error(f"Post request error: {e}")
        return {"status": "error", "message": f"Failed to communicate with WordPress: {str(e)}"}

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/test-wordpress-connection/")
async def test_connection(
    wp_url: str = Form(...),
    wp_username: str = Form(...),
    wp_app_password: str = Form(...)
):
    wp_config = WordPressConfig(
        wp_url=wp_url,
        username=wp_username,
        app_password=wp_app_password
    )
    result = await test_wordpress_connection(wp_config)
    return JSONResponse(content=result)

@app.post("/test-nebius-connection/")
async def test_nebius_connection(
    nebius_api_key: str = Form(...)
):
    try:
        client = get_openai_client(api_key=nebius_api_key)
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello in one word."}
            ],
            max_tokens=10
        )
        content = response.choices[0].message.content
        return JSONResponse(content={"status": "ok", "message": f"Connection successful: {content}"})
    except Exception as e:
        logger.error(f"Nebius API connection test failed: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)})

@app.post("/generate-and-post/")
async def generate_and_post(
    wp_url: str = Form(...),
    wp_username: str = Form(...),
    wp_app_password: str = Form(...),
    nebius_api_key: str = Form(...),
    main_topic: str = Form(...),
    keywords: str = Form(...),
    status: str = Form("draft"),
    categories: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    feature_image: Optional[UploadFile] = File(None),
    tone: str = Form("informative"),
    post_type: str = Form("article"),
    word_count: int = Form(800)
):
    # Create WordPress config
    wp_config = WordPressConfig(
        wp_url=wp_url,
        username=wp_username,
        app_password=wp_app_password
    )
    
    # Get OpenAI client
    client = get_openai_client(api_key=nebius_api_key)
    
    # Parse keywords into a list
    keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
    
    try:
        # Generate SEO content
        blog_content = generate_seo_blog_content(
            client=client,
            main_topic=main_topic,
            keywords=keyword_list,
            tone=tone,
            post_type=post_type,
            word_count=word_count
        )
        
        if not blog_content or "title" not in blog_content:
            return JSONResponse(content={"status": "error", "message": "Failed to generate content"})
        
        # Post to WordPress
        post_result = await post_to_wordpress(
            wp_config=wp_config,
            title=blog_content["title"],
            content=blog_content["content"],
            excerpt=blog_content["excerpt"],
            status=status,
            feature_image_file=feature_image,
            categories=categories,
            tags=tags
        )
        
        # Return combined results
        return JSONResponse(content={
            "generation": {
                "title": blog_content["title"],
                "excerpt": blog_content["excerpt"],
                "content_preview": blog_content["content"][:200] + "..."
            },
            "wordpress_post": post_result
        })
        
    except Exception as e:
        logger.error(f"Error in generate and post workflow: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)})

# Add additional routes as needed
@app.get("/api/health/")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)