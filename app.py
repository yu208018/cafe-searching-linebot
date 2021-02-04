# coding:utf-8
from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, MessageTemplateAction, TemplateSendMessage,ImageSendMessage,
    ButtonsTemplate, CarouselTemplate, CarouselColumn, PostbackTemplateAction, URITemplateAction, PostbackEvent, LocationSendMessage
)
import googlemaps
from cloudant.client import Cloudant
from cloudant.error import CloudantException
from cloudant.result import Result, ResultByKey
from cloudant.design_document import DesignDocument
from cloudant.document import Document
from requests.adapters import HTTPAdapter
from cloudant.adapters import Replay429Adapter
import sys
import requests
import random

app = Flask(__name__)

CHANNEL_SECRET = '{LINE_CHANNEL_SECRET}'
ACCESS_TOKEN = '{LINE_ACCESS_TOKEN}'

line_bot_api = LineBotApi(ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

global placeId
placeId = ''


def drawrandom():
    drawcoffee = str(random.randint(1, 20))
    my_coffee = coffeedb[drawcoffee]
    return my_coffee


def drawrrecommend(species):
    if(species == "meal"):
        drawpicture = str(random.randint(1, 3))
        my_recommend = picturedb[drawpicture]
        return my_recommend
    elif(species == "view"):
        drawpicture = str(random.randint(4, 6))
        my_recommend = picturedb[drawpicture]
        return my_recommend
    else:
        drawpicture = str(random.randint(7, 13))
        my_recommend = picturedb[drawpicture]
        return my_recommend


def find_coffeeshop(search_key):
    gmaps = googlemaps.Client(key="YOUR_Googlemaps_KEY")
    location = (25.013374954867782, 121.5405596723314)
    radius = 5000
    lists = []
    result = gmaps.places_nearby(
        location, radius, keyword=search_key+"咖啡廳", language="zh-TW")['results']
    size = 0
    if(len(result) > 5):
        size = 5
    elif(5 >= len(result) > 0):
        size = len(result)
    else:
        return lists

    for i in range(0, size):
        detail = gmaps.place(place_id=result[i]['place_id'])['result']
        img = (result[i]['photos'][0]
               ['html_attributions'][0]).split("\"", 2)[1]
        lists.append(
            CarouselColumn(
                thumbnail_image_url="https://i.imgur.com/LfJoabm.jpg",
                title=result[i]['name'],
                text=' ',
                actions=[
                    PostbackTemplateAction(
                        label='推薦菜單',
                        data=result[i]['place_id']
                    ),
                    URITemplateAction(
                        label='地圖',
                        uri=detail['url']
                    )
                ]
            )
        )
    return lists


# kkbox api - obtain access token
def get_access_token():
    url = "https://account.kkbox.com/oauth2/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "account.kkbox.com"
    }
    # parameter
    data = {
        "grant_type": "client_credentials",
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET"
    }
    access_token = requests.post(url, headers=headers, data=data)
    return access_token.json()["access_token"]


# get recommended tracks randomly
def get_tracks(chart_id):
    access_token = get_access_token()
    url = "https://api.kkbox.com/v1.1/charts/" + chart_id + "/tracks"
    headers = {
        "accept": "application/json",
        "authorization": "Bearer " + access_token
    }
    params = {
        "territory": "TW"
    }
    response = requests.get(url, headers=headers, params=params)

    # json parse
    result = response.json()["data"]
    trackList = {}  # storing name & url
    musicRandom = []  # for trackList shuffle key
    for item in result:
        trackList[item["name"]] = item["url"]
        musicRandom.append(item["name"])
        print([item["name"], item["url"]])
    random.shuffle(musicRandom)
    musicIndex = musicRandom[0]
    msg=musicIndex+"\n"+trackList.get(musicIndex)
    return msg


@ app.route("/")
def root():
    return 'cannot GET/'


@ app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


# event of crawler button
@ handler.add(PostbackEvent)
def postbackEvent_message(event):
    line_bot_api.reply_message(
        event.reply_token, TextSendMessage(text="Sorry! 此功能尚未開放..."))


flag_coffee = ""
flag_track = False

