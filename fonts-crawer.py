import argparse
import os
import urllib.request

parser = argparse.ArgumentParser(description="Google Fonts Crawler")
parser.add_argument("fontFamily", help="The name of the Font Family that you wish to crawl.")
parser.add_argument("-fd", "--fontDirectory", default=None, help="The directory that the font files will save to. Default directory is 'fonts/{{ fontFamily }}' relative to current folder.")
parser.add_argument("-cd", "--cssDirectory", default="css/fonts", help="The directory that the css file will save to. Default directory is 'css/fonts' relative to current folder.")
parser.add_argument("-w", "--weights", default=None, help="The font style and weights that you wish to crawl, seperated with commas. Default to grab all available weights and styles.")
args = parser.parse_args()

fontFamily = args.fontFamily
if fontFamily is None or len(fontFamily) == 0:
    raise Exception("Font Family cannot be none")

weights = args.weights
if weights is None:
    weights = ""
    for i in range(9):
        weights += str((i + 1) * 100) + ","
    for i in range(9):
        weights += str((i + 1) * 100) + "italic,"
    weights = weights[:-1]

googleUrl = "https://fonts.googleapis.com/css?family="
googleUrl += fontFamily + ":" + weights

fontWeightMap = {
    "100": "Thin",
    "200": "ExtraLight",
    "300": "Light",
    "400": "Regular",
    "500": "Medium",
    "600": "SemiBold",
    "700": "Bold",
    "800": "ExtraBold",
    "900": "Black"
}

userAgents = {
    "eot": 'Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)',
    "woff": 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:27.0) Gecko/20100101 Firefox/27.0',
    "woff2": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:61.0) Gecko/20100101 Firefox/61.0',
    "svg": 'Mozilla/4.0 (iPad; CPU OS 4_0_1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/4.1 Mobile/9A405 Safari/7534.48.3',
    "ttf": 'Mozilla/5.0'
}

print("Preparing directories")
if args.fontDirectory is None:
    fontDirectory = "fonts/" + fontFamily
else:
    fontDirectory = args.fontDirectory
cssDirectory = args.cssDirectory
directories = [fontDirectory, cssDirectory]
for directory in directories:
    if not os.path.exists(directory):
        os.makedirs(directory)

print("Downloading css files from Google")
cssFiles = []
for fontType, userAgent in userAgents.items():
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', userAgent)]
    urllib.request.install_opener(opener)
    fileName = cssDirectory + "/" + fontFamily + "." + fontType + ".css"
    urllib.request.urlretrieve(googleUrl, fileName)
    cssFiles.append({
        "name": fileName,
        "fontType": fontType.lower()
    })

def getNext(content, firstKey, lastKey=None, iterate=1):
    content = content.split(firstKey, iterate)
    if lastKey is not None:
        content = content[iterate]
        content = content.split(lastKey, 1)
        iterate = 1
    return content[iterate], content[0].strip()

def getInfo(cssFile, splitStr, infoKeys, ext):
    f = open(cssFile, "r")
    contents = f.read()
    splittedContents = contents.split(splitStr)
    parsedContents = []
    for content in splittedContents:
        content = content.strip()
        if len(content) == 0:
            continue
        if "unicodeRange" in infoKeys:
            content, unicodeRangeName = getNext(content, None)
        else:
            unicodeRangeName = None
        content, fontStyle = getNext(content, "font-style:", ";")
        content, fontWeight = getNext(content, "font-weight:", ";")
        localNames = []
        if "localNames" in infoKeys:
            for i in range(2):
                content, localName = getNext(content, "local('", "')")
                localNames.append(localName)
        content, url = getNext(content, "url(", ")")
        if "fontFormat" in infoKeys:
            content, fontFormat = getNext(content, "format('", "')")
        else:
            fontFormat = None
        if "unicodeRange" in infoKeys:
            content, unicodeRange = getNext(content, "unicode-range:", ";")
        else:
            unicodeRange = None
        name = fontFamily + "-" + fontWeightMap[fontWeight]
        if fontStyle.lower() == "italic":
            name += "Italic"
        parsedContents.append({
            "unicodeRangeName": unicodeRangeName,
            "fontStyle": fontStyle,
            "fontWeight": fontWeight,
            "name": name,
            "localNames": localNames,
            "url": url,
            "unicodeRange": unicodeRange,
            "fontFormat": fontFormat,
            "ext": ext
        })
    f.close()
    return parsedContents

