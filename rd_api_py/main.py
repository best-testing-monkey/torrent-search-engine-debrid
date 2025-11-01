from rdapi import RD

RD = RD()

result = RD.torrents.add_magnet('magnet:?xt=urn:btih:94bb1500406fb2e3ead8db9e41e8a709d1d1e3f7&dn=Rishloo+-+Feathergun+%282009%29+%5Bmp3%40160%5D&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969&tr=udp%3A%2F%2Fzer0day.ch%3A1337&tr=udp%3A%2F%2Fopen.demonii.com%3A1337&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fexodus.desync.com%3A6969').json()
currentId = result["id"]
print(result)