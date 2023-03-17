# Import required libraries
import json
import sys
import os
import re
import unicodedata
import argparse
from datetime import datetime
from ytmusicapi import YTMusic
from queue import Queue
from threading import Thread
from requests.exceptions import HTTPError

# Function to normalize strings, removing accents and converting to lowercase
def normalize_string(text):
    normalized = unicodedata.normalize('NFD', text).encode('ASCII', 'ignore').decode('utf-8')
    return normalized.lower()

# Function to tokenize a string, returning a set of unique words
def tokenize_string(text):
    return set(re.findall(r'\b\w+\b', normalize_string(text)))

# Function to compare two strings by tokenizing and finding the ratio of matched tokens
def compare_strings(query, result):
    query_tokens = tokenize_string(query)
    result_tokens = tokenize_string(result)
    matched_tokens = query_tokens & result_tokens
    return len(matched_tokens) / len(query_tokens)

# Function to prompt the user for their desired match from search results
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

# Main function
def main():
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Create a YouTube Music playlist from a JSON file.')
    parser.add_argument('json_file', type=str, help='Path to the JSON file containing song data')
    parser.add_argument('-o', '--output_file', type=str, default=None, help='Optional path to the text file to store the playlist ID')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose mode (print warnings)')
    parser.add_argument('-l', '--log_file', type=str, default=None, help='Optional path to the log file to store warnings')
    args = parser.parse_args()

    # Read command line arguments
    json_file = args.json_file
    output_file = args.output_file
    verbose = args.verbose
    log_file = args.log_file

    # Load JSON data
    with open(json_file) as f:
        data = json.load(f)

    # Set playlist title and description
    playlist_title = data[0].get('name', os.path.splitext(os.path.basename(json_file))[0])
    playlist_title += f" - {datetime.now().strftime('%Y%m%d-%H%M%S')}"
    playlist_description = 'A playlist created from a JSON file.'

    # Load the JSON data again
    with open(json_file) as f:
        data = json.load(f)

       # Initialize the YTMusic API with the authentication headers
    ytmusic = YTMusic('headers_auth.json')

    # Check for cache file and load video IDs if it exists
    cache_file = f"{os.path.splitext(json_file)[0]}_cache.json"
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            video_ids = set(json.load(f))
    else:
        video_ids = set()  # Initialize a set to store unique video IDs
    log = []  # Initialize a list to store duplicate warnings

    if len(video_ids) == 0:

        user_input_queue = Queue()

        # Function to process user input
        def process_user_input():
            while True:
                search_query, search_result = user_input_queue.get()

                video_id = prompt_user_choice(search_query, search_result)

                if video_id is None:
                    # Perform a search with the scope set to "uploads"
                    video_results = ytmusic.search(search_query, filter='videos', ignore_spelling=True)[:10] # limit results to 10

                    if video_results and len(video_results) > 0:
                        video_id = prompt_user_choice(search_query, video_results)

                if video_id is not None:
                    if video_id in video_ids:
                        log.append(f"Warning: Duplicate video ID ({video_id}) for {artist} - {track}")
                    else:
                        video_ids.add(video_id)  # Add the video ID to the set

                user_input_queue.task_done()

        # Start the user input processing thread
        user_input_thread = Thread(target=process_user_input)
        user_input_thread.daemon = True
        user_input_thread.start()

        # Iterate through the tracks and search for them on YouTube Music
        for item in data[0]['tracks']:
            artist = item['artist']
            track = item['track']
            search_query = f"{artist} - {track}"
            search_results = ytmusic.search(search_query, filter='songs', ignore_spelling=True)[:10] # limit results to 10

            if search_results and len(search_results) > 0:
                first_match_ratio = compare_strings(search_query, f"{search_results[0]['artists'][0]['name']} - {search_results[0]['title']}")

                if first_match_ratio < 0.5:
                    user_input_queue.put((search_query, search_results))
                else:
                    video_id = search_results[0]['videoId']

                    if video_id in video_ids:
                        log.append(f"Warning: Duplicate video ID ({video_id}) for {artist} - {track}")
                    else:
                        video_ids.add(video_id)  # Add the video ID to the set

        # Wait for the user to finish providing input
        user_input_queue.join()

    try:
        # Add all unique video IDs to the playlist at once
        playlist_id = ytmusic.create_playlist(playlist_title, playlist_description, privacy_status='UNLISTED')
        add_items_result = ytmusic.add_playlist_items(playlist_id, list(video_ids))
        log.append(f"add_playlist_items result: {add_items_result}")

        # Delete cache file if it exists
        if os.path.exists(cache_file):
            os.remove(cache_file)

        # Append the playlist ID to the specified text file, if provided
        if output_file is not None:
            with open(output_file, 'a') as f:
                f.write(f"https://music.youtube.com/playlist?list={playlist_id}\n")

    except HTTPError as e:
        if e.response.status_code == 400:
            print(f"Error: {e}")
            print("Saving video IDs to cache file...")
            with open(cache_file, 'w') as f:
                json.dump(list(video_ids), f)
        else:
            raise

    # Display warnings
    for warning in log:
        if verbose and warning.startswith("Warning:"):
            print(warning)
    
    # Save warnings to log file, if provided
    if log_file is not None:
        with open(log_file, 'a') as f:
            for warning in log:
                f.write(f"{warning}\n")

# Run the main function
if __name__ == "__main__":
    main()