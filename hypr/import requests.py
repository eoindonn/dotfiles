import requests
from bs4 import BeautifulSoup

def google_doc_letter_printer(url):
    # Gets the text + sets declares html parser
    response = requests.get(url)
    unparsed = response.text
    soup = BeautifulSoup(unparsed, 'html.parser')

    # Self explanatory
    found_table = soup.find('table')
    if not found_table:
        print("No table found")
        return

    doc_chars = []
    # Finds all html elements with certain tags, row by row parses x, char, and y
    rows = found_table.find_all('tr')
    for row in rows[1:]:
        cols = row.find_all(['td', 'th'])
        x = int(cols[0].get_text()) #x
        char = cols[1].get_text() #char
        y = int(cols[2].get_text()) #y
        doc_chars.append((x, char, y))

    # If nothing in the array, returns here
    if not doc_chars:
        print("No character data found")
        return

    # I love list comprehensions
    max_x = max(x for x, _, _ in doc_chars)
    max_y = max(y for _, _, y in doc_chars)

    # Grid to put all our chars in
    grid = [[' ' for _ in range(max_x + 1)] for _ in range(max_y + 1)]

    # Flipped grid because 0,0 is bottom left, not top
    for x, char, y in doc_chars:
        grid[max_y - y][x] = char

    for row in grid:
        print(''.join(row)) # Joined for actual readable output

google_doc_letter_printer("https://docs.google.com/document/d/e/2PACX-1vSvM5gDlNvt7npYHhp_XfsJvuntUhq184By5xO_pA4b_gCWeXb6dM6ZxwN8rE6S4ghUsCj2VKR21oEP/pub")