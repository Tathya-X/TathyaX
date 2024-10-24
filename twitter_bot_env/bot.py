import os
from dotenv import load_dotenv
import tweepy
import openai
import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# API credentials
TWITTER_CONSUMER_KEY = os.getenv('TWITTER_CONSUMER_KEY')
TWITTER_CONSUMER_SECRET = os.getenv('TWITTER_CONSUMER_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_CSE_ID = os.getenv('GOOGLE_CSE_ID')

# After loading environment variables
logger.info("API keys loaded:")
logger.info(f"Twitter Consumer Key: {'*' * len(TWITTER_CONSUMER_KEY)}")
logger.info(f"OpenAI API Key: {'*' * len(OPENAI_API_KEY)}")
logger.info(f"Google API Key: {'*' * len(GOOGLE_API_KEY)}")

# Initialize API clients
auth = tweepy.OAuth1UserHandler(
    TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
)
api = tweepy.API(auth)
client = openai.OpenAI(api_key=OPENAI_API_KEY)

def generate_context(tweet_text):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Generate a search query to find context for this tweet."},
                {"role": "user", "content": tweet_text}
            ],
            max_tokens=50
        )
        search_query = response.choices[0].message.content
        
        search_url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_CSE_ID}&q={search_query}"
        search_results = requests.get(search_url).json()
        
        context = ""
        for item in search_results.get('items', [])[:3]:
            url = item['link']
            page = requests.get(url)
            soup = BeautifulSoup(page.content, 'html.parser')
            paragraph = soup.find('p')
            if paragraph:
                context += f"{paragraph.text}\n\n"
        
        return context.strip()
    except Exception as e:
        logger.error(f"Error generating context: {str(e)}")
        return None

def find_citations(tweet_text):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Identify key claims in this tweet that need citation."},
                {"role": "user", "content": tweet_text}
            ],
            max_tokens=100
        )
        key_claims = response.choices[0].message.content.split('\n')

        citations = []
        for claim in key_claims:
            search_url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_CSE_ID}&q={claim}"
            search_results = requests.get(search_url).json()

            if 'items' in search_results:
                top_result = search_results['items'][0]
                url = top_result['link']
                title = top_result['title']
                domain = urlparse(url).netloc
                citations.append(f"{claim}: {title} ({domain})")

        return citations
    except Exception as e:
        logger.error(f"Error finding citations: {str(e)}")
        return None

def fact_check_tweet(tweet_text):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a fact-checking assistant. Analyze the following tweet and provide a fact-check response."},
                {"role": "user", "content": tweet_text}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error fact-checking tweet: {str(e)}")
        return None

def compose_detailed_reply(fact_check_result, context, citations):
    reply = f"Fact check: {fact_check_result}\n\nContext: {context[:100]}...\n\nCitations:\n"
    for citation in citations[:2]:
        reply += f"- {citation}\n"
    return reply[:280]  # Ensure the reply fits in a tweet

def test_bot():
    test_tweet = "Elon Musk comes out of the closet and says he is gay"
    
    print(f"Testing with tweet: '{test_tweet}'")
    
    fact_check_result = fact_check_tweet(test_tweet)
    context = generate_context(test_tweet)
    citations = find_citations(test_tweet)
    
    if fact_check_result and context and citations:
        reply = compose_detailed_reply(fact_check_result, context, citations)
        print(f"\nGenerated reply:\n{reply}")
    else:
        print("Failed to generate a complete response.")

if __name__ == "__main__":
    test_bot()
