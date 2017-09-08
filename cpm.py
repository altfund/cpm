# The CPM needs to support Kraken, Bittrex and Bitfinex. The goal is to buy Multiple Coins with one script automatically. All coins supported by those 3 exchanges must be supported and may be setup in a config area of this script.
## Please see the config file in order to set the settings

# Inside of the configs you define how much money you plan to invest per interval. Let's assume 500 EUR per week.

#Invest = 500
#BaseCurrency = EUR
#Interval = weekly
#Steps = 2

#This configuration means that we invest on weekly bases 500 EUR in 2 steps so per investment round it will be 250 EUR. 

#In a next step I define the percentages per currency. NOTE - I simplify here, it must be way more coins.

#Bitcoin = 40%
#IOTA = 30%
#PAY = 10%
#ETH = 10%
#GAM = 10%
#TransferCurrency = ETH 

#There is one last setting.
#Rebalance = true / false
#If Rebalance is false the script buys always the percentage of the investment budget. If rebalance is true than the script buys in a manner that the percentage inside of the configuration is the percentage of the overall value in base currency. The script may not do any sell orders in order to perform the rebalancing. Only the buy volume may be altered. 

import bitfinex
from bittrex.bittrex import Bittrex
import krakenex

import copy
import configparser
config = configparser.ConfigParser()
config.read('config')


#Now the script buys first on Kraken from the 250 EUR (remember 500 EUR in 2 steps) whatever can be bought on Kraken. For this example it is 40% or 250 EUR in Bitcoin and 10% of 250 EUR in Etherium.
# The other 50% must be transferred to the other two exchanges. In the given example 20% (PAY & GAM) to Bittrex and 30% to Bitfinex.
# In case one coin is available in two exchanges choose where to buy cheaper.
## ^ Any price discrepancies among exchanges will not be actionable by the time the transfer has gone through so I have implemented a strict prioritization: Kraken, Bitfinex, Bittrex (also order of most-->least trusted)

exchanges = ["KRAKEN","BITFINEX","BITTREX"]
op = dict(config["currencies"])
op = {x.upper():float(op[x]) for x in op}
optimal_portfolio_percents = {x.upper():op[x]/float(sum(op.values())) for x in op}
init_portfolio = {x:{"optimal_percent":optimal_portfolio_percents[x], "optimal_balance":None, "actual_balance":0, "actual_percent":None, "fx_rate":None} for x in optimal_portfolio_percents}
portfolio = copy.deepcopy(init_portfolio)

kraken_instance = krakenex.api.API(key=config["KRAKEN"]["key"], secret=config["KRAKEN"]["secret"])
kraken_balances = dict(kraken_instance.query_private("Balance")["result"])

bittrex_instance = Bittrex(api_key=config["BITTREX"]["key"], api_secret=config["BITTREX"]["secret"])
bittrex_raw_balances = bittrex_instance.get_balances()['result']
bittrex_balances = {x['Currency']:x['Available'] for x in bittrex_raw_balances}

bitfinex_public_instance = bitfinex.Client()
bitfinex_instance = bitfinex.TradeClient(key=config["BITFINEX"]["key"], secret=config["BITFINEX"]["secret"])
bitfinex_raw_balances = bitfinex_instance.balances()
bitfinex_balances = {x['currency'].upper():x['available'] for x in bitfinex_raw_balances if x['type']=='exchange'}

bittrex_raw_currencies = bittrex_instance.get_currencies()['result']
bittrex_currencies = [x['Currency'] for x in bittrex_raw_currencies]
bittrex_raw_pairs = bittrex_instance.get_markets()['result']
bittrex_pairs = [x['MarketName'] for x in bittrex_raw_pairs]

kraken_raw_currencies = list(kraken_instance.query_public("Assets")["result"].keys())
kraken_currencies = [x[-3:] if x[0] in ['Z','X'] else x for x in kraken_raw_currencies]
kraken_currencies = ["BTC" if x=="XBT" else x for x in kraken_currencies]
kraken_pairs = kraken_instance.query_public("AssetPairs")["result"]

