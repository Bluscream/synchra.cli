# synchra.cli

A powerful, interactive command-line interface for monitoring streams and sending messages through the [Synchra API](https://synchra.net).

## Features
- **Real-time Monitoring**: Connect to Synchra channels via WebSockets to see chat messages and activity in real-time.
- **Interactive Chat**: Send messages to all connected platforms (Twitch, YouTube, etc.) directly from your terminal.
- **Flexible Targeting**: Resolve channels by UUID, platform/username shorthand (e.g. `tiktok/username`), or positional arguments.
- **Multi-Platform Support**: Unified interface for Twitch, YouTube, and TikTok.

## Installation
```bash
pip install synchra.cli
```

## Usage
### Start Monitoring
```bash
synchra tiktok username
# OR
synchra 019d49d2-0891-70e5-b791-c94fd76ca590
```

### Options
- `--timeout SECONDS`: Exit automatically after a specified time.
- `--token TOKEN`: Provide your Synchra API token (can also be set via `SYNCHRA_TOKEN` environment variable).

## License
MIT
