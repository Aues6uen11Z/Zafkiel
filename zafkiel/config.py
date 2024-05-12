from airtest.core.settings import Settings


class Config:
    ST = Settings
    ST.CVSTRATEGY = ["tpl", "akaze"]
    ST.THRESHOLD = 0.8
