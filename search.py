import os
import re
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from clint.textui import progress
import requests
import time
import pprint
from tabulate import tabulate

chrome_options = Options()
chrome_options.add_argument("--headless")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"
}
appurl = "https://www.goodreads.com"

# Create a table from the list in prompt
def tabulate_data(data):
    table = [
        ["Index", "Title", "Author", "Language", "Pages", "Size", "Format"]
    ]

    for book in data:
        book_detail = [
            book["title"],
            book["author"],
            book["language"],
            book["pages"],
            book["size"],
            book["format"],
        ]
        table.append(book_detail)

    print(
        tabulate(
            table, headers="firstrow", showindex="always", tablefmt="grid"
        )
    )


def tabulate_recommendations(data):
    table = [["Index", "Title", "Url"]]

    for book in data:
        book_detail = [book["title"], book["book_url"]]
        table.append(book_detail)
    print(
        tabulate(
            table, headers="firstrow", showindex="always", tablefmt="grid"
        )
    )


# Search Book Function
def search_book(query):
    # driver = webdriver.Chrome(executable_path="./chromedriver.exe")
    # driver = webdriver.Chrome(executable_path="./chromedriver.exe", options=chrome_options)
    driver = webdriver.Chrome(
        ChromeDriverManager().install(), options=chrome_options
    )
    url = "http://gen.lib.rus.ec"
    driver.get(url)
    print("Please wait while we look for your book...")

    driver.maximize_window()
    driver.implicitly_wait(20)
    time.sleep(5)

    search_input = driver.find_element_by_id("searchform")
    search_input.send_keys(query)

    search_btn = driver.find_element_by_xpath("//input[@value='Search!']")
    search_btn.click()

    print(f"Searching for {query}...")

    time.sleep(10)

    records = driver.find_elements_by_xpath("//table[@class='c']//tr")

    results = len(records) - 1
    books = []
    if results == 0:
        print(f"Found {results} results. Please search again.")
        return books
    else:
        print(f"We have found some books. Hang on...")

        for x in range(2, (len(records) + 1)):
            title_xpath = f"//table[@class='c']//tr[{x}]/td[3]/a"
            ele = driver.find_element_by_xpath(title_xpath)
            title = ele.text.strip()
            children = ele.find_elements_by_xpath("./*")
            if len(children) > 1:
                for child in children:
                    title = title.replace(child.text, "", 1).strip()

            author = driver.find_element_by_xpath(
                f"//table[@class='c']//tr[{x}]/td[2]/a[1]"
            ).text.strip()
            pages = driver.find_element_by_xpath(
                f"//table[@class='c']//tr[{x}]/td[6]"
            ).text.strip()
            language = driver.find_element_by_xpath(
                f"//table[@class='c']//tr[{x}]/td[7]"
            ).text.strip()
            size = driver.find_element_by_xpath(
                f"//table[@class='c']//tr[{x}]/td[8]"
            ).text.strip()
            extension = driver.find_element_by_xpath(
                f"//table[@class='c']//tr[{x}]/td[9]"
            ).text.strip()
            url = driver.find_element_by_xpath(
                f"//table[@class='c']//tr[{x}]/td[10]/a"
            ).get_attribute("href")

            res = requests.get(url)
            soup = BeautifulSoup(res.text, "html.parser")
            download_url = soup.find("a").get("href")

            books.append(
                {
                    "title": title,
                    "author": author,
                    "language": language,
                    "pages": pages,
                    "format": extension,
                    "size": size,
                    "url": download_url,
                }
            )

        # pp = pprint.PrettyPrinter()
        # pp.pprint(books)

        driver.close()
        driver.quit()

        return books


# Download File function
def download_file(url, title, ext):
    reqfile = requests.get(url, stream=True)

    file_name = f"{title}.{ext}"
    path = "downloads"
    if not os.path.exists(path):
        os.makedirs(path)
    with open(os.path.join(path, file_name), "wb") as pyFile:
        total_length = int(reqfile.headers.get("content-length"))
        print(total_length)
        for ch in progress.bar(
            reqfile.iter_content(chunk_size=2391975),
            expected_size=(total_length / 1024) + 1,
        ):
            if ch:
                pyFile.write(ch)
    print("Download complete!")


# Search for recommendations
def recommend(book):
    url = f"https://www.goodreads.com/search?q={book}"
    recommended_books = []

    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    title = soup.find(class_="bookTitle")
    names = soup.select(".bookTitle > span")

    if len(names):
        title_url = title.get("href")
        search_url = f"{appurl}{title_url}"

        res = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        seemorelinks = soup.select(".seeMoreLink")
        if len(seemorelinks):
            similar_url = seemorelinks[0].get("href")
            res = requests.get(similar_url, headers=headers)
            soup = BeautifulSoup(res.text, "html.parser")

            similar_titles_url = soup.select(
                "a.gr-h3.gr-h3--serif.gr-h3--noMargin"
            )
            similar_titles = soup.select(
                "a.gr-h3.gr-h3--serif.gr-h3--noMargin > span"
            )

            if len(similar_titles) > 6:
                r = 6
            else:
                r = len(similar_titles)

            for x in range(1, r):
                similar_title = similar_titles[x].getText()
                similar_title_url = similar_titles_url[x].get("href")
                recommended_books.append(
                    {
                        "title": similar_title,
                        "book_url": f"{appurl}{similar_title_url}",
                    }
                )
                # print(f"{similar_title} - {appurl}{similar_title_url}")
            return recommended_books


# Program starts from here
query = input("Enter the book name: ")

if len(query) < 1:
    print("Invalid query. Search again please.")
else:
    books_found = search_book(query)
    if len(books_found):
        print(f"Found {len(books_found)} books.")
        tabulate_data(books_found)

        index_query = input("Please enter the index to download: ")
        try:
            download_index = int(index_query)
            if download_index < len(books_found):
                book = books_found[download_index]
                book_title = book["title"]
                book_url = book["url"]
                book_format = book["format"]

                print(f"Downloading {book_title}. Please wait...")
                time.sleep(5)
                book_title = re.sub("[^A-Za-z0-9]+", " ", book_title)
                download_file(book_url, book_title, book_format)

                # print recommendations
                print("Looking for similar books for you:")
                recommends_found = recommend(query)
                tabulate_recommendations(recommends_found)

            else:
                print("You entered invalid index")
        except:
            print("You entered invalid index")
