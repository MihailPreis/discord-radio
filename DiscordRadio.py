import asyncio
import logging
import os
import random
from functools import partial
from threading import Timer

import requests
from discord import FFmpegPCMAudio
from discord.ext import commands
from discord.ext.commands import Bot
from dotenv import load_dotenv

load_dotenv()

GROUP_CALLS = {}
GENERATORS = {}
DEFAULT_MP3 = os.getenv('DEFAULT_MP3', 'default.mp3')
PREFIX = os.getenv('DISCORD_PREFIX', '$')

_l = logging.getLogger(os.path.basename(__file__))
_l.setLevel(os.getenv("LOG_LEVEL", "INFO"))
_log_formatter = logging.Formatter('[%(asctime)s] %(levelname)-8s : %(message)s')
c_handler = logging.StreamHandler()
c_handler.setFormatter(_log_formatter)
_l.addHandler(c_handler)

_log_file = os.getenv('LOG_FILE')
if _log_file:
    f_handler = logging.FileHandler(_log_file, mode='a')
    f_handler.setFormatter(_log_formatter)
    _l.addHandler(f_handler)

client = Bot(command_prefix=list(PREFIX))


@client.event
async def on_ready():
    _l.info('Radio Bot Ready')


@client.command(name='start-radio',
                aliases=['p', 'play', 'start'],
                help="Go on air.")
@commands.has_permissions(manage_channels=True)
async def play_handler(ctx):
    try:
        _gen = GENERATORS.get(ctx.guild.id)
        if _gen is None:
            _gen = gen_playlist(ctx)
            GENERATORS[ctx.guild.id] = _gen

        player = await ctx.message.author.voice.channel.connect()
        GROUP_CALLS[ctx.guild.id] = player
        on_audio_ended(ctx, None)
    except Exception as e:
        _l.error(e)
        await ctx.reply(':construction: Startup error. Try to connect to the voice channel and repeat the command.')


@client.command(name='stop-radio',
                aliases=['s', 'stop'],
                help="Stop a radio broadcast.")
@commands.has_permissions(manage_channels=True)
async def stop_handler(ctx):
    player = GROUP_CALLS.get(ctx.guild.id)
    if player:
        del GROUP_CALLS[ctx.guild.id]
        player.stop()
        await player.disconnect()


@client.command(name='list',
                aliases=['l'],
                help="Get a playlist.")
@commands.has_permissions(manage_channels=True)
async def get_list_handler(ctx):
    _ftm = partial(rm_ext, prefix=" - ")
    result = ""
    if os.path.isfile(get_track_path(ctx)):
        result += "Tracks:\n"
        result += '\n -'.join(map(_ftm, filter(is_mp3, os.listdir(get_track_path(ctx)))))
    if os.path.isfile(get_announce_path(ctx)):
        result += "Announces:\n"
        result += '\n - '.join(map(_ftm, filter(is_mp3, os.listdir(get_announce_path(ctx)))))
    if os.path.isfile(get_insert_path(ctx)):
        result += "Inserts:\n"
        result += '\n'.join(map(_ftm, filter(is_mp3, os.listdir(get_insert_path(ctx)))))
    if not result:
        result = ":smiling_face_with_tear: Playlist is empty..."
    await ctx.reply(result)


@client.command(name='add-track',
                aliases=['+t'],
                help="Append track in playlist. Just send mp3 audio file with command.")
@commands.has_permissions(manage_channels=True)
async def add_track(ctx):
    await _get_attachments(ctx, get_track_path)


@client.command(name='add-insert',
                aliases=['+i'],
                help="Append insert in playlist. Just send mp3 audio file with command.")
@commands.has_permissions(manage_channels=True)
async def add_insert(ctx):
    await _get_attachments(ctx, get_insert_path)


@client.command(name='add-announce',
                aliases=['+a'],
                help="Append announce in playlist. Just send mp3 audio file with command.")
@commands.has_permissions(manage_channels=True)
async def add_announce(ctx):
    await _get_attachments(ctx, get_announce_path)


@client.command(name='rm-track',
                aliases=['-t'],
                help="Remove track from playlist.")
@commands.has_permissions(manage_channels=True)
async def rm_track(ctx):
    await _rm_file(ctx, get_track_path)


@client.command(name='rm-insert',
                aliases=['-i'],
                help="Remove insert from playlist.")
@commands.has_permissions(manage_channels=True)
async def rm_insert(ctx):
    await _rm_file(ctx, get_insert_path)


@client.command(name='rm-announce',
                aliases=['-a'],
                help="Remove announce from playlist.")
@commands.has_permissions(manage_channels=True)
async def rm_announce(ctx):
    await _rm_file(ctx, get_announce_path)


class CustomHelpCommand(commands.DefaultHelpCommand):
    async def prepare_help_command(self, ctx, command=None):
        self.no_category = "Commands"
        await super().prepare_help_command(ctx, command)

    def get_ending_note(self):
        return super().get_ending_note() + """

# How it work?

Radio works on principle of playing a random list of tracks.
An 'insert' is played between each 'track' (and 'announce').
Every third 'track' is played a random 'announce'.
"""


client.help_command = CustomHelpCommand()


