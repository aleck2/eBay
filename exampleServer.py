from flask import Flask, url_for, request, Response
import json
import MySQLdb as my
app = Flask(__name__)

@app.route('/getUndelivered', methods = ['GET'])
def getUndelivered():
    db = my.connect(host='localhost',user='USER',passwd='PASSWORD',db='eBay')
    cursor = db.cursor()
    json_data = []

    sql = """SELECT itemID, LEFT(endTime,10) as endTime, trackingNumber, url, pictureURL, title, zipCode, sellerID, sellerEmail, totalPricePaid, quantity from TABLENAME WHERE delivered=0 ORDER BY endTime ASC """
    try:
        cursor.execute(sql)
        row_headers=[x[0] for x in cursor.description] 
        data = cursor.fetchall()
        for row in data : 
            json_data.append(dict(zip(row_headers, row)))

    except Exception as e:
        print e

    cursor.close()
    db.close()
    return json.dumps(json_data)


@app.route('/updateDeliveries', methods = ['POST'])
def updateDeliveries():
    
    if request.headers['Content-Type'] == 'application/json':
        db = my.connect(host='localhost',user='USER',passwd='PASSWORD',db='eBay')
        cursor = db.cursor()

        try:
            sql = """UPDATE TABLENAME SET quantity=%s, delivered=%s where itemID = '%s'""" % (request.json['quantity'], request.json['delivered'], request.json['itemID'])
            cursor.execute(sql)
            db.commit()
            result = "success"
        except Exception as e:
            print e
            db.rollback()
            result = "failure"

        cursor.close()
        db.close()
        return result

if __name__ == '__main__':
    app.run(host= '0.0.0.0') # accessible from server's ip address

