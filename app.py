import requests
from lxml import etree
from bs4 import BeautifulSoup as bs
from tabulate import tabulate
import time
import os
import re
from clint.textui import progress
import concurrent.futures


HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 \
            (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36",
    "Accept-Language": "en-US, en;q=0.5",
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
    table = [["Index", "Title"]]

    for book in data:
        book_detail = [book["title"]]
        table.append(book_detail)
    print(
        tabulate(
            table, headers="firstrow", showindex="always", tablefmt="grid"
        )
    )


def search_books(query):
    app_url = f"http://libgen.rs/search.php?req={query}"
    res = requests.get(app_url, headers=HEADERS)
    soup = bs(res.content, "html.parser")
    dom = etree.HTML(str(soup))

    records = dom.xpath("//table[@class='c']//tr")

    results = len(records) - 1
    books = []
    if results == 0:
        print(f"Found {results} results. Please search again.")
    else:
        print(f"We have found some books. Hang on...")

        for x in range(2, (len(records) + 1)):
            title_xpath = f"//table[@class='c']//tr[{x}]/td[3]/a"
            elements = dom.xpath(title_xpath)
            title = ""
            for ele in elements:
                if ele.text is not None:
                    title = ele.text.strip()

            title = title if len(title) < 50 else f"{title[:51]}..."

            author = dom.xpath(f"//table[@class='c']//tr[{x}]/td[2]/a[1]")[
                0
            ].text.strip()

            pages = dom.xpath(f"//table[@class='c']//tr[{x}]/td[6]")[0].text
            pages = "NA" if pages is None else pages.strip()

            language = dom.xpath(f"//table[@class='c']//tr[{x}]/td[7]")[0].text
            language = "NA" if language is None else language.strip()

            size = dom.xpath(f"//table[@class='c']//tr[{x}]/td[8]")[
                0
            ].text.strip()
            size = "NA" if size is None else size.strip()

            extension = dom.xpath(f"//table[@class='c']//tr[{x}]/td[9]")[
                0
            ].text
            extension = "NA" if extension is None else extension.strip()

            url = dom.xpath(f"//table[@class='c']//tr[{x}]/td[10]/a")[0].get(
                "href"
            )

            res = requests.get(url)
            soup = bs(res.text, "html.parser")
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

    return books


# Search for recommendations
def recommend(book):
    url = f"https://www.goodreads.com/search?q={book}"
    recommended_books = []

    res = requests.get(url, headers=HEADERS)
    soup = bs(res.text, "html.parser")

    title = soup.find(class_="bookTitle")
    names = soup.select(".bookTitle > span")

    if len(names):
        title_url = title.get("href")
        search_url = f"{appurl}{title_url}"

        res = requests.get(search_url, headers=HEADERS)
        soup = bs(res.text, "html.parser")

        seemorelinks = soup.select(".seeMoreLink")
        if len(seemorelinks):
            similar_url = seemorelinks[0].get("href")
            res = requests.get(similar_url, headers=HEADERS)
            soup = bs(res.text, "html.parser")

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


# Program starts from here
query = input("Enter the book name: ")
start = time.perf_counter()

if len(query) < 1:
    print("Invalid query. Search again please.")
else:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        t1 = executor.submit(search_books, query)
        t2 = executor.submit(recommend, query)
        books_found = t1.result()
        recommends_found = t2.result()
        # books_found = search_books(query)
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
                    # recommends_found = recommend(query)
                    tabulate_recommendations(recommends_found)

                else:
                    print("You entered invalid index")
            except:
                print("You entered invalid index")


finish = time.perf_counter()
print(f"Finished in {round(finish-start, 2)} seconds.")
