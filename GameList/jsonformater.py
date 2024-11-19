import json
import re

def clean():
    # Load the JSON data from the file
    with open('scraped_results.json', 'r') as jsfile:
        data = json.load(jsfile)

    # Base URL for images
    images = "https://steamrip.com/wp-content/uploads/"
    steamrip_base = "https://steamrip.com/"

    # Create a new dictionary to store updated data
    updated_data = {}

    # Process each item in the JSON data
    for title, content in data.items():
        # Remove "Free Download" from the title
        new_title = title.replace(" Free Download", "")
        
        # Process URLs
        rawurls = content["other_urls"]
        urls = []
        download_urls = []
        original_url = None
        
        # Separate URLs into screenshots, download URLs, and original URL
        for b in rawurls:
            if str(b).startswith(images):
                urls.append(b)
            elif str(b).startswith(steamrip_base):
                original_url = b
            else:
                download_urls.append(b)
        
        # Update the JSON structure
        content.pop("image_urls", None)  # Remove image_urls if it exists
        content.pop("other_urls", None)  # Remove other_urls if it exists
        content["text_content"].pop(0)
        content["text_content"] = [text.replace("Direct Download", "") for text in content["text_content"]]
        content['screenshots'] = urls
        content['downloads'] = download_urls
        content['original_url'] = original_url
        
        # Extract System Requirements and Game Info
        origin = content['text_content']
        
        cleaned_text = '\n'.join(origin[0].split('\n', 1)[1:])  # Remove the first sentence
        cleaned_text = re.sub(r'(.*?DOWNLOAD HERE)', '', cleaned_text, flags=re.MULTILINE).strip()  # Remove all download services
        cleaned_text = cleaned_text.replace("\nSCREENSHOTS", "")  # Remove "SCREENSHOTS"

        system_requirements_match = re.search(r'SYSTEM REQUIREMENTS\n(.*?)\nGAME INFO', cleaned_text, re.S)
        game_info_match = re.search(r'GAME INFO\n(.*)', cleaned_text, re.S)

        system_requirements = system_requirements_match.group(1).strip() if system_requirements_match else "Not found"
        game_info = game_info_match.group(1).strip() if game_info_match else "Not found"

        # Update the content with new keys
        content['system_requirements'] = system_requirements
        content['game_info'] = game_info

        # Remove extracted parts from text_content
        cleaned_text = re.sub(r'SYSTEM REQUIREMENTS\n.*?\nGAME INFO\n.*', '', cleaned_text, flags=re.S).strip()
        content['text_content'] = cleaned_text
        
        # Add the updated content to the new dictionary with the new title
        updated_data[new_title] = content

    # Optionally, write the cleaned data back to a file
    with open('cleaned_results.json', 'w') as outfile:
        json.dump(updated_data, outfile, indent=4)
