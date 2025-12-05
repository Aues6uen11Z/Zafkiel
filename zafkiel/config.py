from airtest.core.settings import Settings


class Config:
    ST = Settings
    ST.CVSTRATEGY = ["tpl", "akaze"]
    ST.THRESHOLD = 0.8
    KEEP_FOREGROUND = False
    BUFFER_TIME = 3     # seconds, time to wait before bringing window to foreground
