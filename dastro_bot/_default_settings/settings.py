import languages

# Loggers
LOG_FILE = "dastro_bot.log"
LOGGER_NAME = "Star Citizen Discord Astro-Bot logger"

# language
messages = languages.messages_en
additional_commands = languages.commands_en

# server
GUILD_ID = 000000000000000000
CHANNELS = {
    'main': '000000000000000000',
    'lobby': '000000000000000000',
    'recruitment': '000000000000000000',
}
MEMBER_ROLES = [
    'member',
    'older member'
]
PRIVILEGED_ROLES = [
    'officer',
    'admin'
]
MESSAGE_MAX_CHARACTERS = 2000
MESSAGE_MAX_SHIPS = 24

# Database manager
DATABASE_NAME = "database.sqlite"
DATABASE_DIALECT = 'sqlite:///%s'

# MongoDB
MONGO_CONNECTION_STRING = "mongodb://127.0.0.1:27017"

# RSI DATA PARSER
BASE_URL = "https://robertsspaceindustries.com"
SHIP_DATA_HEADERS = ['manufacturer', 'name', 'price', 'focus', 'production_status', 'length', 'beam', 'height',
                     'size', 'mass', 'cargocapacity', 'min_crew', 'max_crew', 'scm_speed', 'afterburner_speed']
SHIP_UPGRADES_URL = BASE_URL + "/pledge/ship-upgrades"
SHIPS_MATRIX_URL = BASE_URL + "/ship-matrix/index"
GAME_PACKAGES_URL = BASE_URL + "/pledge/game-packages"
SHIPS_MATRIX_KEYS = ["name", "focus", "url", "production_status", "length", "beam", "height", "size", "mass",
                     "cargocapacity", "min_crew", "max_crew", "scm_speed", "afterburner_speed"]

API_INIT_URL = BASE_URL + "/roadmap/board/1-Star-Citizen"
ROAD_MAP_URL = BASE_URL + "/api/roadmap/v1/boards/1"
SQ_ROAD_MAP_URL = BASE_URL + "/api/roadmap/v1/boards/2"
FORUM_SEARCH_URL = BASE_URL + "/api/spectrum/search/content/extended"
FORUM_SEARCH_PAYLOAD = {
    "community_id": "1",
    "highlight_role_id": "2",
    "type": ["", "op"],
    "text": "",
    "page": 1,
    "sort": "latest",
    "range": "week",
    "visibility": "nonerased"
}

# Price reporter
REPORT_SHIP_PRICE_LIST = [
            ("Cutlass Black", 100),
            ("Avenger Titan", 50),
        ]

# Trade Assistant
SCM_TOKEN = "YOURTOKEN"
