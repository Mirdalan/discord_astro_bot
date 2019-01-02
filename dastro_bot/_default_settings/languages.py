from collections import namedtuple


Messages = namedtuple('Messages', [
    'ship_not_exists',
    'multiple_ships_found',
    'member_not_found',
    'member_ships_modified',
    'member_ships_invalid',
    'member_ship_not_found',
    'ship_price_unknown',
    'ship_from_report_not_found',
    'ship_price_report',
    'new_version',
    'road_map_not_found',
    'something_went_wrong',
    'success'
])

Commands = namedtuple('Commands', [
    'help',
    'fleet',
    'add_ship',
    'remove_ship',
    'clear_member_ships',
    'remove_member',
    'prices',
    'ship',
    'compare',
    'releases',
    'roadmap',
    'trade',
    'mining',
    'trade_report',
    'mining_report',
])

messages_pl = Messages(
    ship_not_exists="%s, taki okręt nie istnieje!",
    multiple_ships_found="Niestety, nie jestem pewien czego dokładnie szukasz druhu. Czy chodziło Ci może o ...\n%s",
    member_not_found="Przykro mi, nie znalazłem takiej osoby.",
    member_ships_modified="Drogi %s, zanotowałem. Oto Twoja aktualna flota:",
    member_ships_invalid="%s, przykro mi lecz takie statki nie istnieją:",
    member_ship_not_found="%s, przykro mi lecz nie posiadasz tego statku.",
    ship_price_unknown="Wybacz Panie Bracie, lecz nie znam ceny okrętu *%s*  **%s**.",
    ship_from_report_not_found="Czołem!\nNie mogłem odnaleźć żadnych wieści o statku *%s*.",
    ship_price_report="Czołem!\n *%s* obecnie kosztuje *%s*",
    new_version="Czołem! Przynoszę Wam wieści:\n%s",
    road_map_not_found="Przykro mi, nic takiego nie znalazłem. Posiadam jednakże wiedzę o poniższych:\n```%s```",
    something_went_wrong="Coś poszło nie tak...",
    success="Udało się!",
)

commands_pl = Commands(
    help="pomoc",
    fleet="flota",
    add_ship="dodaj",
    remove_ship="usuń",
    clear_member_ships="usuń moje statki",
    remove_member="usuń_członka",
    prices="ceny",
    ship="statek",
    compare="porównaj",
    releases="wersje",
    roadmap="obiecanki",
    trade="handel",
    mining="kopanie",
    trade_report="raport_handlowy",
    mining_report="raport_górniczy",
)

messages_en = Messages(
    ship_not_exists="%s, there's no such ship!",
    multiple_ships_found="Not sure what you mean. Maybe try one of this:\n%s",
    member_not_found="I'm sorry, there's no such member.",
    member_ships_modified="%s Here's your updated fleet:",
    member_ships_invalid="%s, sorry but those ships are not valid:",
    member_ship_not_found="%s, sorry but you don't have such ship.",
    ship_price_unknown="I'm sorry but I don't knowh price of *%s*  **%s**.",
    ship_from_report_not_found="Sorry, didn't find anything on ship *%s*.",
    ship_price_report="The price of *%s* is updated to *%s*",
    new_version="Howdy! I found some news:\n%s",
    road_map_not_found="Sorry, didn't find anything like that. You may try something like:\n```%s```",
    something_went_wrong="Something went wrong...",
    success="Done!",
)

commands_en = Commands(
    help="help",
    fleet="fleet",
    add_ship="add_ship",
    remove_ship="remove_ship",
    clear_member_ships="clear my ships",
    remove_member="remove_member",
    prices="prices",
    ship="ship",
    compare="compare",
    releases="releases",
    roadmap="roadmap",
    trade="trade",
    mining="mining",
    trade_report="trade_report",
    mining_report="mining_report",
)
