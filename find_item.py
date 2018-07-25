#!/usr/bin/python
#Look into GetSingleItem
from time import gmtime, strftime, strptime
import datetime
import smtplib
from email.mime.text import MIMEText
from sys import argv    
import json
import ebaysdk
from ebaysdk.finding import Connection as finding

def execute(api, itemId, findingCall):
        api.execute(findingCall, {
            'keywords' : itemId,  
            'buyerPostalCode' : 60423,
            'sortOrder' : 'EndTimeSoonest'
        })

def findQuery(myargs): 
    if '-id' in myargs:
        itemId = myargs['-id']
    else:
        itemId = input("Input ItemID, no quotes: ")

    api = finding(siteid='EBAY-US', config_file="../sensitive_files/falcons070.yaml")
    execute(api, itemId, 'findItemsAdvanced')

    dictstr = api.response.dict()

    if dictstr['searchResult']['_count'] == '0':
        execute(api, itemId, 'findCompletedItems')
    else:          
        for item in dictstr['searchResult']['item']:
            print json.dumps(item, indent=4)

def getopts(argv):
    opts = {}  
    while argv:
        if argv[0][0] == '-':  
            opts[argv[0]] = argv[1]  
        argv = argv[1:]  

    return opts

def start():
    myargs = getopts(argv)
    findQuery(myargs)

start()
