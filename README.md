# 🔊 DiscordRadio

Radio server for Discord voice rooms.

## Requirements

 - [Python 3.8+](https://www.python.org/)

## How to use

1. Create `.env` in root:
   ```dotenv
   # required
   DISCORD_TOKEN=<BOT_TOKEN>
   # optional
   DISCORD_PREFIX=^ # default: $
   DEFAULT_MP3=default.mp3 # default: default.mp3
   LOG_LEVEL=DEBUG # default: INFO | see https://docs.python.org/3/howto/logging.html#logging-levels
   LOG_FILE=/var/log/DiscordRadio.log # if specified, log file will be writing
   ```
   *For get `id` and `hash` see [this](https://core.telegram.org/api/obtaining_api_id)*

2. Create `default.mp3` audio for loop playing if channel not have tracks.

3. Run server
   ```shell
   $ docker build -t discrod-radio .
   $ docker run -d --env-file .env --mount source=discord-radio-data,target=/app/data --name discrod-radio discord-radio:latest
   $ docker cp default.mp3 discrod-radio:/app
   ```

4. Add you **radio** account in group.

5. Send `<you_prefix or $>help` in group for get help.

---

- **License:** © 2021 M.Price.<br>See the [LICENSE file](LICENSE) for license rights and limitations (MIT).
