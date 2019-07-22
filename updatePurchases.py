import datetime
import sys
import mysql.connector

from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading

# TODO fix relative path issue (have to call it from directory for it to work)
sys.path.append("../sensitive_files")
from email_code import SQL_PASSWORD

class Transaction:
    def __init__(self, api, order):
        self.api = api
        # Get Order level information on this transaction
        self.itemID = order['TransactionArray']['Transaction'][0]['Item']['ItemID']
        self.transactionID = order['TransactionArray']['Transaction'][0]['TransactionID']
        if (self.transactionID == '0'):
            self.transactionID = self.itemID # Transaction ID not working for auctions for whatever reason
            # Since an auction will always be for 1 transaction. This isn't an issue as long as we have a unique ID
        self.totalTaxesPaid = order['TransactionArray']['Transaction'][0]['Taxes']['TotalTaxAmount']['value']
        self.totalPricePaid = order['Total']['value']
        self.quantity = order['TransactionArray']['Transaction'][0]['QuantityPurchased']
        self.address1 = order['ShippingAddress']['Street1']
        if 'ActualShippingCost' in order['TransactionArray']['Transaction'][0].keys():
            self.shipPrice = order['TransactionArray']['Transaction'][0]['ActualShippingCost']['value']
        else:
            print ("*** ERROR *** \nSHIP PRICE NOT FOUND for itemID %s" % self.itemID)
            self.shipPrice = 0.01
        self.listPrice = order['Subtotal']['value']

        if order['OrderStatus'] == 'Cancelled':
            self.orderStatus = 'C'
        else:
            self.orderStatus = 'O'

        if 'ShipmentTrackingDetails' in order['TransactionArray']['Transaction'][0]['ShippingDetails'].keys():
            if type(order['TransactionArray']['Transaction'][0]['ShippingDetails']['ShipmentTrackingDetails']) is list:
                self.trackingNumber = order['TransactionArray']['Transaction'][0]['ShippingDetails']['ShipmentTrackingDetails'][0]['ShipmentTrackingNumber']
            else:
                self.trackingNumber = order['TransactionArray']['Transaction'][0]['ShippingDetails']['ShipmentTrackingDetails']['ShipmentTrackingNumber']
        else:
            self.trackingNumber = None

        if ('ShippedTime' in order.keys()):
            self.shippedTime = timeConvert(order['ShippedTime'])
        else:
            self.shippedTime = None

        self.getItemDetails();

    def getItemDetails(self):

        self.api.execute("GetItem", {
            'ItemID': self.itemID
        });

        item = self.api.response.dict()['Item']

        self.title = item['Title'].encode('utf-8')
        self.title = self.title.replace('\\xa0', ' ') # TODO learn about encoding later
        self.currencyID = item['Currency']
        self.categoryID = item['PrimaryCategory']['CategoryID']
        self.listingType = item['ListingType']
        self.quantityBid = item['SellingStatus']['BidCount']

        self.pictureURL1 = self.pictureURL2 = None
        if (('PictureDetails' in item.keys()) & ('PictureURL' in item['PictureDetails'].keys()) ):
            if (type(item['PictureDetails']['PictureURL']) == str):
                self.pictureURL1 = item['PictureDetails']['PictureURL']
            elif (len(item['PictureDetails']['PictureURL']) >= 2):
                self.pictureURL1 = item['PictureDetails']['PictureURL'][0]
                self.pictureURL2 = item['PictureDetails']['PictureURL'][1]

        self.startTime = timeConvert(item['ListingDetails']['StartTime'])
        self.endTime =  timeConvert(item['ListingDetails']['EndTime'])
        self.currentDtm = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if (self.currentDtm < self.endTime):
            endTime = self.currentDtm

        self.sellerID = item['Seller']['UserID']
        self.sellerEmail = item['Seller']['Email']
        self.totalFeedbackN = item['Seller']['FeedbackScore']
        self.positiveFeedbackPercent = item['Seller']['PositiveFeedbackPercent']

        if ('ConditionDisplayName' in item.keys()):
            self.conditionInfo = item['ConditionDisplayName']
        else:
            self.conditionInfo = None

        self.city = self.state = None
        if ('Location' in item.keys()):
            locationList = item['Location'].split(", ")
            if (len(locationList) == 2):
                self.city = locationList[0]
                self.state = locationList[1]

        if ('PostalCode' in item.keys()):
            self.postalCode = item['PostalCode']
        else:
            self.postalCode = None

    def getSqlInsertValues(self):
        return (self.itemID, self.transactionID, self.title, self.totalPricePaid, self.shipPrice, self.listPrice,
                self.currencyID, self.quantity, self.categoryID, self.listingType, self.quantityBid, self.pictureURL1,
                self.pictureURL2, self.startTime, self.endTime, self.shippedTime, None, self.sellerID, self.sellerEmail,
                self.totalFeedbackN, self.positiveFeedbackPercent, self.city, self.state, self.postalCode, self.trackingNumber,
                None, self.conditionInfo, self.orderStatus, self.totalTaxesPaid, self.address1, 0)

    def getSqlUpdateValues(self):
        return (self.trackingNumber, self.shippedTime, self.orderStatus, self.transactionID)

