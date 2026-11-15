TERRAPULSE — WINDOWS QUICK START

1. Extract this entire folder from the ZIP file.
2. Double-click RUN_TERRAPULSE.bat.
3. The first launch may take a few minutes because Python packages are installed.
4. Your browser should open TerraPulse at http://localhost:8501.
5. Keep the black launcher window open while using the website.
6. To stop TerraPulse, close the launcher window or press Ctrl+C in it.

LIVE NASA FIRMS DATA (OPTIONAL)
- Open the .streamlit folder.
- Make a copy of secrets.toml.example and rename the copy to secrets.toml.
- Open secrets.toml and replace the placeholder with your own NASA FIRMS MAP_KEY.
- Save the file and relaunch TerraPulse.
- Do not share your private key or upload secrets.toml publicly.

CSV uploads can be used without configuring a live-data key.

RECOMMENDED PYTHON VERSION
Python 3.12 (or 3.11). If the launcher cannot create its environment,
install Python 3.12 from https://www.python.org/downloads/ and try again.

IMPORTANT
This launcher installs packages into a local .venv folder inside this project.
It does not replace your system Python installation.
