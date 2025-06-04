import discord
from dotenv import load_dotenv
import os
import re
import requests
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
CACHED_APP_EMOJIS = {}

PLATFORMS_TO_CHECK = {
    'appleMusic': {
        'emoji_name': 'Apple_Music_icon',
        'name': 'Apple Music'
    },
    'spotify': {
        'emoji_name': 'Spotify_icon',
        'name': 'Spotify'
    },
    'youtube': {
        'emoji_name': 'Youtube_Music_icon',
        'name': 'YouTube'
    },
    'soundCloud': {
        'emoji_name': 'Soundcloud_icon',
        'name': 'SoundCloud'
    }
}

def find_music_link(text):
    """
    Checks a string for a Spotify, Apple Music, or SoundCloud link.
    Returns the first link found, or None if no link is found.
    """
    pattern = re.compile(
        r'http[s]?://'  # Match http or https
        r'(?:'          # Start a non-capturing group for the domains
        r'open\.spotify\.com/(?:track|album)/[a-zA-Z0-9]+'  # Spotify track or album
        r'|'            # OR
        r'music\.apple\.com/[\w/]+/(?:album|song)/[^/]+/\d+' # Apple Music song or album
        r'|'            # OR
        r'soundcloud\.com/[^/]+/[^/]+' # SoundCloud track
        r'|'
        r'youtu\.be/[\w-]+' 
        r'|'            # OR
        r'www\.youtube\.com/watch\?v=[\w-]+' 
        r')'           # End the non-capturing group
    )
    
    match = pattern.search(text)
    if match:
        return match.group(0) # Return the full matched URL
    return None


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    
    # --- Start of New Section: Fetch and Cache Emojis ---
    print("Fetching and caching application emojis...")
    try:
        # Fetch all emojis owned by this application
        app_emojis = await client.fetch_application_emojis()
        
        # Match the fetched emojis with the names in our config
        for platform_key, platform_info in PLATFORMS_TO_CHECK.items():
            emoji_name_to_find = platform_info['emoji_name']
            found_emoji = discord.utils.get(app_emojis, name=emoji_name_to_find)
            
            if found_emoji:
                CACHED_APP_EMOJIS[platform_key] = found_emoji
                print(f"  Successfully cached emoji '{emoji_name_to_find}'")
            else:
                print(f"  WARNING: Could not find an application emoji named '{emoji_name_to_find}'.")
                # Fallback to a default emoji so the bot doesn't crash
                CACHED_APP_EMOJIS[platform_key] = '▪️' 

    except discord.errors.Forbidden:
        print("Error: Bot does not have permission to fetch application emojis.")
    except Exception as e:
        print(f"An unexpected error occurred during emoji fetching: {e}")
    # --- End of New Section ---

@client.event
async def on_message(message):
        if message.author == client.user:    
            return
        
        
          # Regex to find Spotify track URLs
        music_link = find_music_link(message.content)

        if music_link:
       
            api_url = f'https://api.song.link/v1-alpha.1/links?url={music_link}'\
            
            try:
                response = requests.get(api_url)
                response.raise_for_status()
                data = response.json()
               
                song_info = data['entitiesByUniqueId'][data['entityUniqueId']]
                song_title = song_info.get('title', 'Unknown Title')
                artist_name = song_info.get('artistName', 'Unknown Artist')
                thumbnail_url = song_info.get('thumbnailUrl')

                embed = discord.Embed(title=f"{song_title} by {artist_name}", color=discord.Color.blue())

                if thumbnail_url:
                    embed.set_thumbnail(url=thumbnail_url)
                

                platform_links = data.get('linksByPlatform', {}) 
                clickable_icons = []
                for platform_key, platform_value in PLATFORMS_TO_CHECK.items():
                    if platform_key in platform_links:
                        platform_url = platform_links[platform_key]['url']
                        platform_emoji = CACHED_APP_EMOJIS.get(platform_key, '▪️')
                        # Create a clickable link where the text is the standard emoji
                        clickable_icons.append(f"\n[{platform_emoji} {platform_value['name']}]({platform_url})\n")
                if clickable_icons:
                    embed.add_field(
                        name="Listen On:\n",
                        value=" ".join(clickable_icons),
                        inline=True
                    )
                await message.channel.send(embed=embed)
                

                
            except requests.exceptions.RequestException as e:
                print(f"Error calling Odesli API: {e}")
                error_embed = discord.Embed(
                    title="API Error",
                    description="Sorry, I had trouble converting that link right now.",
                    color=discord.Color.orange()
                )
                await message.channel.send(embed=error_embed)
            
client.run(DISCORD_TOKEN)