def timeConvert(time):
    time = time.replace(".000Z", "")
    return time.replace("T", " ")


# TODO break this into smaller functions
# Queries to see which transactions exist in table
# If not exists in table, create entry in table for that transaction
# Otherwise if exists in table, update that entry in table because some data may have changed
def insertAndUpdateRecords(transactions):
    data = {}
    dataToUpdate = []
    dataToInsert = []
    for t in transactions:
        data[t.transactionID] = t

    transactionIDs = ",".join(data.keys())
    sql = "Select transactionID from newPurchases where transactionID in (%s);" % transactionIDs

    try:
        cnx = mysql.connector.connect(user='root', password=SQL_PASSWORD, database='eBay', auth_plugin= 'mysql_native_password')
        cursor = cnx.cursor(buffered=True)
        cursor.execute(sql)
        cnx.commit()

        # Transactions already exist in table. Update these records, do not attempt to insert again
        for cursorTuple in cursor:
            transactionID = cursorTuple[0].decode('utf-8').encode("ascii", "ignore")
            dataToUpdate.append(data[transactionID].getSqlUpdateValues())
            del data[transactionID]

        for t in data.values():
            dataToInsert.append(t.getSqlInsertValues())

        cursor.close()
        cnx.close()

    except Exception as e:
        print "SQL error when trying to retrieve transactions already in table"
        print e

    sql = "INSERT INTO newPurchases(itemID, transactionID, title, totalPricePaid, shipPrice, listPrice, currencyID, " \
          "quantity, categoryID, listingType, quantityBid, pictureURL1, pictureURL2, startTime, endTime, shippedTime, " \
          "receivedDate, sellerID, sellerEmail, totalFeedbackN, positiveFeedbackPercent, city, state, postalCode, " \
          "trackingNumber, model, conditionInfo, orderStatus, totalTaxesPaid, address1, synced) " \
          "VALUES " \
          "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, %s)"

    try:
        cnx = mysql.connector.connect(user='root', password=SQL_PASSWORD, database='eBay', auth_plugin= 'mysql_native_password')
        cursor = cnx.cursor(buffered=True)
        cursor.executemany(sql, dataToInsert)
        cnx.commit()

    except Exception as e:
        print "SQL error for in updatePurchases.py"
        print e

    updateTransactions(dataToUpdate)

# Updates item entry based with dynamic information that may change a few days after purchase
def updateTransactions(dataToUpdate):

    # TODO maybe include another dirty flag to tell sheets to update an existing entry
    try:
        cnx = mysql.connector.connect(user='root',password=SQL_PASSWORD, database='eBay',auth_plugin='mysql_native_password')
        cursor = cnx.cursor(buffered=True)
        sql = "UPDATE newPurchases SET trackingNumber = %s, shippedTime = %s, orderStatus = %s where transactionID = %s"
        cursor.executemany(sql, dataToUpdate)
        cnx.commit()
        cursor.close()
        cnx.close()

    except Exception as e:
        print "SQL error when updating transactions"
        print e

def start():

    try:
        api = Trading(debug=False, config_file="../sensitive_files/buying.yaml",
                      warnings=True, timeout=20, siteid="0")

    except ConnectionError as e:
        print(e)

    api.execute("GetOrders", {
        'NumberOfDays': '3', 
        'OrderRole': 'Buyer'});

    if (api.response.dict()['ReturnedOrderCountActual'] == '0'):
        return

    transactions = []
    for order in api.response.dict()['OrderArray']['Order']:
        transactions.append(Transaction(api, order))

    insertAndUpdateRecords(transactions)


start()
