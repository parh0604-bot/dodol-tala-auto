import sys
import requests
import questionary
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logo = """
    
     /$$      /$$                                        
    | $$$    /$$$                                        
    | $$$$  /$$$$  /$$$$$$  /$$$$$$$   /$$$$$$  /$$   /$$
    | $$ $$/$$ $$ /$$__  $$| $$__  $$ /$$__  $$| $$  | $$
    | $$  $$$| $$| $$  \ $$| $$  \ $$| $$$$$$$$| $$  | $$
    | $$\  $ | $$| $$  | $$| $$  | $$| $$_____/| $$  | $$
    | $$ \/  | $$|  $$$$$$/| $$  | $$|  $$$$$$$|  $$$$$$$
    |__/     |__/ \______/ |__/  |__/ \_______/ \____  $$
                                                /$$  | $$
                                               |  $$$$$$/
                                                \______/ 

"""
print(logo)

API_KEY = "AIzaSyCXi8qs6k2QibkjyWfDANL257n3UhBCRzg"
API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
urls = []



def wordpress_check(url):

    # check if the website is built with WordPress
    print(f"Checking if {url} is built with WordPress...")
    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/58.0.3029.110 Safari/537.3"
    }
    is_wp = False

    try:
        response = requests.get(
            url,
            headers=header,
            timeout=20,
        )

        if response.status_code != 200:
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        html_content = response.text.lower()

        if 'wp-content' in html_content or 'wp-includes' in html_content:
            is_wp = True

        meta_generator = soup.find('meta', attrs={'name': 'generator'})
        if meta_generator and 'wordpress' in meta_generator.get('content', '').lower():
            is_wp = True

        wp_api_link = soup.find('link', attrs={'rel': 'https://w.org'})
        if wp_api_link:
            is_wp = True

        login_url = urljoin(url, '/wp-login.php')
        login_response = requests.get(login_url, headers=header, timeout=5)
        if login_response.status_code == 200 and ('wp-login' in login_response.text or 'wordpress' in login_response.text):
            is_wp = True

    except requests.exceptions.RequestException as e:
        return {"error": {str(e)}}

    finally:
        if is_wp:
            urls.append(url)
            print(f"{url} is built with WordPress.")





def test():

    # process urls
    for url in urls:
        params = {
            "url": url,
            "key": API_KEY,
            "strategy": "mobile",
            "category": "performance",
        }

        try:
            response = requests.get(
                API_URL,
                params=params,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()

            lighthouse = data["lighthouseResult"]
            audits = lighthouse["audits"]

            score = (
                lighthouse["categories"]["performance"]["score"]
                * 100
            )

            print(f"Website: {url}")
            print(f"Performance: {round(score)}/100")
            print(
                "LCP:",
                audits["largest-contentful-paint"]["displayValue"],
            )
            print(
                "CLS:",
                audits["cumulative-layout-shift"]["displayValue"],
            )
            print(
                "Speed Index:",
                audits["speed-index"]["displayValue"],
            )

        except requests.RequestException as error:
            print(f"API request failed: {error}")

        except (KeyError, TypeError) as error:
            print(f"Unexpected API response: {error}")




def main():

    # read urls
    try:
        with open("file.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    wordpress_check(line)
                    print(f"Checking {line}...")
                
    except FileNotFoundError:
        print("File not found.")

    finally:
        if len(urls) != 0:
            test()






    

while True:
    choice = questionary.select(
        "What do you want to do?",
        choices=[
            'start',
            'help',
            'exit'
        ]).ask()

    if choice == 'start':
        main()
    elif choice == 'help':
        print("...")
    elif choice == 'exit':
        sys.exit()
    else:
        print("Invalid choice. Please try again.")

    print("\n")