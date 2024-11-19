import json
import geckodriver_autoinstaller
import os
import hashlib
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from urllib.parse import urljoin  # To handle relative URLs

class ContinuousScraper:
    def __init__(self):
        # Auto-install the geckodriver (Firefox WebDriver)
        geckodriver_autoinstaller.install()

        # Set up Firefox driver options
        firefox_options = Options()
        firefox_options.headless = True  # Run in headless mode (no GUI)
        
        # Initialize the WebDriver once
        self.driver = webdriver.Firefox(options=firefox_options)

    def retrieve_visible_text_and_urls(self, url, xpaths):
        # Open the specified URL
        self.driver.get(url)
        
        text_content = []
        image_urls = []
        other_urls = []
        banner_url = None
        
        # Loop through the provided XPath expressions
        for xpath in xpaths:
            elements = self.driver.find_elements(By.XPATH, xpath)
            for element in elements:
                # Retrieve text content
                text = element.text.strip()
                if text:
                    text_content.append(text)

                # Retrieve image URLs (if the element contains an image)
                img_elements = element.find_elements(By.TAG_NAME, "img")
                for img in img_elements:
                    src = img.get_attribute("src")
                    if src:
                        image_urls.append(src)

                # Retrieve other URLs (if the element contains a link)
                link_elements = element.find_elements(By.TAG_NAME, "a")
                for link in link_elements:
                    href = link.get_attribute("href")
                    if href:
                        other_urls.append(href)
        
        # Attempt to extract the banner image URL (assumes XPath exists for banner)
        try:
            banner_element = self.driver.find_element(By.XPATH, '//*[@id="tie-wrapper"]/div[2]/div/div/figure/img')  # Example XPath for banner
            banner_url = banner_element.get_attribute("src")
            if banner_url:
                banner_url = urljoin(url, banner_url)  # Convert to absolute URL if it's relative
        except Exception as e:
            print(f"Error extracting banner image: {e}")

        return {"text_content": text_content, "image_urls": image_urls, "other_urls": other_urls, "banner_url": banner_url}

    def close(self):
        # Close the WebDriver instance
        self.driver.quit()

def load_urls_from_json(file_path):
    with open(file_path, "r") as f:
        # Directly load the list of URLs
        urls = json.load(f)
    return urls

def load_checked_urls(file_path):
    # Load previously checked URLs from a JSON file
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            checked_urls = json.load(f)
    else:
        checked_urls = []
    return checked_urls

def save_checked_urls(file_path, checked_urls):
    # Save checked URLs to a JSON file
    with open(file_path, "w") as f:
        json.dump(checked_urls, f, indent=4)

def save_results(results, file_path):
    # Save all results into a single JSON file, appending new data
    with open(file_path, "w") as f:
        json.dump(results, f, indent=4)

def load_existing_results(file_path):
    # Load existing results if the file exists
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            existing_results = json.load(f)
    else:
        existing_results = {}
    return existing_results

def main(skip_checked=False):
    # Initialize the scraper (no need for path to geckodriver since it's auto-installed)
    scraper = ContinuousScraper()

    # Define the XPaths (add the banner image XPath)
    xpaths = [
        '//*[@id="tie-wrapper"]/div[1]/div/header/div/h1',  # Title or main text
        '//*[@id="tie-wrapper"]/div[2]/div/div/figure/img',  # Images to be handled separately
        '//*[@id="the-post"]/div[1]',  # Additional text or content
    ]
    
    # Load URLs from the JSON file
    urls = load_urls_from_json("game_list.json")
    
    # Load previously checked URLs
    checked_urls = load_checked_urls("checked_pages.json")

    # If skip_checked is True, filter out already checked URLs
    if skip_checked:
        urls = [url for url in urls if url not in checked_urls]

    # Load existing results from the output JSON file
    all_results = load_existing_results("scraped_results.json")

    # Scrape each URL
    for url in urls:
        print(f"Processing {url}...")

        # Retrieve the results (text, image URLs, other links, and banner)
        result = scraper.retrieve_visible_text_and_urls(url, xpaths)

        # Use the first piece of text as the parent key (use the first non-empty text)
        parent_key = result['text_content'][0] if result['text_content'] else hashlib.md5(url.encode()).hexdigest()

        # Save the results in the dictionary, using the parent key
        all_results[parent_key] = {
            "text_content": result["text_content"],
            "other_urls": result["other_urls"],
            "image_urls": result["image_urls"],
        }

        # If there is a banner URL, add it to the results
        if result["banner_url"]:
            all_results[parent_key]["banner_url"] = result["banner_url"]

        # Add the URL to the checked list
        checked_urls.append(url)

        # Save the updated checked URLs list immediately
        save_checked_urls("checked_pages.json", checked_urls)

        # Save the updated results into the JSON file continuously
        save_results(all_results, "scraped_results.json")

    # Close the WebDriver instance after scraping
    scraper.close()

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Scrape URLs and save results.")
    parser.add_argument('--skip-checked', action='store_true', 
                        help="Skip already checked URLs based on the checked_pages.json file.")
    args = parser.parse_args()

    # Run the main function with the parsed argument
    main(skip_checked=args.skip_checked)
