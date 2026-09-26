"""English words for Majora's Mask text-bearing textures (from the decomp's names).

label(path) -> list of lines, or None.  "|" in a FIX entry splits lines.
Names come from 2S2H's asset XML (gItemName*ENGTex, gDoAction*ENGTex, gFileSel*ENGTex, ...).
"""
import re

FIX = {
    # item names that need punctuation or differ from the symbol
    "HerosBow": "Hero's Bow", "GreatFairysSword": "Great Fairy's Sword", "FullMilk": "Milk",
    "HalfMilk": "Milk (1/2)", "MoonsTear": "Moon's Tear", "FierceDeitysMask": "Fierce Deity's Mask",
    "KafeisMask": "Kafei's Mask", "GarosMask": "Garo's Mask", "RomanisMask": "Romani's Mask",
    "CircusLeadersMask": "Circus Leader's Mask", "PostmansHat": "Postman's Hat",
    "CouplesMask": "Couple's Mask", "GreatFairysMask": "Great Fairy's Mask", "DonGerosMask": "Don Gero's Mask",
    "KamarosMask": "Kamaro's Mask", "CaptainsHat": "Captain's Hat", "GiantsMask": "Giant's Mask",
    "HerosShield": "Hero's Shield", "Quiver30": "Quiver", "Quiver40": "Big Quiver", "Quiver50": "Biggest Quiver",
    "BombBag20": "Bomb Bag", "BombBag30": "Big Bomb Bag", "BombBag40": "Biggest Bomb Bag",
    "OdolwasRemains": "Odolwa's Remains", "GohtsRemains": "Goht's Remains", "GyorgsRemains": "Gyorg's Remains",
    "TwinmoldsRemains": "Twinmold's Remains", "ElegyOfEmptyness": "Elegy of Emptiness",
    "NewWaveBossaNova": "New Wave Bossa Nova", "EponasSong": "Epona's Song", "BombersNotebook": "Bombers' Notebook",
    "SpecialDeliveryToMama": "Special Delivery to Mama", "LetterToKafei": "Letter to Kafei",
    "PictographBox": "Pictograph Box", "DekuPrincess": "Deku Princess", "BigKey": "Boss Key",
    "DungeonMap": "Map", "StrayFairies": "Stray Fairies", "LullabyIntro": "Lullaby Intro",
    "SeaHorse": "Sea Horse", "ChateauRomani": "Chateau Romani", "MaskOfScents": "Mask of Scents",
    "MaskOfTruth": "Mask of Truth", "LensOfTruth": "Lens of Truth", "OcarinaOfTime": "Ocarina of Time",
    "SongOfTime": "Song of Time", "SongOfHealing": "Song of Healing", "SongOfSoaring": "Song of Soaring",
    "SongOfStorms": "Song of Storms", "SonataOfAwakening": "Sonata of Awakening", "OathToOrder": "Oath to Order",
    "PieceOfHeart": "Piece of Heart", "PendantOfMemories": "Pendant of Memories", "AllNightMask": "All-Night Mask",
    # do-action (A button) labels
    "Num1": "1", "Num2": "2", "Num3": "3", "Num4": "4", "Num5": "5", "Num6": "6", "Num7": "7", "Num8": "8",
    "PutAway": "Put Away", "Navi": "Tatl", "Decide": "Decide",
    # file select
    "AreYouSureCopy": "Are you sure?", "AreYouSureErase": "Are you sure?",
    "CheckBrightness": "Adjust the brightness", "CopyButton": "Copy", "EraseButton": "Erase",
    "CopyToWhichFile": "Copy to which file?", "CopyWhichFile": "Copy which file?",
    "DecideCancel": "Decide|Cancel", "DecideSave": "Decide|Save", "ENDButton": "END",
    "EraseWhichFile": "Erase which file?", "File1Button": "File 1", "File2Button": "File 2",
    "File3Button": "File 3", "FileCopied": "File copied.", "FileEmpty": "This file is empty.",
    "FileErased": "File erased.", "FileInUse": "This file is in use.", "FinalDay": "Final Day",
    "FirstDay": "First Day", "SecondDay": "Second Day", "Headset": "Headset", "Hold": "Hold",
    "MASKS": "MASKS", "Mono": "Mono", "Name": "Name", "NoEmptyFile": "There is no empty file.",
    "NoFileToCopy": "No file to copy.", "NoFileToErase": "No file to erase.", "OpenThisFile": "Open this file?",
    "OptionsButton": "Options", "Options": "Options", "PleaseSelectAFile": "Please select a file.",
    "PleaseWait": "Please wait...", "QuitButton": "Quit", "Sound": "Sound", "Stereo": "Stereo",
    "Surround": "Surround", "Switch": "Switch", "Targeting": "Z Targeting", "YesButton": "Yes",
    # pause screen
    "Map10": "Map", "Masks10": "Masks", "QuestStatus00": "Quest", "QuestStatus10": "Status",
    "SelectItem00": "Select", "SelectItem10": "Item", "ToDecide": "to Decide", "ToEquip": "to Equip",
    "ToMap": "to Map", "ToMasks": "to Masks", "ToPlayMelody": "to Play Melody",
    "ToQuestStatus": "to Quest Status", "ToSelectItem": "to Select Item", "ToViewNotebook": "to View Notebook",
    "GreatBayTitle": "Great Bay", "SnowheadTitle": "Snowhead", "StoneTowerTitle": "Stone Tower",
    "WoodfallTitle": "Woodfall",
    # map points
    "ZoraHall": "Zora Hall", "IkanaGraveyard": "Ikana Graveyard", "IkanaCanyon": "Ikana Canyon",
    "GreatBayCoast": "Great Bay Coast", "ZoraCape": "Zora Cape",
    # day telop / clock / notebook
    "1st": "1st Day", "2nd": "2nd Day", "Final": "Final Day", "Day1st": "1st Day", "Day2nd": "2nd Day", "DayFinal": "Final Day", "TimeOfDay": "Time",
    "FirstDayLeft": "Dawn of|The First Day", "SecondDayLeft": "Dawn of|The Second Day",
    "FinalDayLeft": "Dawn of|The Final Day", "NewDayLeft": "Dawn of|A New Day",
    "72Hours": "-72 Hours Remain-", "48Hours": "-48 Hours Remain-", "24Hours": "-24 Hours Remain-",
    "CUp": "Tatl", "Copyright2000Nintendo": "(C) 2000 Nintendo",
    "ControllerNotConnectedText": "Controller not connected", "InsertControllerText": "Insert a controller",
    "TheLegendOfText": "THE LEGEND OF", "PressStart": "PRESS START",
    # boss title cards (subtitle | name)
    "OdolwaTitleCard": "Masked Jungle Warrior|Odolwa", "GohtTitleCard": "Masked Mechanical Monster|Goht",
    "GyorgTitleCard": "Gargantuan Masked Fish|Gyorg", "TwinmoldTitleCard": "Giant Masked Insect|Twinmold",
    "MajorasMaskTitleCard": "Majora's Mask", "MajorasIncarnationTitleCard": "Majora's Incarnation",
    "MajorasWrathTitleCard": "Majora's Wrath",
}

