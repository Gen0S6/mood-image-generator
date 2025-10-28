import streamlit as st
import requests
import random
from PIL import Image, ImageDraw, ImageFont
import requests.exceptions
import os
import datetime
from openai import OpenAI
import re
import base64
import io
from langdetect import detect  # Restored for language detection

# Replace with your keys
UNSPLASH_ACCESS_KEY = 'ws6OVordNuNogW3Iwo34IRlrMHU0jabQnjooaqKGFM0'
OPENAI_API_KEY = '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'
PEXELS_API_KEY = 'qJ8RyQKAEKudOH0iLFeKu2DjfAjYpgWXHXLoELb0JGOtKKQIHyN3hCj8'  # Optional, get from https://www.pexels.com/api/

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def analyze_mood_with_openai(mood_input):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an emotion analyst. Provide ONLY 5-7 keywords for aesthetic photo searches, emphasizing action, adventure, or mood-specific themes (e.g., 'thrill', 'journey', 'exploration', 'adventure', 'excitement', 'dynamic', 'outdoors'), separated by commas. Do not include explanations or narratives."},
                {"role": "user", "content": f"Mood: {mood_input}"}
            ],
            max_tokens=50
        )
        content = response.choices[0].message.content.strip()
        keywords = re.search(r'^(?:[^,]+,){4,6}[^,]+$', content)
        if keywords:
            return [kw.strip() for kw in content.split(',') if kw.strip()]
        else:
            st.warning("Unexpected keyword format from OpenAI. Using default keywords.")
            return mood_input.lower().split()
    except Exception as e:
        st.error(f"OpenAI analysis error: {e}. Using default keywords.")
        return mood_input.lower().split()

def summarize_mood_with_openai(mood_input):
    try:
        if len(mood_input) <= 50:  # Threshold for summarization
            return mood_input.capitalize()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a text summarizer. Provide a concise title (exactly 2-5 words) summarizing the mood text, reflecting its key emotions and themes, in the same language as the input. Ensure the output is exactly 2-5 words."},
                {"role": "user", "content": f"Mood: {mood_input}"}
            ],
            max_tokens=20
        )
        summary = response.choices[0].message.content.strip().capitalize()
        words = summary.split()
        if 2 <= len(words) <= 5:
            return summary
        elif len(words) > 5:
            return ' '.join(words[:5])  # Truncate to 5 words
        else:
            return ' '.join(words + ['...'] * (2 - len(words)))  # Pad to 2 words
        print(f"Summary generated: {summary}")  # Debug output
    except Exception as e:
        st.error(f"OpenAI summarization error: {e}. Using truncated text.")
        return mood_input.capitalize()[:50] + "..." if len(mood_input) > 50 else mood_input.capitalize()

def deep_analysis_with_openai(mood_input, lang_override=None):
    try:
        # Detect language with a minimum length check
        lang = lang_override if lang_override else detect(mood_input) if len(mood_input) > 10 else 'en'
        print(f"Detected language: {lang}")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are an emotion analyst. Provide a deep, concise analysis of the mood text in 3-5 sentences, starting with a natural introductory phrase tailored to the mood and in the same language as the input (detected as {lang}). Highlight key emotions, themes, and nuances without exceeding 150 tokens."},
                {"role": "user", "content": f"Mood: {mood_input}"}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"OpenAI deep analysis error: {e}. No analysis available.")
        return "No deep analysis available due to error."


    
def encode_image(image_url):
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        img = Image.open(response.raw)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            st.error(f"Rate limit hit for image download: {e}. Skipping this image.")
        else:
            st.error(f"Error encoding image: {e}")
        return None
    except Exception as e:
        st.error(f"Error encoding image: {e}")
        return None

def score_image_with_openai(mood_input, image_url):
    try:
        base64_image = encode_image(image_url)
        if not base64_image:
            return 0
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a visual mood analyst. Score this image from 1-10 based on how well it matches the mood, prioritizing vibrant colors and dynamic motion (e.g., flowing water, active figures) for 'exhilarating anticipation', dramatic skies or tense compositions for 'apprehension', and serene landscapes or soft lighting for 'serenity'. Provide only the score as a number."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Mood: {mood_input}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=10
        )
        score = int(response.choices[0].message.content.strip())
        return max(0, min(10, score))  # Ensure score is between 0 and 10
    except Exception as e:
        st.error(f"OpenAI image scoring error: {e}")
        return 0

