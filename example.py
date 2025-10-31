import logging
import time

from rd_api_py.rdapi import RD
from torrentsearchengine.searchengine import TorrentSearchEngine

RD = RD()
engine = TorrentSearchEngine()

engine.add_provider('sites/kickasstorrents.json5')
# engine.add_provider('sites/eztv.json5')
# engine.add_provider('sites/ettv.json')
engine.add_provider('sites/1337x.json5')
engine.add_provider('sites/magnetdl.json5')
engine.add_provider('sites/piratebay.json5')
# engine.enable_debrid() #= Default
# engine.disable_debrid()

query = 'metallica master of puppets'

results = engine.search(query, limit=10, timeout=5)

results = results[:1]

for result in results:
    result.startDebridDownload()
    result.updateInfo()

    logging.info(
        f"{result['info']['filename']}: [{result['info']['status']}]\t{result['info']['progress']}%")
    while result['info']["progress"] < 100 and not result['info']["status"] in ["uploading", "error"]:
        time.sleep(20)
        result.updateInfo()
        logging.info(f"{result['info']['filename']}: [{result['info']['status']}]\t{result['info']['progress']}% {result['info']['seeders']}S")
