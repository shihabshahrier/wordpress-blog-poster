import os
from openai import OpenAI
from dotenv import load_dotenv
import logging
from typing import Dict, List, Tuple, Optional
import json
import time
import requests

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(
    base_url="https://api.studio.nebius.com/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY")
)

def generate_seo_blog_content(
    main_topic: str,
    keywords: List[str],
    tone: str = "informative",
    post_type: str = "article",
    word_count: int = 800,
    max_retries: int = 3,
    retry_delay: int = 2
) -> Dict[str, str]:
    """
    Generate SEO-optimized blog content with title, excerpt, and body
    
    Args:
        main_topic: The primary topic or focus of the blog post
        keywords: List of SEO keywords to incorporate
        tone: Desired tone of the content (informative, conversational, professional, etc.)
        post_type: Type of post (article, listicle, how-to guide, etc.)
        word_count: Approximate word count for the main content
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Dictionary containing title, excerpt, and content
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

def post_to_wordpress(
    title: str,
    content: str,
    excerpt: str,
    status: str = "draft",
    categories: Optional[List[int]] = None,
    tags: Optional[List[int]] = None,
    image_path: Optional[str] = None
) -> Dict:
    """
    Post content to WordPress using your existing API
    This function would integrate with your FastAPI endpoint
    """
    # Implementation to use your FastAPI endpoint
    api_url = "http://127.0.0.1:8000/post-blog/"

    form_data = {
        "title": title,
        "content": content,
        "excerpt": excerpt,
        "status": status,
        "categories": categories,
        "tags": tags
    }



    try:
        logger.info(f"Posting to WordPress: {title}")

        response = requests.post(

            api_url,
            form_data,
        )
    
        if response.status_code == 200:
            logger.info("Post created successfully!")
            return response.json()
        
        else:
            logger.error(f"Failed to create post: {response.status_code}")
            return {
                "status": "error",
                "message": response.text
            }
    except requests.RequestException as e:
        logger.error(f"An error occurred while posting to WordPress: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
    

# Example usage
if __name__ == "__main__":
    # Example parameters
    main_topic = "AI Tools for Content Marketing"
    keywords = ["AI content tools", "content marketing automation", "SEO optimization"]
    
    # Generate the content
    blog_post = generate_seo_blog_content(
        main_topic=main_topic,
        keywords=keywords,
        tone="professional",
        post_type="guide",
        word_count=1000
    )
    
    # Print the generated content
    if blog_post:
        print("TITLE:", blog_post['title'])
        print("\nEXCERPT:", blog_post['excerpt'])
        print("\nCONTENT PREVIEW:", blog_post['content'][:200] + "...")
        
        # You could then call your WordPress poster
        # post_to_wordpress(**blog_post)
    else:
        print("Failed to generate content")

    # post_to_wordpress(**blog_post)

    post = post_to_wordpress(
        title=blog_post['title'],
        content=blog_post['content'],
        excerpt=blog_post['excerpt'],
        status="publish",
    )

    print("Post response:", post)