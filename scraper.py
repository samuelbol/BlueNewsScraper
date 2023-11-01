import asyncio
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from bs4 import BeautifulSoup
from pyppeteer import launch
from pytz import utc
from keep_alive import keep_alive
import os

BOT_TOKEN = ${{ sercets.BOT_TOKEN }}
CHAT_ID = ${{ secrets.CHAT_ID }}
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

keep_alive()

async def scrape_cfc_official():
    browser = await launch()
    page = await browser.newPage()

    await page.goto("https://www.chelseafc.com/en/news/category/mens-team")
    await page.waitForSelector('.news-card.news-card--article')

    html_content = await page.content()

    soup = BeautifulSoup(html_content, 'html.parser')

    card_list = soup.find_all("div", class_="news-card news-card--article")
    news_items = []
    no_news = ['chelsea vs', 'live streaming chelsea vs', 'prediction, betting tips, odds & preview',
               'predicted line up', 'where to watch, tv channel, kick-off time, date']

    for card in card_list[:3]:
        try:
            crd_img = card.find("img")['data-src']
            crd_title = card.find("a", class_="news-card__floating-link")['title']
            crd_link = f"https://www.chelseafc.com{card.find('a', class_='news-card__floating-link')['href']}"
            print(crd_link)

            if not crd_link or not crd_title or not crd_img:
                continue

            if any(no_new in crd_title.lower() for no_new in no_news):
                continue

            try:
                with open("logfile.txt", "r", encoding='utf-8') as file:
                    saved_titles = [line.rstrip("\n") for line in file.readlines()]
                    if crd_title in saved_titles:
                        continue
            except FileNotFoundError:
                pass

            await page.goto(crd_link)
            await page.waitForSelector('p')

            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')

            p_list = soup.find_all("p")
            crd_summary = ''.join([p.get_text(strip=True) + '\n\n' for p in p_list[:4]])

            news_items.append({"title": crd_title, "summary": crd_summary, "image": crd_img})

        except AttributeError:
            pass

    await browser.close()
    return news_items

# Function to send news to Telegram
def send_news_to_telegram(article_items):
    for item in article_items:
        title_ = item.get("title", "")
        contents = item.get("summary", "")
        img_ = item.get("image", "")

        # Check if any of the required data is missing
        if not title_ or not contents:
            print("Skipping item due to missing data.")
            continue

        message = f"📰 *{title_}*\n\n{contents}\n" \
                  f"*🔗 ChelseaFC*\n\n" \
                  f"📲 @JustCFC"
        # print(message)

        try:
            with open("logfile.txt", "r", encoding='utf-8') as file:
                saved_titles = [line.rstrip("\n") for line in file.readlines()]
        except FileNotFoundError:
            saved_titles = []

        if title_ not in saved_titles:
            response = requests.post(BASE_URL + "sendPhoto",
                                     json={
                                         "chat_id": CHAT_ID,
                                         "disable_web_page_preview": False,
                                         "parse_mode": "Markdown",
                                         "caption": message,
                                         "photo": img_
                                     })
            # Check the response status
            if response.status_code == 200:
                print("Message sent successfully.")

                with open("logfile.txt", "a", encoding='utf-8') as file:
                    file.write(f"{title_}\n")

            else:
                print(
                    f"Message sending failed. Status code: {response.status_code}"
                )

def main():
    loop = asyncio.get_event_loop()
    news_items = loop.run_until_complete(scrape_cfc_official())
    send_news_to_telegram(news_items)

scheduler = BlockingScheduler(timezone=utc)
scheduler.add_job(main, "interval", minutes=5)
scheduler.start()