def select_best_image_with_openai(mood_input, photos):
    if not photos:
        return None
    
    descriptions = [photo.get('alt_description', 'No description') for photo in photos]
    prompt = f"Mood: {mood_input}. Provide a numbered list (1 to {len(descriptions)}) with a score from 1-10 for each description based on text alone, prioritizing excitement, adventure, or serenity. Conclude with 'Best is #X' where X is a number. Follow this format:\n- 1. [Description] - [Score]\n...\nBest is #X. Descriptions:\n" + "\n".join(f"- {i+1}. {desc}" for i, desc in enumerate(descriptions))
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250
        )
        content = response.choices[0].message.content.strip()
        print(f"OpenAI text response: {content}")
        
        match = re.search(r"Best is #(\d+)", content)
        if match:
            best_index = int(match.group(1)) - 1
            if 0 <= best_index < len(photos):
                top_indices = [best_index]
            else:
                top_indices = list(range(min(2, len(photos))))  # Reduced to top 2
        else:
            top_indices = list(range(min(2, len(photos))))  # Reduced to top 2
        
        scores = {}
        for index in top_indices:
            scores[index] = score_image_with_openai(mood_input, photos[index]['urls']['regular'])
        print(f"Image scores: {scores}")
        
        best_index = max(scores, key=scores.get)
        print(f"Selected best index: {best_index + 1} (Score: {scores[best_index]})")
        return photos[best_index]
    
    except Exception as e:
        st.error(f"OpenAI selection error: {e}. Picking random image.")
        return random.choice(photos)

def get_mood_image(mood_input, lang_override=None):
    try:
        keywords = analyze_mood_with_openai(mood_input)
        print(f"Generated keywords: {keywords}")
        
        photos = []
        # Try Unsplash first
        query_options = [
            'aesthetic ' + ' '.join(keywords) + ' adventure outdoors',
            'aesthetic ' + ' '.join(keywords) + ' journey action',
            'aesthetic ' + ' '.join(keywords) + ' dynamic scene'
        ]
        for i, query in enumerate(query_options, 1):
            url = 'https://api.unsplash.com/search/photos'
            params = {
                'query': query,
                'per_page': 20,
                'client_id': UNSPLASH_ACCESS_KEY
            }
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                print(f"Unsplash Query {i} ('{query}'): {len(data['results'])} images fetched")
                photos.extend(data['results'])
                if len(photos) >= 20:
                    break
            except requests.exceptions.RequestException as e:
                st.warning(f"Unsplash failed: {e}. Trying Pexels...")
                break
        
        # Try Pexels if Unsplash fails or not enough images
        if len(photos) < 10 and PEXELS_API_KEY:
            query = ' '.join(keywords) + ' nature adventure'
            url = 'https://api.pexels.com/v1/search'
            headers = {'Authorization': PEXELS_API_KEY}
            params = {'query': query, 'per_page': 20, 'page': 1}
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                print(f"Pexels Query ('{query}'): {len(data['photos'])} images fetched")
                photos = [{'urls': {'regular': photo['src']['original']}, 'alt_description': photo['alt']} for photo in data['photos']]
            except requests.exceptions.RequestException as e:
                st.warning(f"Pexels failed: {e}. Falling back to Unsplash if possible...")
                if len(photos) == 0 and UNSPLASH_ACCESS_KEY:
                    # Retry Unsplash with a simpler query
                    query = ' '.join(keywords) + ' nature'
                    url = 'https://api.unsplash.com/search/photos'
                    params = {'query': query, 'per_page': 20, 'client_id': UNSPLASH_ACCESS_KEY}
                    try:
                        response = requests.get(url, params=params)
                        response.raise_for_status()
                        data = response.json()
                        print(f"Unsplash Fallback Query ('{query}'): {len(data['results'])} images fetched")
                        photos.extend(data['results'])
                    except requests.exceptions.RequestException as e:
                        st.error(f"Unsplash fallback failed: {e}. No images available.")

        if not photos:
            return None, "No matching images found. Try different words like 'happy day' or 'calm sea'!"
        
        print(f"Total photos fetched: {len(photos)}")
        best_photo = select_best_image_with_openai(mood_input, photos)
        if not best_photo:
            return None, "Error selecting best image."
        
        image_url = best_photo['urls']['regular']
        # Handle attribution based on source
        if 'user' in best_photo:
            photographer = best_photo['user']['name']
            unsplash_link = best_photo['links']['html']
            attribution = f"Photo by {photographer} on Unsplash ({unsplash_link})"
        else:
            photographer = best_photo.get('photographer', 'Unknown')
            attribution = f"Photo by {photographer} on Pexels (https://www.pexels.com/photo/{best_photo.get('id', 'unknown')})"
        mood_text = summarize_mood_with_openai(mood_input)
        
        # Generate deep analysis with language override
        deep_analysis = deep_analysis_with_openai(mood_input, lang_override)
        print(f"Deep analysis: {deep_analysis}")
        
        return image_url, {
            'mood_text': mood_text,
            'attribution': attribution,
            'deep_analysis': deep_analysis
        }
    
    except Exception as e:
        return None, f"Error fetching image: {e}"

