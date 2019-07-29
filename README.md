# eBay
## Getting Started 
You'll need to install the eBay Python sdk from
[timotheus](https://github.com/timotheus/ebaysdk-python) which is easy enough on
unix systems.  Additionally, you need to register with the [eBay Developer
Program](https://go.developer.ebay.com/) to receive your keys (add these to your
eBay.yaml file)  

Additionally, for this set-up to work, you'll need:  
- an empty txt file called ignored_listings.txt
- parent folder called sensitive_files that contains 
    - ebay.yaml (see Timoetheus)
    - email_code.py 

To run a script at a frequent interval, check out cron on unix systems (just
remember, eBay limits you to 2,500 finding calls a day!). 


## Objective 
Pricing items on eBay at a reasonable price is fairly easy. Just browse recently
sold items that match your item or use eBay's trending price tool. However,
often sellers sell their items drastically lower than market prices, giving
resellers arbitrage opportunities. A script like this can be used to frequently
query for a particular item below a particular price point.  

eBay has a saved-search feature that allows "real-time" notifications, but it
only alerts once daily (way too slow for most items). Using the eBay SDK gives
you much faster notifications and allows you to save and track listings. The
latter is especially useful for looking for seasonal variations in price and
volume (another arbitrage opportunity, albeit with more risk depending on the
holding time) and for building new models that use NLP and/or image recognition
to better classify products.

## Visualization
https://public.tableau.com/profile/lucas.aleck#!/vizhome/MP2_15625587782040/Dashboard?publish=yes
