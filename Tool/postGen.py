from feedparser import parse
import pandas as pd
import libsql_experimental as libsql
import os,urllib3,json
from dotenv import load_dotenv, find_dotenv
import datetime
import random


def get_random_gradient(dark=0):
    def random_hue():
        return random.randint(0, 359)

    def random_saturation():
        return random.randint(0, 100)

    def random_lightness():
        return random.randint(60, 96)

    fixed_lightness = 60 if dark else 96

    color1 = f'hsl({random_hue()}, {random_saturation()}%, {fixed_lightness}%)'
    color2 = f'hsl({random_hue()}, {random_saturation()}%, {fixed_lightness}%)'
    color3 = f'hsl({random_hue()}, {random_saturation()}%, {fixed_lightness}%)'

    angle = random.randint(0, 359)

    gradient_type = random.choice(['linear', 'radial'])

    if gradient_type == 'linear':
        return f'linear-gradient({angle}deg, {color1}, {color2}, {color3})'
    else:
        centerX = random.randint(0, 100)
        centerY = random.randint(0, 100)
        return f'radial-gradient(circle at {centerX}% {centerY}%, {color1}, {color2}, {color3})'


# Example usage
print(get_random_gradient())

# Load environment variables
load_dotenv(find_dotenv())
http = urllib3.PoolManager()
def get_rss_df(rss_url: str) -> pd.DataFrame:
    """Fetch and parse the RSS feed, returning a DataFrame of the entries."""
    feed = parse(rss_url)
    df = pd.json_normalize(feed.entries)
    ##reverse df
    df = df.reindex(index=df.index[::-1])
    return df


def generate_tweet_style_content_and_tags(title: str, description: str) -> (str, str):
    """Generate tweet-style content and tags using OpenAI GPT-4 API."""
    prompt = (
        f"Convert the following title and description into a tweet-style content "
        f"and categorize the product. Output should be a Python dictionary format "
        f"with keys 'content' and 'tags':\n\n"
        f"Title: {title}\n"
        f"Description: {description}\n\n"
        f"Output:"
    )

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}'
    }

    data = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 150
    }

    response = http.request(
        'POST',
        f'{os.getenv("API_BASE_URL")}/chat/completions',
        body=json.dumps(data),
        headers=headers
    )

    result = json.loads(response.data.decode('utf-8'))
    content = result['choices'][0]['message']['content'].strip()

    # Log the generated content for debugging
    print(f"Generated content: {content}")

    try:
        output_dict = eval(content)  # Evaluate the string as a Python expression
        tweet_content = output_dict.get('content', '').strip()
        tags = output_dict.get('tags', [])
        if isinstance(tags, list):
            tags = ','.join(tags)
        else:
            tags = str(tags)
    except Exception as e:
        print(f"Error parsing the generated content: {e}")
        tweet_content = content
        tags = "general"

    return tweet_content, tags


def send2turso(df: pd.DataFrame):
    """Send DataFrame entries to the Turso database."""
    url = os.getenv("TURSO_DATABASE_URL")
    auth_token = os.getenv("TURSO_AUTH_TOKEN")
    conn = libsql.connect("next-articles.db", sync_url=url, auth_token=auth_token)

    # Ensure table exists
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS note (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link TEXT NOT NULL,
        title TEXT NOT NULL,
        tags TEXT,
        dark INTEGER NOT NULL DEFAULT 0,
        css TEXT,
        content TEXT NOT NULL,
        createdAt REAL NOT NULL DEFAULT (strftime('%s','now')),
        updatedAt REAL DEFAULT (strftime('%s','now')),
        authorId TEXT NOT NULL,
        usedcount INTEGER NOT NULL DEFAULT 0
    );
    """
    conn.execute(create_table_sql)

    # Insert DataFrame data into the database
    for index, row in df.iterrows():
        title = row.get('title', 'No Title')
        dark = random.choice([0, 1])
        css = get_random_gradient(dark)
        description = row.get('description', '')
        created_at = datetime.datetime.strptime(row.get('published', datetime.datetime.utcnow().isoformat()),
                                                '%a, %d %b %Y %H:%M:%S %z').timestamp()
        updated_at = datetime.datetime.utcnow().timestamp()
        author_id = 987654321

        # Generate tweet-style content and tags
        tweet_content, tags = generate_tweet_style_content_and_tags(title, description)
        insert_sql = """
        INSERT INTO note (title, tags, dark, css, content, createdAt, updatedAt, authorId) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        conn.execute(insert_sql, (title, tags, dark, css, tweet_content, created_at, updated_at, author_id))

    conn.commit()

def rss2turso(url: str):
    """Fetch RSS feed and store its entries into Turso database."""
    df = get_rss_df(url)
    send2turso(df)


# Example usage
if __name__ == '__main__':
    rss_url = 'https://www.dealnews.com/?rss=1&sort=time'
    rss2turso(rss_url)
