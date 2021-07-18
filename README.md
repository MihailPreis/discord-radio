# 🔊 DiscordRadio [![Create and publish a Docker image](https://github.com/MihailPreis/discord-radio/actions/workflows/deploy-image.yml/badge.svg?branch=master)](https://github.com/MihailPreis/discord-radio/actions/workflows/deploy-image.yml)

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
   *For create Discord bot see [this](https://discordpy.readthedocs.io/en/stable/discord.html)*

2. Create `default.mp3` audio for loop playing if channel not have tracks.

3. Run server
   ```shell
   $ docker pull ghcr.io/mihailpreis/discord-radio:master
   $ docker run -d --env-file .env --mount source=discord-radio-data,target=/app/data --name discord-radio ghcr.io/mihailpreis/discord-radio:master
   $ docker cp default.mp3 discord-radio:/app
   ```

4. Add you **radio** bot to server.

5. Send `<you_prefix or $>help` in text channel for get help.

---

- **License:** © 2021 M.Price.<br>See the [LICENSE file](LICENSE) for license rights and limitations (MIT).