bitfinex_pairs = [x.upper() for x in bitfinex_public_instance.symbols()]
bitfinex_raw_currencies = [[x[:-3],x[-3:]] for x in bitfinex_pairs]
bitfinex_currencies = set(x.upper() for l in bitfinex_raw_currencies for x in l)

base_currency = config['settings']['base_currency']
transfer_currency = config['settings']['transfer_currency']
base_currency_for_kraken = kraken_raw_currencies[kraken_currencies.index(base_currency)]
rebalance = bool(config["settings"]["rebalance"])
test = bool(config["settings"]["test"])

if base_currency=="BTC":
    base_to_btc_rate=1
elif "XXBT"+base_currency_for_kraken in list(kraken_pairs.keys()):
    pairname = "XXBT"+base_currency_for_kraken
    ticker = kraken_instance.query_public("Ticker", req={"pair":pairname})["result"]
    base_to_btc_rate = (float(ticker[pairname]['a'][0])+float(ticker[pairname]['b'][0]))/2.0
elif base_currency_for_kraken+"XXBT" in list(kraken_pairs.keys()):
    pairname = base_currency_for_kraken+"XXBT"
    ticker = kraken_instance.query_public("Ticker", req={"pair":pairname})["result"]
    base_to_btc_rate = (float(ticker[pairname]['a'][0])+float(ticker[pairname]['b'][0]))/2.0
    base_to_btc_rate = 1.0/base_to_btc_rate
else:
    print("Base currency is not part of any BTC pair on investment exchange (KRAKEN)")

wallets = {x:copy.deepcopy(init_portfolio) for x in exchanges}

for currency in portfolio:
    if currency in kraken_currencies:
        print(currency)
        krakenized_currency = kraken_raw_currencies[kraken_currencies.index(currency)]
        if krakenized_currency in kraken_balances.keys():
            portfolio[currency]['actual_balance'] += float(kraken_balances[krakenized_currency])
            wallets["KRAKEN"][currency]['actual_balance'] = float(kraken_balances[krakenized_currency])
        ticker_price = None
        if "XXBT"+krakenized_currency in list(kraken_pairs.keys()):
            pairname = "XXBT"+krakenized_currency
            ticker = kraken_instance.query_public("Ticker", req={"pair":pairname})["result"]
            ticker_price = (float(ticker[pairname]['a'][0])+float(ticker[pairname]['b'][0]))/2.0
            ticker_price = 1.0/ticker_price
        elif krakenized_currency+"XXBT" in list(kraken_pairs.keys()):
            pairname = krakenized_currency+"XXBT"
            ticker = kraken_instance.query_public("Ticker", req={"pair":pairname})["result"]
            ticker_price = (float(ticker[pairname]['a'][0])+float(ticker[pairname]['b'][0]))/2.0
        elif currency=="BTC":
            ticker_price=1.0
        
        if ticker_price:
            wallets["KRAKEN"][currency]['fx_rate'] = ticker_price * base_to_btc_rate
            if portfolio[currency]["fx_rate"] is None:
                portfolio[currency]["fx_rate"] = ticker_price * base_to_btc_rate
        else:
            portfolio[currency]["fx_rate"] = 0
            
    elif currency in bitfinex_currencies:
        if currency in bitfinex_balances.keys():
            portfolio[currency]['actual_balance'] += float(bitfinex_balances[currency])
            wallets["BITFINEX"]["actual_balance"] = float(bitfinex_balances[currency])
        ticker_price = None
        if "BTC"+currency in bitfinex_pairs:
            pairname = "BTC"+currency
            ticker = bitfinex_public_instance.ticker(symbol=pairname)
            ticker_price = float(ticker['mid'])
            ticker_price = 1.0/ticker_price
        elif currency+"BTC" in bitfinex_pairs:
            pairname = currency+"BTC"
            ticker = bitfinex_public_instance.ticker(symbol=pairname)
            ticker_price = float(ticker['mid'])
        elif currency=="BTC":
            ticker_price=1.0
        
        if ticker_price:
            wallets["BITFINEX"][currency]['fx_rate'] = ticker_price * base_to_btc_rate
            if portfolio[currency]["fx_rate"] is None:
                portfolio[currency]["fx_rate"] = ticker_price * base_to_btc_rate
        else:
            portfolio[currency]["fx_rate"] = 0
            
    elif currency in bittrex_currencies:
        if currency in bittrex_balances.keys():
            portfolio[currency]['actual_balance'] += float(bittrex_balances[currency])
            wallets["BITTREX"]["actual_balance"] = float(bittrex_balances[currency])
        ticker_price = None
        if "BTC-"+currency in bittrex_pairs:
            pairname = "BTC-"+currency
            ticker = bittrex_instance.get_ticker(market=pairname)['result']
            ticker_price = (float(ticker['Bid']) + float(ticker['Ask']))/2.0
        elif currency+"-BTC" in bitfinex_pairs:
            pairname = currency+"-BTC"
            ticker = bittrex_instance.get_ticker(market=pairname)['result']
            ticker_price = (float(ticker['Bid']) + float(ticker['Ask']))/2.0
            ticker_price = 1.0/ticker_price
        elif currency=="BTC":
            ticker_price=1.0
        
        if ticker_price:
            wallets["BITTREX"][currency]['fx_rate'] = ticker_price * base_to_btc_rate
            if portfolio[currency]["fx_rate"] is None:
                portfolio[currency]["fx_rate"] = ticker_price * base_to_btc_rate
        else:
            portfolio[currency]["fx_rate"] = 0
    else:
        print(currency+" not listed")
        portfolio[currency]['actual_balance'] += 0
        if portfolio[currency]["fx_rate"] is None:
            ticker_price = None
            if ticker_price:
                portfolio[currency]["fx_rate"] = ticker_price * base_to_btc_rate
            else:
                portfolio[currency]["fx_rate"] = 0