PREFIXES = ("gItemName", "gDoAction", "gFileSel", "gPause", "gMapPoint", "gBombersNotebook", "gDaytelop",
            "gTatl", "gTitleScreen", "gClockDay")
SKIP = re.compile(r"(QuarterHeart|FileNameBox|DolbySurroundLogo|Mask\d\dTex|Flame\d|ZeldaLogo|MajorasMask(Subtitle)?(Mask)?Tex$"
                  r"|Digit\d|Colon|1800|Box|Bar|Line|Circle|Arrow|Stamp|Cursor|Connector|Photo|Background|Icon)")


def split_camel(s):
    s = re.sub(r"(?<=[a-z])(?=[A-Z0-9])|(?<=[0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", s)
    small = {"Of", "To", "The", "A", "And", "In"}
    words = s.split()
    return " ".join(w.lower() if i and w in small else w for i, w in enumerate(words))


def label(path):
    base = path.rsplit("/", 1)[-1]
    if not base.endswith("Tex"):
        return None
    if re.search(r"(JPN|GER|FRA|SPA|ESP)Tex$", base):
        return None                              # other-language slots: not shown on US
    for pre in PREFIXES:
        if base.startswith(pre):
            if pre in ("gPause", "gFileSel", "gTatl", "gMapPoint", "gDoAction", "gItemName") and not base.endswith("ENGTex"):
                return None                      # panel pieces / non-text slots
            core = base[len(pre):-3]
            core = re.sub(r"(ENG|NES)$", "", core)
            if SKIP.search(base) and core not in FIX:
                return None
            if core in FIX:
                return FIX[core].split("|")
            if base.startswith("gTitleScreen"):
                return None
            if core.endswith("Right"):              # day telop right halves continue the left
                return None
            return [split_camel(core)]
    for key in ("OdolwaTitleCard", "GohtTitleCard", "GyorgTitleCard", "TwinmoldTitleCard",
                "MajorasMaskTitleCard", "MajorasIncarnationTitleCard", "MajorasWrathTitleCard"):
        if base == "g" + key + "Tex":
            return FIX[key].split("|")
    return None


if __name__ == "__main__":
    import glob
    import sys
    names = set()
    for f in glob.glob(sys.argv[1] + "/**/*.xml", recursive=True):
        names |= set(re.findall(r'Name="(g\w+Tex)"', open(f, encoding="utf-8").read()))
    got = {n: label("x/" + n) for n in sorted(names)}
    got = {n: v for n, v in got.items() if v}
    for n, v in got.items():
        print(f"{n:48s} {' | '.join(v)}")
    print(len(got), "labels")
