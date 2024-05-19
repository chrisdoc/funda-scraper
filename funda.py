import sqlite3
from typing import List
from bs4 import BeautifulSoup, Tag
import requests
import re
from fake_useragent import UserAgent


class Listing:
    def __init__(
        self,
        street: str,
        link: str,
        price: str,
        hasElevator: bool,
        stories: str,
        summary: str,
    ):
        self.street = street.strip()
        self.link = link.strip()
        self.hasElevator = hasElevator
        self.price = price.strip()
        self.stories = stories.strip()
        self.summary = summary.strip()

    def __str__(self) -> str:
        return self.street + " : " + str(self.hasElevator) + " : " + self.price


class Funda:
    user_agent = UserAgent().chrome

    def __init__(self, db_location, openai_client, search_url) -> None:
        print("funda: init client")
        sqlite_connection = sqlite3.connect(db_location)
        self.cursor = sqlite_connection.cursor()
        self.openai_client = openai_client
        self.search_url = search_url

    def fetchNew(self) -> List[Listing]:
        print("funda: doing search")
        searchResult = requests.get(
            self.search_url, headers={"User-Agent": self.user_agent}
        )

        parsed_html = BeautifulSoup(searchResult.text, features="html.parser")
        listings = parsed_html.select('div[data-test-id="search-result-item"]')
        newListings = [x for x in listings if "Nieuw" in x.text]

        result = []

        print("funda: going over listings")
        for newListing in newListings:
            title = newListing.select("h2")[0]
            street = title.text.strip()
            print("funda: checking listing: " + street)
            data = self.cursor.execute(
                "SELECT * from listing WHERE street = ?", (street,)
            ).fetchall()
            if len(data) == 0:
                print("funda: the listing is a new one!")
                self.cursor.execute("INSERT INTO listing VALUES (?)", (street,))
                self.cursor.connection.commit()
                link = title.parent
                apartmentPage = requests.get(
                    link.get("href"), headers={"User-Agent": self.user_agent}
                )
                apartment_page_parsed = BeautifulSoup(
                    apartmentPage.text, features="html.parser"
                )
                listing = Listing(
                    street=title.text,
                    link=link.get("href"),
                    price=self.fetchPrice(newListing),
                    hasElevator=self.hasElevator(apartmentPage),
                    stories=self.fetchNumberOfStories(apartment_page_parsed),
                    summary=self.fetchSummary(apartment_page_parsed),
                )
                result.append(listing)
            else:
                print("funda: listing is an old one ...")
        return result

    def hasElevator(self, apartmentPage) -> bool:
        return (
            ("elevator" in apartmentPage.text)
            or ("lift" in apartmentPage.text)
            or ("Elevator" in apartmentPage.text)
            or ("Lift" in apartmentPage.text)
        )

    def fetchNumberOfStories(self, apartment_page_parsed: Tag) -> str:
        terms = apartment_page_parsed.find_all("dt")
        for term in terms:
            if term.text == "Number of stories" or term.text == "Aantal woonlagen":
                description = term.find_next_siblings("dd")[0]
                print("fetched: " + description.text)
                if description:
                    return description.text.strip()
        return ""

    def fetchPrice(self, listing) -> str:
        return listing.select("p[data-test-id=price-sale]")[0].text

    def fetchSummary(self, apartmentPage) -> str:
        headless = apartmentPage.find_all(
            "div", {"id": re.compile("headlessui-disclosure-panel.*")}
        )
        content = "\n".join(list(map(lambda x: x.get_text(), headless)))

        prompt = f"""
        You are given the information about a dutch house listing and your task is to generate a summary of the listing.

        Please format the output in Markdownv2 so that it can be used to send a message from a telegram bot to a house hunter. Make sure that there is a tl;dr execute summary at the beginning with the most important information like size, number of bedrooms, highlights and location! Only include the most important information and discard everything else. The message should be maximum 100 words long with the most important information at the beginning.

        Do not wrap the text in a markdown code block, just use the markdown syntax for formatting.

        Content:
        \"\"\"
        {content}
        \"\"\"
        """

        completion = self.openai_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], model="gpt-4o"
        )
        return completion.choices[0].message.content
