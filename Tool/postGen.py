from feedparser import parse
import pandas as pd
import libsql_experimental as libsql
import os,urllib3,json
from dotenv import load_dotenv, find_dotenv
import datetime
import random
import ast
import requests

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


def fetch_avatar_data(list_id, authorization):
    base_url = f'http://{os.environ["LOCALHOST"]}:8080/i/lists/{list_id}/members'
    headers = {
        'Authorization': authorization,
    }
    results = []
    next_cursor = None
    while True:
        url = f'{base_url}?cursor={next_cursor}' if next_cursor else base_url
        print(url)
        response = requests.get(url, headers=headers, verify=False)
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        avatars = soup.find_all('a', class_='tweet-avatar')
        for a in avatars:
            img_tag = a.find('img')
            if img_tag:
                href = a['href'][1:]
                src = img_tag['src']
                parsed_src = urllib.parse.unquote(src)
                if parsed_src.startswith('/pic/'):
                    parsed_src = ((parsed_src.replace('/pic/', 'https://')
                                   .replace('_bigger', '_normal'))
                                  .replace('https://pbs.twimg.com/profile_images/', ''))
                results.append((href, parsed_src))
        load_more_div = soup.find_all('div', class_='show-more')
        if len(load_more_div) > 0:
            load_more_div = load_more_div[-1]
        else:
            break
        if load_more_div:
            load_more_link = load_more_div.find('a')
            if load_more_link and 'cursor' in load_more_link['href']:
                next_cursor = load_more_link['href'].split('cursor=')[1]
                time.sleep(1)
            else:
                break
        else:
            break

    if len(results) > 0:
        conn = libsql.connect("notes.db", sync_url=os.getenv("TURSO_DATABASE_URL"),
                              auth_token=os.getenv("TURSO_AUTH_TOKEN"))
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS avatars (
                twitterId TEXT PRIMARY KEY,
                imgSrc TEXT NOT NULL
            )
            ''')
        cursor.executemany('''
                INSERT OR REPLACE INTO avatars (twitterId, imgSrc) VALUES (?, ?)
                ''', results)
        conn.commit()

def generate_tweet_style_content_and_tags(title: str, description: str) -> (str, str):
    """Generate tweet-style content and tags using OpenAI GPT-4 API."""
    prompt = (
        f"Convert the following title and description into a tweet-style content "
        f"and categorize the product. Output should be only a Python dictionary "
        f"with keys 'content' ,'category'(one of [fashion, food, beauty, digital, other]) and 'tags':\n\n"
        f"Title: {title}\n"
        f"Description: {description}\n\n"
        f"Output:"
    )

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}'
    }

    data = {
        "model": "gpt-4o",
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

    output_dict = ast.literal_eval(content.strip('```python').strip())  # Evaluate the string as a Python expression
    print(output_dict)
    tweet_content = output_dict.get('content', '').strip()
    tags = output_dict.get('tags', [])
    category = output_dict.get('category', 'Uncategorized').strip()
    if isinstance(tags, list):
        tags = ','.join(tags)
    else:
        tags = str(tags)


    return tweet_content, category, tags


def send2turso(df: pd.DataFrame):
    """Send DataFrame entries to the Turso database."""
    url = os.getenv("TURSO_DATABASE_URL")
    auth_token = os.getenv("TURSO_AUTH_TOKEN")
    conn = libsql.connect("notes.db", sync_url=url, auth_token=auth_token)

    # Ensure table exists
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS note (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link TEXT NOT NULL,
        title TEXT NOT NULL,
        category TEXT,
        tags TEXT,
        dark INTEGER NOT NULL DEFAULT 0,
        textalign INTEGER NOT NULL DEFAULT 0,
        css TEXT,
        content TEXT NOT NULL,
        inspiration TEXT,
        createdAt REAL NOT NULL DEFAULT (strftime('%s','now')),
        updatedAt REAL DEFAULT (strftime('%s','now')),
        userId TEXT NOT NULL,
        authorId TEXT NOT NULL,
        usedcount INTEGER NOT NULL DEFAULT 0
    );
    """
    conn.execute(create_table_sql)

    # Insert DataFrame data into the database
    for index, row in df.iterrows():
        title = row.get('title', 'No Title')
        link = row.get('link', '')
        dark = random.choice([0, 1])
        textalign = random.choice([0, 1, 2])
        css = get_random_gradient(dark)
        description = row.get('description', '')
        created_at = datetime.datetime.strptime(row.get('published', datetime.datetime.utcnow().isoformat()),
                                                '%a, %d %b %Y %H:%M:%S %z').timestamp()
        updated_at = datetime.datetime.utcnow().timestamp()
        user_id = row.get('userId', 'defaultUserId')
        author_id = row.get('authorId', 'defaultAuthorId')
        usedcount = row.get('usedcount', 0)

        # Generate tweet-style content and tags
        tweet_content, category, tags = generate_tweet_style_content_and_tags(title, description)

        insert_sql = """
        INSERT INTO note (link, title, category, tags, dark, textalign, css, content, inspiration, createdAt, updatedAt, userId, authorId, usedcount) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        conn.execute(insert_sql, (
        link, title, category, tags, dark, textalign, css, tweet_content, description, created_at, updated_at, user_id,
        author_id, usedcount))

    conn.commit()

def llm(prompt:str):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.getenv("LLM_API_KEY")}'
    }
    print(os.getenv("LLM_BAK_MODEL"))
    data = {
        "model": os.getenv("LLM_BAK_MODEL"),
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user",
             "content": prompt}
        ],
        "stream": False
    }
    response = requests.post(
        f'{os.getenv("API_BASE_URL")}/chat/completions',
        headers=headers,
        data=json.dumps(data)
    )
    result = response.json()
    content = result['choices'][0]['message']['content'].strip()
    print(content)
    return content

def coze2api(prompt:str):
    url = f'http://{os.environ["LOCALHOST"]}:7077/v1/chat/completions'
    print(url)
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {os.environ["COZE2API_SECRET"]}',
        'Content-Type': 'application/json'
    }
    data = {
        'channelId': os.environ['COZE2API_CHN'],
        'messages': [{'role': 'user', 'content': prompt}],
        'model': 'gpt-4o',
        'stream': True
    }
    complete_response = ""
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), stream=True)
        for line in response.iter_lines():
            if line:
                try:
                    line = line.decode('utf-8')
                    if line.startswith("data: "):
                        line = line[6:]
                    chunk = json.loads(line)
                    if 'choices' in chunk:
                        for choice in chunk['choices']:
                            if 'delta' in choice and 'content' in choice['delta']:
                                complete_response += choice['delta']['content']
                except json.JSONDecodeError as e:
                    print("JSON decode error:", e)
    except Exception as e:
        print("An unexpected error occurred:", e)
    return complete_response

def chat2api(prompt:str):
    url = f"http://{os.environ['LOCALHOST']}:6677/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['CHAT2API_AUTHTOKEN']}"
    }
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    response = requests.post(url, headers=headers, json=data, stream=False)
    return response.json()["choices"][0]["message"]["content"]


def dealAnswer(answer:str):
    for lang in ["json","python"]:
        if f"```{lang}" not in answer:
            continue
        checkstring = answer.split(f"```{lang}")[1]
        if "```" in checkstring:
            print(checkstring.split("```")[0])
            return json.loads(checkstring.split("```")[0])

def comment(rss_url: str, length: int = 10):
    feed = parse(rss_url)
    entry_list = [f'[{e.published} {e.author}:]({e.link}) {e.title}' for e in feed.entries if
                  not e.title.startswith('RT by @') and not e.title.startswith('R to @')]
    rss = '\n\n'.join(entry_list[:length])
    instruct = 'pick the most creative idea from the tweets above, and make a question or praise to comment it with emoji, output in json format like [{"tweetUrl":"url1","comment":"xxx"},{"tweetUrl":"url1","comment":"xxx"}...]'
    prompt = rss + '\n\n' + instruct
    # comments = None
    # try:
    #     answer = coze2api(prompt)
    #     print(answer)
    #     comments = dealAnswer(answer)
    # except Exception as e:
    #     print('coze2api error', e)
    #     pass
    #
    # if comments is None:
    #     try:
    #         answer = chat2api(prompt)
    #         print(answer)
    #         comments =  dealAnswer(answer)
    #     except Exception as e:
    #         print('chat2api error', e)
    #         pass

    answer = llm(prompt)
    comments = dealAnswer(answer)
    comment_dict = {comment['tweetUrl']: comment['comment'] for comment in comments}
    entries_with_comments = []

    for entry in feed.entries:
        if entry.link in comment_dict:
            entries_with_comments.append({
                'entry': entry,
                'comment': comment_dict[entry.link]
            })

    return entries_with_comments


def rss2turso(url: str):
    """Fetch RSS feed and store its entries into Turso database."""
    df = get_rss_df(url)
    send2turso(df)


# Example usage
if __name__ == '__main__':
    rss_url = 'https://www.dealnews.com/?rss=1&sort=time'
    rss2turso(rss_url)
