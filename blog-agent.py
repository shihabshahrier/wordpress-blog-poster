import os
from openai import OpenAI
from dotenv import load_dotenv
import time
import logging

# Load environment variables
load_dotenv()

# Set up logging for error handling
logging.basicConfig(level=logging.INFO)

client = OpenAI(
    base_url="https://api.studio.nebius.com/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY")
)

# Generate SEO-Optimized Content using OpenAI
def generate_seo_content(title_keywords, seo_keywords):
    # Create a prompt for OpenAI to generate SEO-friendly title and content
    prompt = f"""
    I want you to create an SEO-optimized blog post. Here are the details:
    - The title should be short, catchy, and SEO-friendly, based on these keywords: {', '.join(title_keywords)}.
    - Include these SEO keywords in the body content: {', '.join(seo_keywords)}.
    - Ensure the title is 6-8 words long.
    - Write a compelling, informative, and valuable body content.
    - Maintain an optimal keyword density (1-2% for each keyword).
    - Use headers (H2, H3) to structure the post and make it SEO-friendly.
    """

    try:
        # Create a messages object for the chat API
        messages = [{"role": "system", "content": "You are an expert in SEO content generation."},
                    {"role": "user", "content": prompt}]

        # Call OpenAI API for content generation
        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3",  # or use a different model based on your preference
            messages=messages,  # Pass the messages here
            max_tokens=1500,  # Adjust the number of tokens based on your needs
            temperature=0.7,
            top_p=0.95
        )
    except Exception as e:
        logging.error(f"Error during API call: {e}")
        return "Error generating content", ""

    return response

        # Extracting the response content
        # content = response['choices'][0]['message']['content'].strip()
        
        # # Ensure response is in the expected format
        # if "\n" not in content:
        #     raise ValueError("The response format is incorrect, no newline detected.")

        # title, body = content.split("\n", 1)
        # return title.strip(), body.strip()

    # except Exception as e:
    #     logging.error(f"Error generating SEO content: {e}")
    #     # Retry logic if desired
    #     for attempt in range(3):
    #         time.sleep(2)  # Wait before retrying
    #         try:
    #             logging.info(f"Retrying... Attempt {attempt + 1}")
    #             return generate_seo_content(title_keywords, seo_keywords)
    #         except Exception as retry_error:
    #             logging.error(f"Retry failed: {retry_error}")
    #     return "Error generating content", ""

# Example execution
if __name__ == "__main__":
    title_keywords = ["AI", "SEO", "Blogging"]
    seo_keywords = ["artificial intelligence", "SEO optimization", "blogging tips"]

    # title, body 
    res = generate_seo_content(title_keywords, seo_keywords)
    print(res)
    # if title and body:
    #     logging.info(f"Generated Title: {title}")
    #     logging.info(f"Generated Body: {body}")
    # else:
    #     logging.error("Failed to generate content.")
