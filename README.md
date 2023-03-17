# YouTube Music Playlist Creator

This Python script creates a YouTube Music playlist from a JSON file containing song information. It searches for songs using the YouTube Music API and adds them to a new playlist.

## Features

- Automatically create a playlist on YouTube Music with a custom name and description.
- Search for songs and add them to the playlist.
- Warn about duplicate songs being added to the playlist.
- Save the playlist ID to an output file.
- Save any warnings to a log file.
- Support verbose mode for printing warnings during execution.
- Cache video IDs in case of errors to avoid losing progress.

## Prerequisites

- Python 3.x
- ytmusicapi package

Install the ytmusicapi package with the following command:

```
pip install ytmusicapi
```

## Usage

1. Prepare a JSON file containing the song data.
2. Create a `headers_auth.json` file for authenticating with the YouTube Music API. Follow the instructions in the [ytmusicapi](https://github.com/sigma67/ytmusicapi#setup) repository.
3. Run the script:

```
python create_ytm_playlist.py path/to/your/json_file.json -o output_file.txt -l log_file.txt -v
```

## Arguments

- `json_file`: The path to the JSON file containing song data.
- `-o`, `--output_file`: (Optional) The path to the text file to store the playlist ID.
- `-v`, `--verbose`: (Optional) Enable verbose mode (print warnings).
- `-l`, `--log_file`: (Optional) The path to the log file to store warnings.

## JSON File Format

The JSON file should have the following format:

```json
[
  {
    "name": "Playlist Name",
    "tracks": [
      {
        "artist": "Artist Name",
        "track": "Track Name"
      },
      ...
    ]
  }
]
```

Replace "Playlist Name" with your desired playlist name, and add as many artist-track pairs as needed.

## License
This project is licensed under the MIT License.