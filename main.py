import sys
import requests
import questionary
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import json

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

header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/58.0.3029.110 Safari/537.3"
}


def get_issues(audits):
    issues = []
    for key, a in audits.items():
        if a.get("scoreDisplayMode") in ("informative", "notApplicable", "manual", "error"):
            continue
        score = a.get("score")
        if score is not None and score < 0.9:
            title = a.get("title", key)
            val = a.get("displayValue", "")
            issues.append(f"- {title} {('(' + val + ')') if val else ''}")
    return issues



def wordpress_check(url):

    # check if the website is built with WordPress
    
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




def find_info(url):
    EMAIL_REGEX = re.compile(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    )

    PHONE_REGEX = re.compile(
        r"(?:(?:\+|00)\d{1,3}[\s\-\.]?)?"
        r"(?:\(?\d{2,4}\)?[\s\-\.]?)?"
        r"\d{3,4}[\s\-\.]?\d{3,4}"
    )

    contacts = {"emails": set(), "phones": set(), "tel_links": set(), "mailto_links": set()}

    try:
        contact_url = urljoin(url, "/contact-us/")
        response = requests.get(contact_url, headers=header, timeout=20)  # ← اصلاح شد

        if response.status_code != 200:
            for path in ["/contact/", "/contact-us", "/تماس-با-ما/", "/about-us/"]:
                r = requests.get(urljoin(url, path), headers=header, timeout=20)  # ← اصلاح شد
                if r.status_code == 200:
                    response = r
                    contact_url = urljoin(url, path)
                    break

        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        html = response.text

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.lower().startswith("mailto:"):
                contacts["mailto_links"].add(href[7:].split("?")[0])
            if href.lower().startswith("tel:"):
                contacts["tel_links"].add(href[4:])

        contacts["emails"].update(EMAIL_REGEX.findall(text))
        contacts["emails"].update(EMAIL_REGEX.findall(html))

        contacts["emails"] = {
            e for e in contacts["emails"]
            if not e.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"))
        }

        contacts["phones"].update(PHONE_REGEX.findall(text))

        contacts["phones"] = {
            p.strip() for p in contacts["phones"]
            if 7 <= len(re.sub(r"\D", "", p)) <= 15
        }

        contacts["phones"].update(contacts["tel_links"])

        return {
            "url": contact_url,
            "emails": sorted(contacts["emails"]),
            "phones": sorted(contacts["phones"]),
        }

    except requests.RequestException as e:
        return {"url": url, "error": str(e)}



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

            lcp = audits["largest-contentful-paint"]["numericValue"] / 1000
            cls = audits["cumulative-layout-shift"]["numericValue"]

            if score < 70 or lcp > 4 or cls > 0.25:
                with open("results.txt", "a", encoding="utf-8") as f:
                    f.write(f"Website: {url}\n")
                    f.write(f"Performance: {round(score)}/100\n")
                    f.write(
                        f"LCP: {audits['largest-contentful-paint']['displayValue']}\n"
                    )
                    f.write(
                        f"CLS: {audits['cumulative-layout-shift']['displayValue']}\n"
                    )
                    f.write(
                        f"Speed Index: {audits['speed-index']['displayValue']}\n"
                    )
                    for issue in get_issues(audits):
                        f.write(f"{issue}\n")
                    f.write(f"info: \n")

                    info = find_info(url)

                    if "error" in info:
                        with open("contacts.txt", "a", encoding="utf-8") as f:
                            f.write(f"Site: {info['url']}\n")
                            f.write(f"ERROR: {info['error']}\n")
                            f.write("-" * 30 + "\n")
                    else:
                        with open("contacts.txt", "a", encoding="utf-8") as f:
                            f.write(f"Site: {info['url']}\n")
                            f.write(f"Emails ({len(info['emails'])}): {', '.join(info['emails']) or '-'}\n")
                            f.write(f"Phones ({len(info['phones'])}): {', '.join(info['phones']) or '-'}\n")

                    f.write("-" * 30 + "\n")


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
            'exit'
        ]).ask()

    if choice == 'start':
        main()

    elif choice == 'exit':
        sys.exit()
    else:
        print("Invalid choice. Please try again.")

    print("\n")