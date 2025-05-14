# common_service.py

from serp import Serp

class CommonService:
    def __init__(self):
        # bây giờ Serp là class bạn vừa viết
        self.serp = Serp()

    def process(self, json_data, log):
        raise NotImplementedError("Các service con phải override method này")