# text of the selected function on rich menu
@ handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global flag_coffee
    global flag_track
    musicSeries = {}
    musicSeriesID = []

    if (event.message.text == "尋找咖啡廳"):
        flag_coffee = "search"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入欲搜尋的關鍵字"))
    elif (flag_coffee == "search"):
        flag_coffee = ""
        if(len(find_coffeeshop(event.message.text)) == 0):
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="Sorry!找不到你想要的咖啡廳><\n要不要換個關鍵字試試?"))
        else:
            Carousel_template = TemplateSendMessage(
                alt_text='目錄 template',
                template=CarouselTemplate(
                    find_coffeeshop(event.message.text)
                )
            )
            line_bot_api.reply_message(event.reply_token, Carousel_template)
    elif (event.message.text == "音樂推薦"):
        flag_track = True
        musicSeries = {"隨機歌曲": "0", "華語歌曲": "1", "西洋樂": "2", "韓語歌曲": "3", "日語歌曲": "4", "電子": "5", "嘻哈": "6",
                "R＆B": "7", "爵士": "8", "搖滾樂": "9", "獨立/另類歌曲": "10", "靈魂樂": "11", "鄉村樂": "12", "雷鬼樂": "13"}
        musicSeriesID = ["LZPhK2EyYzN15dU-PT", "WnL70wKpBhWItUXO6V", "5aJI4jxgnNDC5-PtBE", "OmZZqDSpy7BGeNp7Sl", "Os00AlGuw-NvJDa6Ov", "T-2adICVU3QJSMkIRL", "GmJQUC2hoIXuLG09gB",
                         "PYwaFPxIpiAubREH9R", "0rl4x_jCzZ7WEq-Q14", "9ZU-9bghQ1a9ykbDWp", "OmnNqDSpy7BGe6U6wm", "1Xt9wLl1ZgBNbh3sqy", "Gk7UFgiC1bzp1hJ9V-", "-kGtNC5wNZlr5KaqvX"]
        msg = "只要輸入以下列表中感興趣的音樂類型，找咖將為您推薦一首適合您的音樂!\n\n"
        for key in musicSeries.keys():
            msg += " 🎶 "+key+"\n"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
    elif(flag_track):
        flag_track = False
        chart_id = musicSeriesID[int(musicSeries[event.message.text])]
        msg=get_tracks(chart_id)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        # print(event.message.text)
        # if str(event.message.text) in musicSeries.keys():
        #     chart_id = musicSeriesID[int(musicSeries[event.message.text])]
        #     msg=get_tracks(chart_id)
        #     line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        # else:
        #     line_bot_api.reply_message(
        #         event.reply_token, TextSendMessage(text="Oops! 看起來好像輸錯了..."))
    elif (event.message.text == "食譜"):
        coffee = drawrandom()
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text=coffee["name"]+"\n"
                                               + coffee["ingredients"]+"\n"
                                               + coffee["step"]))
    elif (event.message.text == "美照教學"):
        teach = drawrrecommend(random.choice(['meal', 'view', 'person']))
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text=teach["tipname"]+"\n"
                                               + teach["description"]+"\n"
                                               + teach['picurl']))
        line_bot_api.reply_message(
            event.reply_token, ImageSendMessage(original_content_url=teach['picurl'], 
                                                preview_image_url=teach['picurl']))
    else:
        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text="可以透過下方圖文選單選擇欲操作功能唷!!"))


global picturedb,coffeedb

if __name__ == "__main__":
    httpAdapter = HTTPAdapter(pool_connections=15, pool_maxsize=100)
    ACCOUNT_NAME = "2fcdf5e3-efe2-4275-a37e-b9e4e2fcea20-bluemix"
    API_KEY = "z1_XduHEdf8rm8_TYnwql_TgErsMEcY0J2RlQbiBW1Xg"

    client = Cloudant.iam(ACCOUNT_NAME, API_KEY, connect=True,
                          adapter=Replay429Adapter(retries=10, initialBackoff=0.01))
    client.connect()

    databaseName = "recipedata"
    coffeedb = client.create_database(databaseName)
    picdatabaseName = "picturedata"
    picturedb = client.create_database(picdatabaseName)

    if coffeedb.exists():
        print("'{0} successfully created.\n".format(databaseName))
    if picturedb.exists():
        print("'{0} successfully created.\n".format(picdatabaseName))
    
    app.run()