portfolio_value = sum([portfolio[x]['fx_rate'] * portfolio[x]["actual_balance"] for x in portfolio])

max_txn_size = float(config['settings']['invest']) / float(config['settings']['steps'])

for currency in portfolio:
    portfolio[currency]["actual_percent"] = (float(portfolio[currency]["actual_balance"]) * float(portfolio[currency]["fx_rate"])) / portfolio_value
    
    optimal_balance = 0
    if rebalance:
        optimal_balance = portfolio[currency]["optimal_percent"] * portfolio_value
    else:
        optimal_balance = portfolio[currency]["optimal_percent"] * min(max_txn_size, portfolio[base_currency]["actual_balance"]) + portfolio[currency]["actual_balance"]
        
    if currency==base_currency:
        optimal_balance = max(0, optimal_balance - max_txn_size)
    
    if portfolio[currency]["fx_rate"] != 0:
        optimal_balance = optimal_balance / portfolio[currency]["fx_rate"]
    else:
        optimal_balance = 0
    portfolio[currency]["optimal_balance"] = optimal_balance
    print(currency)

## now that we have wallets and optimal portfolio, figure out which trades & transfers need to happen
## if can do on kraken do, else bitfinex else bittrex
## waterfall so that transfers happen immediately

final_wallets = {}
allocated_currencies = []
for exchange in exchanges:
    print(exchange)
    final_wallets[exchange] = {}
    for currency in wallets[exchange]:
        print(currency)
        if (wallets[exchange][currency]['fx_rate'] is not None) and (currency not in allocated_currencies):
            final_wallets[exchange][currency] = wallets[exchange][currency]
            final_wallets[exchange][currency]['optimal_balance'] = portfolio[currency]['optimal_balance']
            allocated_currencies.append(currency)




##figure out which transfers need to happen
transfers = {x:0 for x in exchanges[::-1]}
for exchange in exchanges[::-1]:
    account = final_wallets[exchange]
    total_account_balance = sum([account[currency]['actual_balance'] * account[currency]['fx_rate'] for currency in account])
    optimal_account_balance = sum([account[currency]['optimal_balance'] * account[currency]['fx_rate'] for currency in account])
    value_to_move = total_account_balance - optimal_account_balance
    if exchange in ['BITTREX', 'BITFINEX'] and value_to_move<0:
        transfers[exchange] = value_to_move
    if exchange=="KRAKEN" and value_to_move>0:
        transfers[exchange] = value_to_move
        account[config['settings']['transfer_currency']]['optimal_balance']


