import json
import sys
import os
import re
import unicodedata
from datetime import datetime
from ytmusicapi import YTMusic

def normalize_string(text):
    normalized = unicodedata.normalize('NFD', text).encode('ASCII', 'ignore').decode('utf-8')
    return normalized.lower()

def tokenize_string(text):
    return set(re.findall(r'\b\w+\b', normalize_string(text)))

def compare_strings(query, result):
    query_tokens = tokenize_string(query)
    result_tokens = tokenize_string(result)
    matched_tokens = query_tokens & result_tokens
    return len(matched_tokens) / len(query_tokens)

def prompt_user_choice(search_query, search_results):
    print(f"\nOriginal query: {search_query}")

    for i, result in enumerate(search_results):
        matched_artist = result['artists'][0]['name']
        matched_title = result['title']
        matched_query = f"{matched_artist} - {matched_title}"
        match_ratio = compare_strings(search_query, matched_query) * 100

        print(f"{i + 1}. {matched_query} (Match: {round(match_ratio)}%)")

    user_input = input("Enter the number of the desired match to add it to the playlist, or type 'n' to skip: ")

    if user_input.lower() != 'n':
        try:
            selected_index = int(user_input) - 1
            if 0 <= selected_index < len(search_results):
                return search_results[selected_index]['videoId']
            else:
                print("Invalid input. Skipping this song.")
                return None
        except ValueError:
            print("Invalid input. Skipping this song.")
            return None
    else:
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python create_ytmusic_playlist.py <JSON_file>")
        return

    json_file = sys.argv[1]  # Get JSON file name from command line
    playlist_title = os.path.splitext(os.path.basename(json_file))[0]  # Set playlist title based on file name
    playlist_title += f" - {datetime.now().strftime('%Y%m%d-%H%M%S')}"  # Add timestamp to playlist title
    playlist_description = 'A playlist created from a JSON file.'  # Set your desired playlist description

    with open(json_file) as f:
        data = json.load(f)

    ytmusic = YTMusic('headers_auth.json')

    video_ids = set()  # Initialize a set to store unique video IDs

    for item in data[0]['tracks']:
        artist = item['artist']
        track = item['track']
        search_query = f"{artist} - {track}"
        search_results = ytmusic.search(search_query, filter='songs', ignore_spelling=True)[:10] # limit results to 10

        if search_results and len(search_results) > 0:
            first_match_ratio = compare_strings(search_query, f"{search_results[0]['artists'][0]['name']} - {search_results[0]['title']}")

            if first_match_ratio < 0.5:
                video_id = prompt_user_choice(search_query, search_results)

                if video_id is None:
                    # Perform a search with the scope set to "uploads"
                    video_results = ytmusic.search(search_query, filter='videos', ignore_spelling=True)[:10] # limit results to 10

                    if video_results and len(video_results) > 0:
                        video_id = prompt_user_choice(search_query, video_results)

            else:
                video_id = search_results[0]['videoId']

            if video_id is not None:
                if video_id in video_ids:
                    print(f"Warning: Duplicate video ID ({video_id}) for {artist} - {track}")
                else:
                    video_ids.add(video_id)  # Add the video ID to the set


    # Add all unique video IDs to the playlist at once
    playlist_id = ytmusic.create_playlist(playlist_title, playlist_description, privacy_status='UNLISTED')
    add_items_result = ytmusic.add_playlist_items(playlist_id, list(video_ids))
    print(f"add_playlist_items result: {add_items_result}")

if __name__ == "__main__":
    main()
