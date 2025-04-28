# WordPress SEO Content Generator and Poster

A full-stack application to automatically generate SEO-optimized content using AI and post it directly to your WordPress site.

## Features

- Generate SEO-optimized blog content with AI (using Nebius DeepSeek-V3 model)
- Automatically post content to WordPress via the REST API
- Upload feature images for posts
- Set post categories and tags
- Configure tone, content type, and word count
- Test connections to WordPress and AI services before posting

## Prerequisites

- Python 3.8+ installed
- A WordPress site with REST API enabled
- WordPress application password for authentication
- Nebius API key for AI content generation

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd wordpress-seo-generator
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the dependencies:
   ```
   pip install fastapi uvicorn python-multipart requests python-dotenv openai
   ```

4. Create the directory structure:
   ```
   mkdir -p templates static
   ```

5. Create the files according to the project structure below.

## Project Structure

```
wordpress-seo-generator/
├── main.py              # FastAPI application
├── templates/
│   └── index.html       # Frontend HTML template
├── static/
│   └── styles.css       # CSS styles
├── .env                 # Environment variables (create this)
└── README.md            # This file
```

## Environment Variables

Create a `.env` file in the root directory with the following variables (these can also be set in the web interface):

```
WP_URL=https://yourwordpresssite.com
WP_USERNAME=your_username
WP_APP_PASSWORD=your_app_password
NEBIUS_API_KEY=your_nebius_api_key
```

## Running the Application

1. Start the FastAPI server:
   ```
   uvicorn main:app --reload
   ```

2. Open your browser and navigate to:
   ```
   http://127.0.0.1:8000/
   ```

3. Fill in the required fields and click "Generate & Post Content"

## WordPress Configuration

To use this application, you'll need to set up an application password in WordPress:

1. Go to your WordPress admin panel
2. Navigate to Users → Profile
3. Scroll down to "Application Passwords"
4. Enter a name (e.g., "SEO Content Generator") and click "Add New"
5. Copy the generated password and use it in this application

