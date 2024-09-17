import io
import re
import os
import asyncio
import argparse
from pypdf import PdfMerger, PdfReader
from playwright.async_api import async_playwright

# regex to extract the book IDs
re_book_href = re.compile(r"#doc/(\d+)")
# user agent for the headless browser
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.6567.90 Safari/537.36"


async def download_book(page, book_id):
    file_name = f"{book_id}.pdf"
    try:
        # skip if pdf exists
        if os.path.exists(file_name):
            print(f"[-] {file_name} already exists, skipping")
            return

        pdf = PdfMerger()

        # open the book and use js to get the maximum pages
        await page.goto(
            f"https://app.edubase.ch/#doc/{book_id}/1", wait_until="networkidle"
        )
        await asyncio.sleep(1)

        max_pages_raw = await page.evaluate(
            """() => {
            return Array.from(document.querySelector("#pagination").getElementsByTagName("span"))
                .filter(span => span.textContent.includes("/ "))[0].innerHTML;
        }"""
        )

        # remove the slash + whitespace
        max_pages = int(max_pages_raw.replace("/ ", ""))

        # download each page into memory
        for i in range(1, max_pages + 1):
            print(f"[*] Downloading page {i}/{max_pages} of book '{book_id}'")
            await page.goto(
                f"https://app.edubase.ch/#doc/{book_id}/{i}", wait_until="networkidle"
            )
            await asyncio.sleep(0.75)

            # append page to the merger
            pdf_page = io.BytesIO(await page.pdf())
            pdf.append(PdfReader(pdf_page))

        # save the final pdf
        print(f"[*] Creating {file_name}")
        pdf.write(file_name)
        pdf.close()

    except Exception as e:
        print("[!] There was an error during download")
        print(e)
        return


async def main(args):
    async with async_playwright() as p:
        # custom chrome path if specified
        launch_options = {"headless": not args.show}
        if args.chromepath:
            launch_options["executable_path"] = args.chromepath

        try:
            browser = await p.chromium.launch(**launch_options)
            context = await browser.new_context(user_agent=user_agent)
            page = await context.new_page()
        except Exception as e:
            print("[!] There was an error while setting up Chrome")
            print(e)
            return

        try:
            # login
            print("[*] Logging in")
            await page.goto(
                "https://app.edubase.ch/#promo?popup=login", wait_until="networkidle"
            )

            # webapp takes a while even after networkidle
            await asyncio.sleep(3)
            await page.fill('input[name="login"]', args.username)
            await page.fill('input[name="password"]', args.password)
            await asyncio.sleep(1)

            await page.click('button[type="submit"]')
            await asyncio.sleep(3)

            body_text = await page.locator("body").inner_text()
            if (
                "An account with the credentials you entered does not exist."
                in body_text
            ):
                print("[!] Invalid credentials")
                return

            print("[+] Login successful")

        except Exception as e:
            print("[!] There was an error during login")
            print(e)
            return

        try:
            print("[*] Searching for books")

            # wait for the doc library to load
            await page.wait_for_selector("#libraryItems li")
            await asyncio.sleep(3)

            books = []

            # get all links
            links = await page.query_selector_all("a.lu-library-item-aux")

            for link in links:
                href = await link.get_attribute("href")
                title = await link.get_attribute("title")

                if href:
                    match = re_book_href.match(href)
                    if match:
                        books.append({"id": match.group(1), "title": title})

            if len(books) == 0:
                print("[!] No books found")
                return

            print(f"[+] Got a total of {len(books)} books\n")

        except Exception as e:
            print("[!] There was an error while searching for books")
            print(e)
            return

        # let the user select a book if not specified
        if not args.all:
            while True:
                for book in books:
                    print(f"{book['title']} (ID: {book['id']})")
                selection = input(
                    "\n[?] Please enter the ID of the book I should download: "
                )
                if not any(book["id"] == selection for book in books):
                    print("[!] Invalid book ID\n")
                else:
                    break

            # download the book
            await download_book(page, selection)
            await browser.close()
            return

        else:
            # user wants all books
            for book in books:
                await download_book(page, book["id"])
            await browser.close()
            return


if __name__ == "__main__":
    # parse the arguments
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-u", "--username", action="store", dest="username", default="")
    parser.add_argument("-p", "--password", action="store", dest="password", default="")
    parser.add_argument(
        "-c", "--chrome-path", action="store", dest="chromepath", default=""
    )
    parser.add_argument("-a", "--all", action="store_true", default=False)
    parser.add_argument("-s", "--show", action="store_true", default=False)
    parser.add_argument("-h", "--help", action="store_true", default=False)
    args = parser.parse_args()

    helptext = """usage: edubasedl.py [OPTIONS]

Required:
-u, --username      Username (Email) of Edubase account

Options:
-p, --password      Password (can be left empty, script will ask)
-c, --chrome-path   Path to the chrome/chromium binary
-a, --all           Will download all found books
-s, --show          Show the action/open browser in front
-h, --help          Prints this text
    """

    # show help
    if args.help or args.username == "":
        print(helptext)
        exit()

    print("[edubasedl]")

    # user did not specify a password via argument, ask in interactive mode
    if args.password == "":
        try:
            args.password = input("[?] Enter Edubase password: ")
        except SyntaxError:
            print("[!] Password was empty")
            exit()

    # start the main loop
    asyncio.get_event_loop().run_until_complete(main(args))
