import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix, lang
get_lang = lang.get_lang

import utils.global_variables as gv
import random


def get_wordplay(type: str) -> str:
    kappa = "<:kappa:856251476900184074>"
    laugh_emojis = [
        "",
        "<:superjoy:573231729800642570>",
        "<a:yellowlaugh:1480581617960357908>",
        "<a:yellowlaugh:1480581617960357908>",
        "<:shybimbo:1480581796109357199>",
        "<:kick_feet:1480581817395450008>",
        "<a:princess_yawning:1480586554236866701>",
        "<a:lebron:1480588484870672395>",
        ":sob:",
        ":joy::rofl:",
        ":joy_cat:",
        ":cold_face::pleading_face:",
        ":slight_smile:",
    ]
    
    if type == "quoi":
        choices = [
            "https://cdn.discordapp.com/attachments/1479516231009697813/1479537551512441046/345c0a19fc4f3a3b.mp4?ex=69ac6638&is=69ab14b8&hm=c101b46fb5765daee93edaa2a290911e58dd4921550f68eceb58ce2b1c0e1b0c&",
            "https://cdn.discordapp.com/attachments/1479516231009697813/1479537458889752596/32c9c743089f2128.mp4?ex=69ac6622&is=69ab14a2&hm=f60577ddeba41c2fa7e5e8574abd15b1fb361218078338028ea2fc9dba69f8e4&",
            "https://cdn.discordapp.com/attachments/1479516231009697813/1479537341935648821/8dccea9f06129f43.mp4?ex=69ac6606&is=69ab1486&hm=881b168ca9680b86c3069505e7515519d33dba7d6caca86dcb009ece30dc3359&",
            "https://cdn.discordapp.com/attachments/1479516231009697813/1479537305684279569/698727a031784a1f.mp4?ex=69ac65fe&is=69ab147e&hm=ea7b5ebafbbc2c97c6edd3f7394cbdd94075a4c19024b9edc0d723e9a7753a78&",
            "https://cdn.discordapp.com/attachments/1479516231009697813/1479537278270443691/55114bb218fc5671.mp4?ex=69ac65f7&is=69ab1477&hm=b0a184eb1db4d43ddbfd8b91245e21abc8c35efb418db27a2d29c816f1317285&",
            "FEUR",
            "feur. XDXDXDXD",
            "drilatère[.](https://tenor.com/view/kirby54-qi-iq-genie-genius-gif-14183546)",
        ]
        
        return random.choice(choices)
    
    if type == "hein":
        choices = [
            f"DEUX {random.choice(laugh_emojis)}",
            f"deux {random.choice(laugh_emojis)}",
            f"2 {random.choice(laugh_emojis)}",
            "bécile <:BrainDead:1480589396335001823>",
            "telligent :brain:<:BrainExpand:1480589602485174484>",
        ]
        
        return random.choice(choices)
    
    if type == "oui":
        monkey_emoji = random.choice([
            "<a:stiti1:896356647369342976>",
            "<a:stiti2:896355724165275658>",
        ])
        
        choices = [
            random.choice([f"STITI XDXD {monkey_emoji}", f"STITI {monkey_emoji}"]),
            f"stiti {monkey_emoji}",
            "https://cdn.discordapp.com/attachments/1479516231009697813/1480583457527566569/6157559c60dcbe14.mp4?ex=69b0344c&is=69aee2cc&hm=d14c57231db61c06c62a310b197acb96e819552101f1b25af9c8041e386a2d0e&",
            random.choice([
                "https://cdn.discordapp.com/attachments/1479516231009697813/1480583480726523994/9dc6baa7a811a118.mp4?ex=69b03451&is=69aee2d1&hm=c55d88dc310cf6713b923f1b292cb0743bbd42b66669ee374bc422cbe8ee7ab8&",
                "https://cdn.discordapp.com/attachments/1479516231009697813/1480583503988003002/1fde4bdb610b84b1.mp4?ex=69b03457&is=69aee2d7&hm=029480486ea465386e9f8f91a8f5c0f7a52ea013b3973054762566aac7df425d&",
            ])
        ]
        
        return random.choice(choices)
    
    if type == "ouais":
        laugh_emojis.append("XDXD")
        choices = [
            "stern.",
            f"STERN {random.choice(laugh_emojis)}",
            f"STERN {random.choice(laugh_emojis)}",
        ]
        return random.choice(choices)
    
    if type == "non":
        choices = [
            f"BRIL {random.choice(laugh_emojis)}",
            "bril :P",
            "bril.",
        ]
        if random.randint(1, 10) == 1:
            choices = [
                "BRIL XD T4AS COMPRIS PARCE QUE NOMBRIL LE JEU DE MOTS xD",
            ]
        
        return random.choice(choices)
    
    if type == "chaud":
        choices = [
            f"FAGE XDDDD {kappa}",
            "fage <:chaud:898580659638001675>",
            f"FAGE <:chaud:898580659638001675> {random.choice(laugh_emojis)}",
        ]
        
        return random.choice(choices)
    
    if type == "tulasvu":
        choices = [
            f"mon cul? {kappa}",
            f"MON CUL {random.choice(laugh_emojis)}",
            f"mon q :money_mouth: {random.choice([':hatched_chick:', ''])}",
        ]
        
        return random.choice(choices)
    
    if type == "ah":
        choices = [
            f"bricot {random.choice(laugh_emojis)}",
            f"BRICOT!!! {random.choice(laugh_emojis)}",
            f"BRICOT {random.choice(laugh_emojis)}",
        ]
        return random.choice(choices)
    
    if type == "re":
        fox_emojis = [
            "<a:foxspin:1480590882225782856>",
            "<:foxShrugDX:1480591106696548442>",
            ":fox:",
        ]
        choices = [
            f"nard {random.choice(fox_emojis)}{random.choice(laugh_emojis)}",
            f"NARD!!! {random.choice(fox_emojis)}{random.choice(laugh_emojis)}",
            f"NARD {random.choice(fox_emojis)}{random.choice(laugh_emojis)}",
        ]
        return random.choice(choices)

