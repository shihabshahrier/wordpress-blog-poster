import os
import re
import json
import base64
import argparse
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Any

# Load environment variables
load_dotenv()

class GoogleTrendsAnalyzer:
    def __init__(self, api_key: str = None):
        """Initialize Google Trends Analyzer with Nebius API key."""
        self.api_key = api_key or os.getenv("NEBIUS_API_KEY")
        if not self.api_key:
            raise ValueError("Nebius API key is required. Set NEBIUS_API_KEY environment variable or pass it directly.")
        
        self.client = OpenAI(
            base_url="https://api.studio.nebius.com/v1/",
            api_key=self.api_key
        )

    def encode_image(self, image_path: str) -> str:
        """Encode an image file into a base64 string."""
        image_path = Path(image_path)
        if not image_path.is_file():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")

    def clean_json_response(self, text: str) -> str:
        """Remove Markdown-style ```json ... ``` wrappers from model output."""
        match = re.search(r"```(?:json)?\n([\s\S]*?)\n```", text)
        if match:
            return match.group(1).strip()
        return text.strip()

    def parse_response(self, response_text: str) -> Dict[str, List[str]]:
        """Parse and clean model response text into a dictionary."""
        cleaned_text = self.clean_json_response(response_text)
        try:
            data = json.loads(cleaned_text)
            if isinstance(data, dict):
                return data
            else:
                raise ValueError("Parsed JSON is not a dictionary.")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}")

    def analyze_trends_screenshot(self, image_path: str) -> Dict[str, List[str]]:
        """Analyze a Google Trends screenshot and return extracted trends."""
        base64_image = self.encode_image(image_path)
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a professional data analyst specializing in interpreting Google Trends screenshots. "
                    "Extract all main trend titles and their associated keywords or trend breakdowns. "
                    "Return the extracted information in JSON format like: "
                    "{'Title1': ['keyword1', 'keyword2'], 'Title2': ['keyword1', 'keyword2'], ...}. "
                    "Only output valid JSON without any extra explanation or markdown."
                )
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze the following Google Trends screenshot and extract the trend titles and related keywords."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]

        response = self.client.chat.completions.create(
            model="google/gemma-3-27b-it-fast",
            max_tokens=512,
            temperature=0.5,
            top_p=0.9,
            extra_body={"top_k": 50},
            messages=messages
        )

        response_text = response.choices[0].message.content
        return self.parse_response(response_text)

def main():
    parser = argparse.ArgumentParser(description="Analyze Google Trends screenshot to extract trends and keywords.")
    parser.add_argument("image_path", type=str, help="Path to the Google Trends screenshot image")
    parser.add_argument("--api-key", type=str, help="Nebius API key (optional if set as environment variable)")
    args = parser.parse_args()

    try:
        analyzer = GoogleTrendsAnalyzer(api_key=args.api_key)
        result = analyzer.analyze_trends_screenshot(args.image_path)

        print("\n===== Google Trends Analysis Result =====")
        for title, keywords in result.items():
            print(f"\nTitle: {title}\nKeywords: {', '.join(keywords) if keywords else 'No keywords found'}")
        print("=========================================\n")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