async def _rm_file(ctx, path_fn):
    try:
        track_name = ctx.message.content[len(f'{PREFIX}{ctx.command.name} '):]
        result = await rm(ctx, track_name, path_fn(ctx))
        await ctx.reply(result)
    except Exception as e:
        _l.error(e)
        await ctx.reply(f':construction: Incorrect command. Example: {PREFIX}{ctx.command.name} <file name from !list>')


async def _get_attachments(ctx, patch_fn):
    if not ctx.message.attachments:
        await ctx.reply('Missing attachments.')
        return
    for att in ctx.message.attachments:
        if not att.filename.endswith(".mp3"):
            await ctx.reply(f'{att.filename} not mp3 file.')
            return
        path = os.path.join(patch_fn(ctx), normalize_file_name(att.filename))
        try:
            with requests.get(att.url, stream=True) as r:
                r.raise_for_status()
                os.makedirs(patch_fn(ctx), exist_ok=True)
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except Exception as e:
            _l.error(e)
            await ctx.reply(f'{att.filename} failed download.')
    GENERATORS[ctx.guild.id] = gen_playlist(ctx)


def on_audio_ended(ctx, _):
    _gen = GENERATORS.get(ctx.guild.id)
    if _gen is None:
        _gen = gen_playlist(ctx)
        GENERATORS[ctx.guild.id] = _gen
    player = GROUP_CALLS.get(ctx.guild.id)
    if player:
        new_file = next(_gen)

        def _run():
            player.play(FFmpegPCMAudio(new_file), after=partial(on_audio_ended, ctx))

        delay = Timer(1.0, _run)
        delay.start()


async def rm(ctx, file_name, path):
    _l.info(f'ID:{ctx.guild.id} rm {file_name} from {os.path.basename(path)}')
    try:
        items = list(map(rm_ext, filter(is_mp3, os.listdir(path))))
        if file_name not in items:
            return ':construction: File not found'
        rm_path = os.path.join(path, file_name + '.mp3')
        player = GROUP_CALLS.get(ctx.guild.id)
        player_stopped = False
        if player and player.is_playing():
            current_path = player.source.__dict__['_process'].args[2]
            if current_path == rm_path:
                player_stopped = True
                del GROUP_CALLS[ctx.guild.id]
                player.stop()
        await asyncio.sleep(0.1)
        os.remove(rm_path)
        GENERATORS[ctx.guild.id] = gen_playlist(ctx)
        if player_stopped:
            GROUP_CALLS[ctx.guild.id] = player
            on_audio_ended(ctx, None)
        return ':call_me: File was deleted successfully'
    except Exception as e:
        _l.error(f'ID:{ctx.guild.id} rm {file_name} error: {e}')
        return ':construction: An error occurred while deleting the file. Please check !list.'


def is_mp3(f_name):
    return f_name.endswith('.mp3')


def rm_ext(f_name, prefix=""):
    return f'{prefix}{f_name[:-4]}'


def normalize_file_name(filename: str):
    return filename.strip().replace(' ', '_')


def get_track_path(ctx):
    return os.path.join(os.getcwd(), 'data', str(ctx.guild.id), 'tracks')


def get_insert_path(ctx):
    return os.path.join(os.getcwd(), 'data', str(ctx.guild.id), 'inserts')


def get_announce_path(ctx):
    return os.path.join(os.getcwd(), 'data', str(ctx.guild.id), 'announces')


def gen_playlist(ctx):
    tracks = []
    if os.path.isdir(get_track_path(ctx)):
        tracks = list(map(
            lambda x: os.path.join(get_track_path(ctx), x),
            filter(is_mp3, os.listdir(get_track_path(ctx)))
        ))

    inserts = []
    if os.path.isdir(get_insert_path(ctx)):
        inserts = list(map(
            lambda x: os.path.join(get_insert_path(ctx), x),
            filter(is_mp3, os.listdir(get_insert_path(ctx)))
        ))

    announces = []
    if os.path.isdir(get_announce_path(ctx)):
        announces = list(map(
            lambda x: os.path.join(get_announce_path(ctx), x),
            filter(is_mp3, os.listdir(get_announce_path(ctx)))
        ))

    _l.debug(f'(Re)Create generator for ID:{ctx.guild.id} with T:{len(tracks)} A:{len(announces)} Z:{len(inserts)}')

    if not tracks:
        while True:
            yield os.path.join(os.getcwd(), DEFAULT_MP3)

    track_counter = 0
    while True:
        random.shuffle(tracks)
        for track in tracks:
            if track_counter == 3:
                track_counter = 0
                if len(inserts) > 0:
                    yield random.choice(inserts)
                if len(announces) > 0:
                    yield random.choice(announces)
            if len(inserts) > 0:
                yield random.choice(inserts)
            yield track
            track_counter += 1


if not os.path.isfile(DEFAULT_MP3):
    _l.warning(f'{DEFAULT_MP3} not found! Please use `docker cp {os.path.basename(DEFAULT_MP3)} <container-name>:/app'
               f'` for copy.')

try:
    client.run(os.getenv('DISCORD_TOKEN'))
except InterruptedError:
    exit(0)
except Exception as err:
    _l.error(err)
