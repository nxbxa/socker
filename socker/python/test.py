import matplotlib.font_manager as fm

fonts = fm.findSystemFonts()

for font in fonts:
    if any(name in font.lower() for name in [
        "arial",
        "segoe",
        "calibri",
        "tahoma",
        "simhei",
        "simsun",
        "noto"
    ]):
        print(font)