gv.set("get_wordplay", get_wordplay)

async def wordplay(message, wordplay_type: str):
    await message.channel.send(
        get_wordplay(wordplay_type)
    )

async def wordplay_slash(interaction: nextcord.Interaction, wordplay_type: str):
    await interaction.response.send_message(
        get_wordplay(wordplay_type)
    )


info = {
    "wordplay": {
        "category": "fun",
        "aliases": [],
        "hidden_aliases": ["jeudemot", "jeuxdemot", "jeudemots", "jeuxdemots"], # unused since it's not a text command
        "locale_only": nextcord.Locale.fr,
        "available": ["slash_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "wordplay_name",
        "desc": "wordplay_desc",
        "args": [
            {
                "name": "wordplay_arg_name",
                "desc": "wordplay_arg_desc",
                "required": True,
            }
        ]
    },
    "quoi": {
        "category": "fun",
        "aliases": ["feur"],
        "hidden_aliases": ["koi", "kwoi", "qwa", "feure", "drilatere",
                           "coiffeur", "coifeur", "quoiffeur", "quoifeur",
                           ""],
        "locale_only": nextcord.Locale.fr,
        "available": ["text_command"],
    },
    "hein": {
        "category": "fun",
        "aliases": ["deux"],
        "hidden_aliases": ["hin", "2", "becile", "telligent",
                           "intelligent", "inteligent", "imbecile", "inbecile",
                           "heindeux", "hein2", "hin2"],
        "locale_only": nextcord.Locale.fr,
        "available": ["text_command"],
    },
    "oui": {
        "category": "fun",
        "aliases": ["stiti"],
        "hidden_aliases": ["woui", "ui", "wui", "wi", "vui",
                           "ouistiti", "wistiti", "wiistiti", "uistiti", "westiti"],
        "locale_only": nextcord.Locale.fr,
        "available": ["text_command"],
    },
    "ouais": {
        "category": "fun",
        "aliases": ["stern"],
        "hidden_aliases": ["ouai", "wouais", "wouai", "oue", "oe",
                           "ouaistern", "oestern", "western", "ouestern"],
        "locale_only": nextcord.Locale.fr,
        "available": ["text_command"],
    },
    "non": {
        "category": "fun",
        "aliases": ["bril"],
        "hidden_aliases": ["nn", "nan", "nion", "sinon", "sinn", "sinan", "nom",
                           "nombril", "nonbril"],
        "locale_only": nextcord.Locale.fr,
        "available": ["text_command"],
    },
    "chaud": {
        "category": "fun",
        "aliases": ["ffage"],
        "hidden_aliases": ["cho", "chaux", "chox", "fage",
                           "chauffage", "chaufage", "chofage", "choffage"],
        "locale_only": nextcord.Locale.fr,
        "available": ["text_command"],
    },
    "tulasvu": {
        "category": "fun",
        "aliases": ["moncul"],
        "hidden_aliases": ["tu las vu", "tu la vu", "la tu vu", "las tu vu",
                           "mon cul", "mon q", "mon c", "monq"],
        "locale_only": nextcord.Locale.fr,
        "available": ["text_command"],
    },
    "ah": {
        "category": "fun",
        "aliases": ["bricot"],
        "hidden_aliases": ["a", "abricot"],
        "locale_only": nextcord.Locale.fr,
        "available": ["text_command"],
    },
    "re": {
        "category": "fun",
        "aliases": ["nard"],
        "hidden_aliases": ["r", "renard"],
        "locale_only": nextcord.Locale.fr,
        "available": ["text_command"],
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class WordplayCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in cmd.user_permissions})
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
    )
    async def wordplay_command(self, interaction: nextcord.Interaction,
        wordplay_type: str = get_slash_option(cmd.arg(0), custom_choices={
            'quoi/feur': 'quoi',
            'hein/deux': 'hein',
            'oui/stiti': 'oui',
            'ouais/stern': 'ouais',
            'non/bril': 'non',
            'chaud/ffage': 'chaud',
            # 'tu l\'as vu?/mon cul': 'tulasvu',
            'ah/bricot': 'ah',
            're/nard': 're',
        })
    ):
        await wordplay_slash(interaction, wordplay_type)


def setup(bot: commands.Bot):
    bot.add_cog(WordplayCog(bot))


async def _message_handler(bot, message: nextcord.Message, lang: str, prefix_str: str, wordplay_type: str):
    await wordplay(message, wordplay_type)

_message_handlers = {
    wordplay_type: lambda bot, msg, l, p, wt=wordplay_type: _message_handler(bot, msg, l, p, wt)
    for wordplay_type in ["quoi", "hein", "oui", "ouais", "non", "chaud", "tulasvu", "ah", "re"]
}
