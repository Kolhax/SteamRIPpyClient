import requests
from bs4 import BeautifulSoup
import json
import os
import GameList.scrapper as GetGameDatas

def extract_all_links(url, css_selector):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    target_div = soup.select_one(css_selector)
    if target_div:
        links = target_div.find_all('a', href=True)
        return [link['href'] for link in links]
    else:
        print("Target div not found.")
        return []

def extract_specific_links(links, prefixes):
    return [link for link in links if any(link.startswith(prefix) for prefix in prefixes)]

def save_game_list(url, css_selector, json_file):
    all_links = extract_all_links(url, css_selector)
    with open(json_file, 'w') as file:
        json.dump(all_links, file)
    print("Game list updated and saved to JSON.")

def load_game_list(json_file):
    if os.path.exists(json_file):
        with open(json_file, 'r') as file:
            return json.load(file)
    else:
        return []

def search_games(json_file, prefixes):
    game_list = load_game_list(json_file)
    if not game_list:
        print("No games found. Please update the game list first.")
        return

    search_term = input("Enter the game name to search: ").lower()
    matching_games = [game for game in game_list if search_term in game.lower()]

    if not matching_games:
        print("No matching games found.")
        return

    print("Matching games:")
    for index, game in enumerate(matching_games, start=1):
        print(f"{index}. {game}")

    choice = int(input("Select a game by number to get download links: ")) - 1
    if 0 <= choice < len(matching_games):
        selected_game = matching_games[choice]
        download_links = extract_specific_links([selected_game], prefixes)
        print("Download links:")
        for link in download_links:
            print(link)
    else:
        print("Invalid selection.")

def main_menu():
    url = "https://steamrip.com/games-list-page/"
    css_selector = 'body > div:nth-of-type(1) > div > div > div > div > div > div > div > div > div'
    json_file = 'game_list.json'
    prefixes = [
        "https://buzzheavier.com/",
        "https://gofile.io/d/",
        "https://megadb.net/"
    ]

    while True:
        print("\nMenu:")
        print("1. Save/Update Game List")
        print("2. Search Games")
        print("3. Exit")

        choice = input("Enter your choice: ")

        if choice == '1':
            save_game_list(url, css_selector, json_file)
        elif choice == '2':
            search_games(json_file, prefixes)
        elif choice == '3':
            break
        else:
            print("Invalid choice. Please try again.")

def start_script():
    url = "https://steamrip.com/games-list-page/"
    css_selector = 'body > div:nth-of-type(1) > div > div > div > div > div > div > div > div > div'
    json_file = 'game_list.json'
    prefixes = [
        "https://buzzheavier.com/",
        "https://gofile.io/d/",
        "https://megadb.net/"
    ]
    save_game_list(url, css_selector, json_file)
    with open('game_list.json', 'r') as f:
        data = json.load(f)  # Correctly read and parse the JSON file
    a=0
    for i in data:
        data[a] = "https://steamrip.com" + i  # Prepend the base URL to each 'url' field
        a = a+1
    with open('game_list.json', 'w') as f:
        json.dump(data, f, indent=2)  # Save the updated data back to 'game_list.json'

    GetGameDatas.main()
    import jsonformater
    jsonformater.clean()
    
    #!os.remove('cleaned_results.json')
    os.remove('checked_pages.json')
    os.remove('game_list.json')
    os.remove('scraped_results.json')
    
    os.open('cleaned_results.json')

if __name__ == "__main__":
    url = "https://steamrip.com/games-list-page/"
    css_selector = 'body > div:nth-of-type(1) > div > div > div > div > div > div > div > div > div'
    json_file = 'game_list.json'
    prefixes = [
        "https://buzzheavier.com/",
        "https://gofile.io/d/",
        "https://megadb.net/"
    ]
    save_game_list(url, css_selector, json_file)
    with open('game_list.json', 'r') as f:
        data = json.load(f)  # Correctly read and parse the JSON file
    a=0
    for i in data:
        data[a] = "https://steamrip.com" + i  # Prepend the base URL to each 'url' field
        a = a+1
    with open('game_list.json', 'w') as f:
        json.dump(data, f, indent=2)  # Save the updated data back to 'game_list.json'

    GetGameDatas.main()
    import jsonformater
    jsonformater.clean()
    
    #!os.remove('cleaned_results.json')
    os.remove('checked_pages.json')
    os.remove('game_list.json')
    os.remove('scraped_results.json')
    
    os.open('cleaned_results.json')