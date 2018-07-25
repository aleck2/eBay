# find_widget.py
#
# Executes custom eBay search for a particular widget and alerts via Android FCM when found
# Scheduled via Crontab to execute routinely in order to claim good deals before
#   the competition
#
# TODO
#   * Use basic NLP to identify variations of widget model and apply different maxPrice
#       constraint depending on the estimated widget model
#   * Record all "good deals" in a table and use purchases table to assess how many
#       deals are not purchased by me.
#   * If bestOffer enabled and price lower, alert or send automated offer
#
#

from time import gmtime, strftime, strptime
from pyfcm import FCMNotification
import datetime
import smtplib
from email.mime.text import MIMEText
import ebaysdk
from ebaysdk.trading import Connection as Trading
from ebaysdk.finding import Connection as finding
from ebaysdk.exception import ConnectionError

## Look in subdirectory sensitive_files for email_code
## This only works when running script for local directory, TODO fix when running from elsewhere 
## sys.path.insert(0, '/path/to/application/app/folder') // put path to directory here
import sys;
sys.path.append("../sensitive_files")
from email_code import sendEmail, widget, api_key, registration_id, notification_extra_kwargs, PRICE

IGNORED_LISTINGS = []
NEW_IGNORED_LISTINGS = []

push_service = FCMNotification(api_key)

def getItem(itemId):
    try:
        api = Trading(debug=False, config_file="../sensitive_files/devsdevsdevs.yaml",
                warnings=True, timeout=20, siteid="0")

        api.execute("GetItem", {
            'ItemID': '%s' % itemId 
            });

        quantity = api.response.dict()['Item']['Quantity']

    except ConnectionError as e:
        quantity = -1
        print(e)

    return quantity

def findQuery(): 
    api = finding(siteid='EBAY-US', config_file="../sensitive_files/ebay.yaml")

    api.execute('findItemsAdvanced', {
        'keywords': widget,
        'itemFilter': [
            {'name' : 'ListingType', 'value' : ['AuctionWithBIN', 'FixedPrice', 'StoreInventory']},
            {'name': 'MinPrice', 'value': '0', 'paramName': 'Currency', 'paramValue': 'USD'},
            {'name': 'MaxPrice', 'value': str(PRICE), 'paramName': 'Currency', 'paramValue': 'USD'},
            {'name': 'LocatedIn', 'value': 'US'}
        ],
        'buyerPostalCode' : 60423,
        'sortOrder' : 'PricePlusShippingLowest'
    })

    dictstr = api.response.dict()
    itemLinks = []

    if dictstr['searchResult']['_count'] == '0':
        print 'EMPTY \n\n'
    else:               
        # TODO include bestOffer boolean 
        for item in dictstr['searchResult']['item']:
            # want to avoid accessory case items that often have "skin" in the listing title without using eBay's boolean search
            if ("skin" not in item["title"] and item['itemId'] not in IGNORED_LISTINGS):
                # shippingServiceCost can throw error when seller does calculated shipping but does not define a shipping service (mostly caused by those pesky Canadians...) 
                try:
                    shipping = item['shippingInfo']['shippingServiceCost']['value']
                    if (item['listingInfo']['listingType'] == 'AuctionWithBIN'):
                        price = item['listingInfo']['convertedBuyItNowPrice']['value'] 
                    else:
                        price = float(item['sellingStatus']['convertedCurrentPrice']['value'])

                    total = float(shipping) + float(price)
                    if (total <= PRICE):
                        listingType = item['listingInfo']['listingType']
                        quantity = getItem(item['itemId'])
                        # Convert to utf-8 to stop emjoi text from crashing program
                        data_message = {
                                "url" : item['viewItemURL'],
                                "price" : str(total),
                                "title" : item['title'].encode('utf-8')
                                }
                        result = push_service.notify_single_device(registration_id=registration_id, message_body="Item Found", data_message=data_message, extra_notification_kwargs=notification_extra_kwargs)
                        print result
                        itemLinks.append("$" + str(total) + " " + item['title'].encode('utf-8') + ' ' + '\n' + 
                                listingType + '\n' + 'Quantity: ' + quantity + '\n' + item['viewItemURL'] + '\n' )
                        NEW_IGNORED_LISTINGS.append(item['itemId'])

                except Exception, e:
                    print ("EXCEPTION: " + str(e) + "\n")


# Only alert once on a given item, so store ItemId in ignored_listings
# Periodically, using crontab, clear this txt file to avoid it becoming huge
def readFile():
    myFile = open("ignored_listings.txt", "r")
    for line in myFile:  
        IGNORED_LISTINGS.append(line.rstrip('\n'))

    myFile.close()

def writeFile():
    myFile = open("ignored_listings.txt", "a")
    for x in NEW_IGNORED_LISTINGS:
        myFile.write(x + "\n")

def start():

    now = datetime.datetime.now() # uses local time
    sleepTime = now.replace(hour=1, minute=15, second=0, microsecond=0)
    wakeTime = now.replace(hour=6, minute=25, second=0, microsecond=0)
    # Don't waste API calls when I shouldn't be awake
    if (sleepTime < now < wakeTime):
        return

    readFile()
    findQuery()
    writeFile()

start()

