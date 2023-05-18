import io
import os
import asyncio
import argparse
from pypdf import PdfMerger, PdfReader
from pyppeteer import launch

# every accoutbn has five default books
default_docs = ["12849", "5317", "59767", "58311", "58216"]


async def download_book(page, doc_id):
    file_name = f"{doc_id}.pdf"
    try:
        # skip if pdf exists
        if os.path.exists(file_name):
            print(f"[-] {file_name} already exists, skipping")
            return
        pdf = PdfMerger()
        # open the book and use js to get the maximum pages
        await page.goto(
            f"https://app.edubase.ch/#doc/{doc_id}/1", {"waitUntil": "networkidle0"}
        )
        await asyncio.sleep(1)
        max_pages_raw = await page.evaluate(
            'new Array(...document.querySelector("#pagination").getElementsByTagName("span")).filter(span => span.textContent.includes("/ "))[0].innerHTML',
            force_expr=True,
        )
        # remove the slash + whitespace
        max_pages = int(max_pages_raw.replace("/ ", ""))
        # download each page into memory
        for i in range(1, max_pages + 1):
            print(f"[*] Downloading page {i}/{max_pages} of book '{doc_id}'")
            await page.goto(
                f"https://app.edubase.ch/#doc/{doc_id}/{i}",
                {"waitUntil": "networkidle0"},
            )
            await asyncio.sleep(0.5)
            pdf_page = io.BytesIO(await page.pdf())
            # append page to the merger
            pdf.append(PdfReader(pdf_page))
        # save the final pdf
        print(f"[*] Creating {file_name}")
        pdf.write(file_name)
        pdf.close()
    except Exception as e:
        print("[!] There was an error during download:")
        print(e)
        return


async def main(args):
    options = {
        "headless": (not args.show),
    }

    # custom chrome path if specified
    if args.chromepath != "":
        options["executablePath"] = args.chromepath
    try:
        browser = await launch(options)
        context = await browser.createIncognitoBrowserContext()
        page = await context.newPage()
    except Exception as e:
        print("[!] There was an error while setting up Chrome")
        print(e)
        return

    try:
        # login
        print("[*] Logging in")
        await page.goto(
            "https://app.edubase.ch/#promo?popup=login", {"waitUntil": "networkidle0"}
        )
        # webapp takes a while even after networkidle
        await asyncio.sleep(3)
        await page.type('input[name="login"]', args.username)
        await page.type('input[name="password"]', args.password)
        await asyncio.sleep(1)
        await page.click('button[type="submit"]')
        # wait for the doc library to load
        await page.waitForXPath(r'//*[@id="libraryItems"]/li')
        # use js to extract all IDs
        all_doc_ids = await page.evaluate(
            "new Array(...document.querySelectorAll('li.m-2.lu-library-item')).map((e) => e.getAttribute('data-last-available-version'))",
            force_expr=True,
        )
    except Exception as e:
        print("[!] There was an error during login:")
        print(e)
        return
    print("[+] Login successful")

    doc_ids = []
    for doc_id in all_doc_ids:
        # filter out "None" types
        if doc_id != None:
            # filter out the default ones if not specified
            if not args.defaults and doc_id in default_docs:
                continue
            else:
                doc_ids.append(doc_id)
    print(f"[+] Got a total of {len(doc_ids)} book(s)")

    # let the user select a book if not specified
    if not args.all:
        for doc_id in doc_ids:
            print(f"[*] {doc_id}")
        try:
            selection = input("[?] Which one should I download?: ")
            if selection not in doc_ids:
                raise SyntaxError
        except SyntaxError:
            print("[!] Invalid ID")
            return
        # download the book
        await download_book(page, selection)
        await browser.close()
        return
    else:
        # user wants all books
        for doc_id in doc_ids:
            await download_book(page, doc_id)
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
    parser.add_argument("-d", "--defaults", action="store_true", default=False)
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
-d, --defaults      Will also include the 5 default books every account has
-s, --show          Show the action/open browser in front
-h, --help          Prints this text
    """

    # show help
    if args.help or args.username == "":
        print(helptext)
        exit()

    # user did not specify a password via argument, ask in interactive mode
    if args.password == "":
        try:
            args.password = input("[?] Enter Edubase password: ")
        except SyntaxError:
            print("[!] Password was empty")
            exit()

    # start the main loop
    asyncio.get_event_loop().run_until_complete(main(args))
