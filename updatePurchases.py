import datetime
import json
import MySQLdb as my

import ebaysdk
from ebaysdk.utils import getNodeText
from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading

def run():

    try:
        api = Trading(debug=False, config_file="../sensitive_files/devsdevsdevs.yaml",
                warnings=True, timeout=20, siteid="0")

        api.execute("GetMyeBayBuying", {
            'WonList': {'DurationInDays':'1'}
            });

        if (api.response.dict()['WonList']['PaginationResult']['TotalNumberOfEntries'] == '0'):
            return 

        # if just 1 item returned, put it into a list so the for loop works correctly
        if (api.response.dict()['WonList']['PaginationResult']['TotalNumberOfEntries'] == '1'):
            api.response.dict()['WonList']["OrderTransactionArray"]["OrderTransaction"] = [api.response.dict()['WonList']["OrderTransactionArray"]["OrderTransaction"]]

        wonList = api.response.dict()['WonList']

        api.execute("GetOrders", {
            'NumberOfDays': '10',
            'OrderRole': 'Buyer'});

        orderList = api.response.dict()['OrderArray']['Order']
        for item in wonList["OrderTransactionArray"]["OrderTransaction"]:
            insertRecord(item)

    except ConnectionError as e:
        print(e)

    updateRowsWithGetOrders()

# Parse JSON string and cast each variable to corresponding database variable type 
def insertRecord(item):
    # TODO if existing entry in table with itemId, remove from table or specify cancelled 
    # TODO replace null with None, modify android app accordingly
    if (item['Transaction']['BuyerPaidStatus'] != 'PaidWithPayPal'): # refunded or cancelled
        return None

    totalPrice = (item['Transaction']['TotalPrice']['value'])
    currencyId = item['Transaction']['TotalPrice']['_currencyID']
    quantity = (item['Transaction']['QuantityPurchased'])
    itemId = (item['Transaction']['Item']['ItemID'])
    transactionId = item['Transaction']['TransactionID']
    startTime = item['Transaction']['Item']['ListingDetails']['StartTime']
    endTime = item['Transaction']['PaidTime'] 

    startTime = startTime.replace(".000Z", "")
    startTime = startTime.replace("T", " ")
    endTime = endTime.replace(".000Z", "")
    endTime = endTime.replace("T", " ")

    title = item['Transaction']['Item']['Title']
    listingType = item['Transaction']['Item']['ListingType']
    title = item['Transaction']['Item']['Title']
    url = item['Transaction']['Item']['ListingDetails']['ViewItemURL'] 
    if ('PictureDetails' in item['Transaction']['Item'].keys()):
        pictureUrl = item['Transaction']['Item']['PictureDetails']['GalleryURL'] 
    else:
        pictureUrl = "null"
    sellerId= item['Transaction']['Item']['Seller']['UserID']
    sellerEmail = item['Transaction']['Item']['Seller']['Email']
    listPrice = (item['Transaction']['Item']['SellingStatus']['CurrentPrice']['value'])
    if (item['Transaction']['Item']['ShippingDetails']['ShippingServiceOptions'] ): # if not null 
        shipCost = (item['Transaction']['Item']['ShippingDetails']['ShippingServiceOptions']['ShippingServiceCost']['value'])
    # I think the following happens when multiple shipping options and first one is free
    else:
        shipCost = '0.0' 
    if (item['Transaction']['Item']['BiddingDetails']): # if not null
        quantityBid= (item['Transaction']['Item']['BiddingDetails']['QuantityBid'])
    else:
        quantityBid = '0' 
    
    # parse orderList
    #orderIDArray = [item['TransactionArray']['Transaction'][0]['Item']['ItemID'] for item in orderList]
    #if (itemId not in orderIDArray):
    #    print "ERROR, itemID not in GetOrders reponse"
    #    return

    #orderItem = orderList[orderIDArray.index(itemId)]

    # TODO obfuscate passwords to make committing to git safer
    db = my.connect(host='localhost',user='USER',passwd='PASSWORD',db='eBay')
    cursor = db.cursor()
    #TODO convert title to utf to get rid of emoji
    sql = "INSERT INTO TABLENAME(itemID, transactionID, title, totalPricePaid, shipPrice, listPrice, currencyID, quantity, listingType, quantityBid, url, pictureURL, startTime, endTime, sellerID, sellerEmail, totalFeedbackN, positiveFeedbackN, trackingNumber, delivered, zipCode, hasReef, cond) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, %s,%s,%s,%s)" 
    try:
        cursor.execute(sql, (itemId, transactionId, title, totalPrice, shipCost, listPrice, currencyId,quantity,listingType,quantityBid,url, 
            pictureUrl, startTime,endTime, sellerId, sellerEmail, '0', '1', "null", 0, 'null', 0, '?'))
        db.commit()
    except Exception as e:
        db.rollback()
        print "SQL error for %s" % itemId 
        print e

    cursor.close()
    db.close()

def updateRowsWithGetOrders(): # for tracking, condition, shippedDate
    try:
        api = Trading(debug=False, config_file="../sensitive_files/devsdevsdevs.yaml",
                warnings=True, timeout=20, siteid="0")

        api.execute("GetOrders", {
            'NumberOfDays': '1',
            'OrderRole': 'Buyer'});

        if (api.response.dict()['ReturnedOrderCountActual'] == '0'):
            return

        orderList = api.response.dict()['OrderArray']['Order']
        for item in orderList:
            getOrdersHelper(item)

    except ConnectionError as e:
        print(e)

def getOrdersHelper(item):

    itemId = item['TransactionArray']['Transaction'][0]['Item']['ItemID']

    if ('ConditionDisplayName' in item['TransactionArray']['Transaction'][0]['Item']): 
        condition = item['TransactionArray']['Transaction'][0]['Item']['ConditionDisplayName']
        condition = condition[:8] #TODO make cond bigger field by 1 character to 9 "New Other" is biggest 
    else:
        condition = "?" # condition cannot be null in table 

    if ('ShipmentTrackingDetails' in item['TransactionArray']['Transaction'][0]['ShippingDetails'].keys()):
        if (type(item['TransactionArray']['Transaction'][0]['ShippingDetails']['ShipmentTrackingDetails']) is list):
            trackingNumber = item['TransactionArray']['Transaction'][0]['ShippingDetails']['ShipmentTrackingDetails'][0]['ShipmentTrackingNumber']
        else:
            trackingNumber = item['TransactionArray']['Transaction'][0]['ShippingDetails']['ShipmentTrackingDetails']['ShipmentTrackingNumber']
    else:
        trackingNumber = None

    if ('ShippedTime' in item.keys()):
        shippedTime = item['ShippedTime']
        shippedTime = shippedTime.replace(".000Z", "")
        shippedTime = shippedTime.replace("T", " ")
    else:
        shippedTime = None

    db = my.connect(host='localhost',user='USER',passwd='PASSWORD',db='eBay')
    cursor = db.cursor()
    sql = "UPDATE TABLENAME SET trackingNumber = %s, cond = %s, shippedTime = %s where itemID = %s"
    try:
        cursor.execute(sql, (trackingNumber, condition, shippedTime, itemId))
        db.commit()
    except Exception as e:
        db.rollback()
        print "SQL error for %s" % itemId 
        print e

    cursor.close()
    db.close()

run();


