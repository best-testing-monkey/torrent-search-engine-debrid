import logging

logger = logging.getLogger(__name__)

class TorrentResult(dict[str, object]):
    def __init__(self):
        super().__init__()
        return
    def __init__(self, base_dict: dict):
        super().__init__()
        for key in base_dict.keys():
            self[key] = base_dict[key]

        if "info" in self.keys() and "title" in self['info'].keys() and "filename" not in self['info'].keys():
            self["info"]["filename"] = self["info"]["title"]

        if "magnet" not in self.keys() and "hash" in self.keys():
            magnetHash = self["hash"]
            magnetUrl = "magnet:?xt=urn:btih:" + magnetHash
            self["magnet"] = magnetUrl
        return

        if "info" in self.keys() and "magnet" not in self.keys():
            torrent_info = self["info"]
            if "hash" in torrent_info.keys():
                magnetHash = torrent_info["hash"]
                magnetUrl = "magnet:?xt=urn:btih:" + magnetHash
                self["magnet"] = magnetUrl
            if "magnet" in torrent_info.keys():
                self["magnet"] = torrent_info["magnet"]
        return

    def asdict(self):
        base_dict = {}
        for key in self.keys():
            self[key] = base_dict[key]
        return base_dict