def getEotInfo(cssFile):
    return getInfo(cssFile, "@font-face", [], "eot")

def getSvgInfo(cssFile):
    return getInfo(cssFile, "@font-face", ["localNames", "fontFormat"], "svg")

def getTtfInfo(cssFile):
    return getInfo(cssFile, "@font-face", ["localNames", "fontFormat"], "ttf")

def getWoff2Info(cssFile):
    return getInfo(cssFile, "/*", ["unicodeRange", "localNames", "fontFormat"], "woff2")

def getWoffInfo(cssFile):
    return getInfo(cssFile, "@font-face", ["localNames", "fontFormat"], "woff")

print("Parsing information from the css files")
allData = []
for cssFile in cssFiles:
    fnName = "get" + cssFile["fontType"].capitalize() + "Info"
    allData.append(locals()[fnName](cssFile["name"]))
    os.remove(cssFile["name"])

def grabFonts(fontData):
    for index, data in enumerate(fontData):
        fileName = fontDirectory + "/" + data["name"] + "."
        if data["unicodeRangeName"] is not None:
            fileName += data["unicodeRangeName"] + "."
        fileName += data["ext"]
        fontData[index]["fileName"] = fileName
        urllib.request.urlretrieve(data["url"], fileName)

print("Downloading fonts from Google")
for data in allData:
    grabFonts(data)

print("Preparing data to build new css file")
sortedData = {}
for fontData in allData:
    for data in fontData:
        fontWeight = data["fontWeight"]
        fontStyle = data["fontStyle"]
        key = fontWeight + fontStyle
        if data["unicodeRangeName"] is not None:
            key += data["unicodeRangeName"]
        if key not in sortedData:
            sortedData[key] = {
                "weight": fontWeight,
                "style": fontStyle,
                "fonts": []
            }
            if data["unicodeRangeName"] is not None:
                sortedData[key]["unicodeRange"] = data["unicodeRange"]
                sortedData[key]["unicodeRangeName"] = data["unicodeRangeName"]
        sortedData[key]["fonts"].append(data)

# Grab Local Names
for key, value in sortedData.items():
    localNames = []
    for index, data in enumerate(value["fonts"]):
        localNames += data["localNames"]
    localNames = list(set(localNames))
    value["localNames"] = localNames

print("Building new css file")
for key, value in sortedData.items():
    content = ""
    if "unicodeRangeName" in value:
        content += "/* " + value["unicodeRangeName"] + " */\n"
    content += "@font-face {\n"
    content += "\tfont-family: '" + fontFamily + "';\n"
    content += "\tfont-style: " + value["style"] + ";\n"
    content += "\tfont-weight: " + value["weight"] + ";\n"
    content += "\tsrc: "
    if "unicodeRangeName" in value:
        # Woff2 format
        for localName in value["localNames"]:
            content += "local('" + localName + "'), "
        for data in value["fonts"]:
            content += "url('/" + data["fileName"] + "') format('" + data["fontFormat"] + "');\n"
        content += "\tunicode-range: " + value["unicodeRange"] + ";\n"
    else:
        for data in value["fonts"]:
            if data["ext"] == "eot":
                content += "url('/" + data["fileName"] + "');\n"
                content += "\tsrc: url('/" + data["fileName"] + "?#iefix') format('embedded-opentype'),\n"
        for localName in value["localNames"]:
            content += "\tlocal('" + localName + "'),\n"
        for data in value["fonts"]:
            if data["ext"] == "woff":
                content += "\turl('/" + data["fileName"] + "') format('" + data["fontFormat"] + "'),\n"
        for data in value["fonts"]:
            if data["ext"] == "ttf":
                content += "\turl('/" + data["fileName"] + "') format('" + data["fontFormat"] + "'),\n"
        for data in value["fonts"]:
            if data["ext"] == "svg":
                content += "\turl('/" + data["fileName"] + "#" + fontFamily + "') format('" + data["fontFormat"] + "'),\n"
        content = content[:-2] + ";\n"
    content += "}"
    sortedData[key]["content"] = content

allContent = []
for key, value in sortedData.items():
    allContent.append(value["content"])
allContent = "\n".join(allContent)

print("Saving new css file")
with open(cssDirectory + "/" + fontFamily + ".css", "w") as text_file:
    text_file.write(allContent)
print("Completed. Enjoy the fonts :)")