def overlay_text(image_url, mood_text):
    try:
        import tempfile
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        img = Image.open(response.raw)
        
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
        except IOError as e:
            print(f"Font error: {e}. Using default font.")
            font = ImageFont.load_default()
        
        draw.text((10, 10), mood_text, fill="white", font=font)
        
        # Use a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            img.save(tmp_file, format='JPEG')
            temp_path = tmp_file.name
        
        # Delete the file after use (Streamlit will display it before deletion)
        import atexit
        def cleanup():
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        atexit.register(cleanup)
        
        return temp_path
    
    except Exception as e:
        return f"Error processing image: {e}"

def deep_analysis_with_openai(mood_input, lang_override=None):
    try:
        # Detect language with improved reliability
        if len(mood_input) > 15:  # Increased minimum length
            from langdetect import detect_langs
            langs = detect_langs(mood_input)
            lang = langs[0].lang if langs and langs[0].prob > 0.8 else 'en'  # Use if confidence > 80%
        else:
            lang = 'en'  # Default to English for short inputs
        if lang_override and lang_override != "Auto":
            lang = lang_override.lower()
        print(f"Detected language: {lang}")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are an emotion analyst. Provide a deep, concise analysis of the mood text in 3-5 sentences, starting with a natural introductory phrase tailored to the mood and in the same language as the input (detected as {lang}). Highlight key emotions, themes, and nuances without exceeding 150 tokens."},
                {"role": "user", "content": f"Mood: {mood_input}"}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"OpenAI deep analysis error: {e}. No analysis available.")
        return "No deep analysis available due to error."

# Streamlit app
if "loading" not in st.session_state:
    st.session_state.loading = False
st.title("Mood Image Generator")
st.markdown(
    """
    <style>/* Dark theme */
body {
  background-color: #1a1a1a;
  color: #ffffff;
}
.stApp {
  background-color: #1a1a1a;
}

/* Custom font from Google Fonts */
@import url("https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap");
.stApp * {
  font-family: "Roboto", sans-serif;
}

/* Title styling */
.css-1d391kg {
  /* Center the title */
  text-align: center;
  font-size: 2.5em;
  color: #e0e0e0;
  margin-bottom: 20px;
}

/* Input and button styling */
.stTextInput > div > div > input {
  background-color: #2c2c2c;
  color: #ffffff;
  border: 1px solid #444;
  border-radius: 5px;
  padding: 5px;
}
.stButton > button {
  background-color: #4a90e2;
  color: #ffffff;
  border: none;
  border-radius: 5px;
  padding: 10px 20px;
  font-size: 1em;
  transition: background-color 0.3s;
}
.stButton > button:hover {
  background-color: #357abd;
}

/* Select box styling */
.stSelectbox > div > div > select {
  background-color: #2c2c2c;
  color: #ffffff;
  border: 1px solid #444;
  border-radius: 5px;
  padding: 5px;
  width: 100px; /* Compact size */
}

/* Caption and text styling */
.stImage > figcaption {
  color: #cccccc;
  font-size: 0.9em;
  text-align: center;
}
.stMarkdown {
  color: #e0e0e0;
  font-size: 1em;
}

/* Spacing and layout */
.stApp > div {
  padding: 20px;
}
.element-container {
  margin-bottom: 15px;
}

/* Flashing note during loading */
    .stMarkdown.note {
        animation: flash 1s infinite;
    }
    @keyframes flash {
        0% { opacity: 1; }
        50% { opacity: 0.3; }
        100% { opacity: 1; }
    }
</style>
    """,
    unsafe_allow_html=True
)
st.write("Enter your mood or thoughts, and get an aesthetic image with a personalized message! AI analyzes complex feelings and images.")

col1, col2 = st.columns([3, 1])  # 3 parts for input, 1 part for select
with col1:
    mood_input = st.text_input("How are you feeling today?", placeholder="As I stand at the crossroads of my life...", key="mood_input")
with col2:
    lang_override = st.selectbox("Language", ["Auto", "English", "French", "Spanish", "German", "Italian"], key="lang_select")

if st.button("Generate Image"):
    image_url, result = get_mood_image(mood_input, lang_override=lang_override if lang_override != "Auto" else None)
    
    if image_url:
        output_path = overlay_text(image_url, result['mood_text'])
        if isinstance(output_path, str) and os.path.exists(output_path):
            st.image(output_path, caption=result['mood_text'], use_container_width=True)
            st.write(f"**Credit:** {result['attribution']}")
            st.write("**Deep Mood Analysis:**")
            st.write(result['deep_analysis'])
        else:
            st.error(output_path)
    else:
        st.error(result)

note_text="Note: Images from Unsplash or Pexels with attribution. OpenAI analyzes emotions and images."
st.markdown(f'<div class="stMarkdown note" {"style='animation: none;'" if not st.session_state.loading else ""}>{note_text}</div>', unsafe_allow_html=True)