## make the kraken trades
for currency in final_wallets['KRAKEN']:
    if currency!=base_currency:
        trade_size = min(0,final_wallets['KRAKEN'][currency]['optimal_balance'] - final_wallets['KRAKEN'][currency]['actual_balance'])
        if currency==transfer_currency:
            trade_size += transfers['KRAKEN'] / final_wallets['KRAKEN'][currency]['fx_rate']
        if trade_size > 0:
            # make market order at trade_size, base base_currency
            print("Acquiring "+str(trade_size)+" "+currency+" on Kraken using "+base_currency)
            if not test:
                pairname = kraken_raw_currencies[kraken_currencies.index(currency)]+base_currency_for_kraken
                kraken_instance.query_private("AddOrder",req={"pair":pairname, "type":"buy","ordertype":"market","volume":str(trade_size)})
            # save the orders to csv
        if currency==transfer_currency and abs(transfers['BITFINEX']+transfers['BITTREX'])>0:
            # make the transfers
            transfer_size = transfers["KRAKEN"] / final_wallets['KRAKEN'][currency]['fx_rate']
            bittrex_transfer = transfer_size * (abs(transfers["BITTREX"]) / abs(transfers['BITFINEX']+transfers['BITTREX']))
            bitfinex_transfer = transfer_size * (abs(transfers["BITFINEX"]) / abs(transfers['BITFINEX']+transfers['BITTREX']))
            if not test:
                krakenized_currency = kraken_raw_currencies[kraken_currencies.index(transfer_currency)]
                if bitfinex_transfer > 0:
                    kraken_instance.query_private("Withdraw", req={'asset': krakenized_currency, 'key': config['KRAKEN']['bitfinex_transfer_name'], 'amount': bitfinex_transfer})
                if bittrex_transfer > 0:
                    kraken_instance.query_private("Withdraw", req={'asset': krakenized_currency, 'key': config['KRAKEN']['bittrex_transfer_name'], 'amount': bittrex_transfer})
                
            print("Transferring "+str(bittrex_transfer)+" "+transfer_currency+" from Kraken to Bittrex")
            print("Transferring "+str(bitfinex_transfer)+" "+transfer_currency+" from Kraken to Bitfinex")

for exchange in ['BITTREX', 'BITFINEX']:
    for currency in final_wallets[exchange]:
        trade_size = min(0,final_wallets[exchange][currency]['optimal_balance'] - final_wallets[exchange][currency]['actual_balance'])
        if trade_size > 0:
            if exchange=="BITFINEX":
                print("Acquiring "+str(trade_size)+" "+currency+" on "+exchange)
                if not test:
                    pairname = (currency+transfer_currency).lower()
                    bitfinex_instance.place_order(amount=trade_size, price=None, side="buy", ord_type="market", symbol=pairname)
            if exchange=="BITTREX":
                print("Acquiring "+str(trade_size)+" "+currency+" on "+exchange)
                if not test:
                    pairname = transfer_currency+"-"+currency
                    ## market orders are disabled for bittrex, we will use a limit order to cross the spread
                    buy_price = float(bittrex_instance.get_ticker(market=pairname)['result']['Ask'])
                    bittrex_instance.buy_limit(market=pairname, quantity=trade_size, rate=buy_price)
                # make market order at trade_size, base transfer_currency
                # save the orders to csv

#As the transfer & one investment coin is the same, we do not buy 10% ETH, we buy 60% ETH and than send it as above described to Bitfinex and Bittrex. 

#As soon as the ETH arrives there the buy actions above will be made.
## the script will account for the optimal/actual balances each time it is run, triggering will have to come from elsewhere

#Time of every transaction including it's fees and prices must be stored into the database. The price should be stored in both the base currency and the actual used coin (note - e.g. IOTA must be bought from EUR->ETH->IOTA) so I need the price EUR/IOTA & ETH/IOTA.
## we have no way to track transactions since they have to be cleared on the exchange before we can get any info about them
## so the prices/stats that you want will have to be collected and attributed after-the-fact since they are not returned at the time of orders
## for now we are using market orders, but would recommend switching to limit orders for safety asap

#Please also provide a ready to use installation how to get this installed on a local docker.
## please see readme.md for instructions