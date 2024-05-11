from airtest.core.settings import Settings


class Config:
    ST = Settings
    ST.CVSTRATEGY = ["tpl", "akaze"]
    ST.THRESHOLD = 0.8

    # Top, left and bottom boundary pixel values when running in a bordered program
    # The value on my Win10 computer, may not accurate for everyone.
    BORDER = (32, 3, 2)
