import datetime as dt
import time
import logging
import random 

from optibook.synchronous_client import Exchange
from optibook.common_types import InstrumentType, OptionKind

from math import floor, ceil, exp
from black_scholes import call_value, put_value, call_delta, put_delta
from libs import calculate_current_time_to_date

exchange = Exchange()
exchange.connect()

logging.getLogger('client').setLevel('ERROR')

def round_down_to_tick(price, tick_size):
    return floor(price / tick_size) * tick_size


def round_up_to_tick(price, tick_size):
    return ceil(price / tick_size) * tick_size

#calculates the desires weighted average for the bids and asks
def ab_weighted_averages(instrument_id):
    try:
        order_book = exchange.get_last_price_book(instrument_id=instrument_id)    
        ask_volume, bid_volume, ask_price, bid_price = [], [], [], []

        #print(f"Market value for intrument is {order_book.asks[0].price} - {order_book.bids[0].price}")
        
        #Dynamically get the order book orders - cannot fix the number of orders as it constantly varies
        for i in range(len(order_book.asks)):
            ask_volume.append(order_book.asks[i].volume)
            ask_price.append(order_book.asks[i].price)
        for i in range(len(order_book.bids)):
            bid_volume.append(order_book.bids[i].volume)
            bid_price.append(order_book.bids[i].price)
            
        total_ask_v = sum(ask_volume)
        total_bid_v = sum(bid_volume)
        ask_average = 0
        bid_average = 0

        #Calculate weighted average for the buy and sell 
        for i in range(len(ask_volume)):
            ask_average += (ask_volume[i]*ask_price[i])/total_ask_v
        for i in range(len(bid_volume)):
            bid_average += (bid_volume[i]*bid_price[i])/total_bid_v
    
        l = []
        l.append(ask_average)
        l.append(bid_average)
        l.append(total_ask_v)
        l.append(total_bid_v)
        
        return l
    
    except Exception as e:
        print(f"An error occurred at ab_weighted_averages: {e}")
        return None


def volume_weighted_average(instrument_id):
    try:
        l = ab_weighted_averages(instrument_id)

        #We also need to take the weighted average between the previous averages 
        w = ((l[0]*l[2]) + (l[1]*l[3]))/(l[2] + l[3])
        
        return w
    except Exception as e:
        print(f"An error occurred at volume_weighted_average: {e}")
        return None

    
def place_bid_ask_spread(instrument_id, instrument, perfect_price, delta):
    try:
        
        #trades = exchange.poll_new_trades(instrument_id)
        #for trade in trades:
            #print(f'- Last period, traded {trade.volume} lots in {instrument_id} at price {trade.price:.2f}, side {trade.side}.')
    
        # Pull (remove) all existing outstanding orders
        orders = exchange.get_outstanding_orders(instrument_id)
        for order_id, order in orders.items():
            #print(f'- Deleting old {order.side} order in {instrument_id} for {order.volume} @ {order.price:8.2f}.')
            exchange.delete_order(instrument_id, order_id=order_id)


        averages = ab_weighted_averages(instrument_id)
        p_limit = 100 #max positions allowed to own in the competition
        best_a = averages[0]
        best_b = averages[1]
        
        
        #by the way the weighted averaging works, this could happen (we may still want to buy/sell at the same price)
        my_a = round_down_to_tick((best_a + perfect_price)/2, 0.010)
        my_b = round_up_to_tick((best_b + perfect_price)/2, 0.010)
        
        #print(f"{best_a}        {my_a}      {perfect_price}     {my_b}      {best_b} ")
        
        #Ill do a confidence ratio (the more space we have, the greated the conficence)
        
        magic= 500 #and we scale that by a magic factor 
        """
         #the most important thing is to have into account our delta - we want delta to go to 0
            #we need to know if this is a call or a put - and adjust the number of positons accordingly
            # puts have a delta from -1 to 0 // calls have delta from 0 - 1
            
            if our delta is negative - we want to sell puts and buy calls
            if our delta is positive - we want to buy puts and sell calls
            
            d is a marker that indicates how much we want to buy this option (1 would mean that we really want to buy - and we dont want to sell)
            our delta could theoretically go from (if we have 6 insrtuments, with a max position of 100)  600 to -600
            
            so d = (delta + 600) / 1200 would cover it all, but i dont think it really makes sense - we take borders from 300 to -300
            
            For futures, we need to sell a future when we have a positive delta
            Or buy them when our delta is negative 
        """    
        d = (delta + 100)/200
        print(f"d = {d}, delta = {delta}")

        if instrument.instrument_type == InstrumentType.STOCK_FUTURE:
            d = 1 - d
            my_a = round_down_to_tick((best_a + my_b)/2, 0.010)
            my_b = round_up_to_tick((best_b + my_b)/2, 0.010)
        if instrument.instrument_type == InstrumentType.STOCK_OPTION:
            if instrument.option_kind == OptionKind.CALL:
                d = 1 - d
            #print(instrument.option_kind, d, delta)

        
        c_a = min(((best_a - perfect_price)/perfect_price)*magic*(1-d), 1)
        c_b = min(((perfect_price - best_b)/perfect_price)*magic*d, 1)
        print(c_a, c_b)
        #and then we ask/bid in proportion to what we have left? with a minimum of 5 for example 
        #we are selling ->  limit = 100 + pos
        my_pos = exchange.get_positions()[instrument_id]
        #my_pos = random.randrange(-p_limit, p_limit + 1, 2)
        max_ask = floor(c_a*(p_limit+my_pos))
        #we are buying -> limit = 100 - pos
        max_bid = floor(c_b*(p_limit-my_pos))
        
        """
        l = []
        l.append(my_a)
        l.append(my_b)
        l.append(max_ask)
        l.append(max_bid)
        
        print(f"{best_a}        {my_a}      {perfect_price}     {my_b}      {best_b} ")
        print(f"We have {my_pos} positions, we sell {max_ask} and buy {max_bid}")
        """
        
        if my_a != my_b:
            if max_ask > 0:
                exchange.insert_order(
                    instrument_id=instrument_id,
                    price=my_a,
                    volume=max_ask,
                    side='ask',
                    order_type='limit',
                )
            if max_bid > 0:
                exchange.insert_order(
                    instrument_id=instrument_id,
                    price=my_b,
                    volume=max_bid,
                    side='bid',
                    order_type='limit',
                )
        else: 
            print("-------------------------------WE HAD THE SAME PRICE ---------------------------------------------")
        return 
    except Exception as e:
        print(f"An error occurred at place_bid_ask_spread: {e}")
        return None
    

def theoretical_option_value(expiry, strike, option_kind, stock_value, interest_rate, volatility):
    # Calculate the theoretical value of an option based on Black & Scholes assumptions
    time_to_expiry = calculate_current_time_to_date(expiry)

    if option_kind == OptionKind.CALL:
        option_value = call_value(S=stock_value, K=strike, T=time_to_expiry, r=interest_rate, sigma=volatility)
    elif option_kind == OptionKind.PUT:
        option_value = put_value(S=stock_value, K=strike, T=time_to_expiry, r=interest_rate, sigma=volatility)

    return option_value


def theoretical_future_value(future, future_id, stock_value): 
    # Calculate the theoretical value of a future based on Black & Scholes assumptions
    time_to_expiry = calculate_current_time_to_date(future.expiry)
    interest_rate=0.03
    v  = stock_value*exp(interest_rate*time_to_expiry)
    print(f"the ratio is {exp(interest_rate*time_to_expiry)}")
    print(f"for {future_id} with the stock at {stock_value} the price is {v}")
    return v

    
def calculate_option_delta(expiry_date, strike, option_kind, stock_value, interest_rate, volatility):
    # Calculate the delta of an option based on Black & Scholes assumptions
    time_to_expiry = calculate_current_time_to_date(expiry_date)

    if option_kind == OptionKind.CALL:
        option_delta = call_delta(S=stock_value, K=strike, T=time_to_expiry, r=interest_rate, sigma=volatility)
    elif option_kind == OptionKind.PUT:
        option_delta = put_delta(S=stock_value, K=strike, T=time_to_expiry, r=interest_rate, sigma=volatility)
    else:
        raise Exception(f"""Got unexpected value for option_kind argument, should be OptionKind.CALL or OptionKind.PUT but was {option_kind}.""")

    return option_delta


def load_instruments_for_underlying(underlying_stock_id):
    all_instruments = exchange.get_instruments()
    stock = all_instruments[underlying_stock_id]
    options = {instrument_id: instrument
               for instrument_id, instrument in all_instruments.items()
               if instrument.instrument_type == InstrumentType.STOCK_OPTION 
               and instrument.base_instrument_id == underlying_stock_id}
    futures = {instrument_id: instrument
               for instrument_id, instrument in all_instruments.items()
               if instrument.instrument_type == InstrumentType.STOCK_FUTURE
               and instrument.base_instrument_id == underlying_stock_id}
    return stock, options, futures

def active_trade():
    instruments = {"SAN" : "SAN_DUAL", "NVDA": "NVDA_DUAL"}

    for i in instruments:
        stock_order_book = exchange.get_last_price_book(i)
        stock_order_book_dual = exchange.get_last_price_book(instruments[i])
        
        if not (stock_order_book and stock_order_book.bids and stock_order_book.asks) or not(stock_order_book_dual and stock_order_book_dual.bids and stock_order_book_dual.asks):
            print(f'Order book for {i} or {instruments[i]} does not have bids or offers. Skipping iteration.')
            time.sleep(0.1)
            continue
        
        #here we get the order books for both the instrument and its dual
        best_bid_price = stock_order_book.bids[0].price
        best_ask_price = stock_order_book.asks[0].price
        
        best_bid_price_dual = stock_order_book_dual.bids[0].price
        best_ask_price_dual = stock_order_book_dual.asks[0].price
            
        s1 =  best_bid_price - best_ask_price_dual
        s2 =  best_bid_price_dual - best_ask_price 
        print(s1, s2)  
        #We want to see the max number of positions we can profitably trade - atm we only take into account the best bid/ask
        if(s1>0):
            #because you are buying instruments[i] (dual) and selling i
            max_pos = min(stock_order_book_dual.asks[0].volume, stock_order_book.bids[0].volume, 100 - exchange.get_positions()[instruments[i]], 100 + exchange.get_positions()[i])   
            
            c_a = min(((best_a - perfect_price)/perfect_price)*magic, 1)
            c_b = min(((perfect_price - best_b)/perfect_price)*magic, 1)
            exchange.insert_order(instruments[i], price=best_ask_price_dual, volume=max_pos, side='bid', order_type='ioc')
            exchange.insert_order(i, price=best_bid_price, volume=max_pos, side='ask', order_type='ioc') 
            
            print(f"buy {max_pos} at {best_ask_price_dual} and sell {max_pos} at {best_bid_price}")
            
        if(s2>0):
             #because you are buying i and selling instruments[i] (dual)
            max_pos = min(stock_order_book_dual.bids[0].volume, stock_order_book.asks[0].volume, highest_positions - exchange.get_positions()[i], highest_positions + exchange.get_positions()[instruments[i]] )
    
    
            exchange.insert_order(i, price=best_ask_price, volume=max_pos, side='bid', order_type='ioc')
            exchange.insert_order(instruments[i], price=best_bid_price_dual, volume=max_pos, side='ask', order_type='ioc')
            
            print(f"buy {max_pos} at {best_ask_price} and sell {max_pos} at {best_bid_price_dual}")
             
    print(exchange.get_positions()["SAN"])
    print(exchange.get_positions()["SAN_DUAL"])
    print(exchange.get_positions()["NVDA"])
    print(exchange.get_positions()["NVDA_DUAL"])
    
    
def overall_delta(STOCK_ID):
    # Calculates the overall delta of the portfolio
    try:
        stock, options, futures = load_instruments_for_underlying(STOCK_ID)
        total_delta = 0
        for option_id, option in options.items():
            delta = calculate_option_delta(expiry_date=option.expiry,
                                               strike=option.strike,
                                               option_kind=option.option_kind,
                                               stock_value=stock_value,
                                               interest_rate=0.03,
                                               volatility=3.0)
            my_pos = exchange.get_positions()[option_id]
            #my_pos = random.randrange(-100, 101, 2)
            total_delta += my_pos*delta
            #print(f" {option_id} : {my_pos} postions , {delta} delta -> {total_delta} total_delta")
        
        total_delta += exchange.get_positions()[STOCK_ID]
        #print(f"total_delta = {total_delta}")
        
        for future_id, future in futures.items():
            total_delta += exchange.get_positions()[future_id]
        
        #print(f"new total_delta = {total_delta}")
        return total_delta
    except Exception as e:
        print(f"An error occurred in overall_delta: {e}")
        return None


def track_delta(total_delta, it, delta, min_delta, max_delta):
    # Tracks the delta of the portfolio over time - helps to see if the delta is converging to 0
    min_delta = min(delta, min_delta)
    max_delta = max(delta, max_delta)
    it += 1
    total_delta += delta
    average_delta = (total_delta + delta)/it
    
    print(f"Average: {average_delta}    Delta: {delta}     C: {it}       Min: {min_delta}    Max: {max_delta}")
    
    return average_delta, total_delta, it, min_delta, max_delta

def track_pnl(last_pnl):
    # Tracks the pnl of the portfolio over time - helps to see the rate of change of the pnl
    pnl = exchange.get_pnl()
    increase = pnl - last_pnl
    print(f"PNL: {pnl}, last: {last_pnl}, diff: {increase}")
    last_pnl = pnl
    return last_pnl, increase


# Load all instruments for use in the algorithm
STOCK_ID = 'NVDA'
stock, options, futures = load_instruments_for_underlying(STOCK_ID)
max_delta = 0
min_delta = 0
average_delta = 0
total_delta = total_incr = 0  
c = p = 0
last_pnl = exchange.get_pnl() 
_ = __ = 0
last_time = time.time()

while True:
    print("---------------")
    
    """
    delta = overall_delta(STOCK_ID)
    a = place_bid_ask_spread("NVDA_DUAL", None , stock_value, delta)
    print(stock_value)
    time.sleep(0.2)


    for future_id, future in futures.items():
        try:
            stock_value = volume_weighted_average(STOCK_ID)
            print(theoretical_future_value(future, future_id , stock_value))
            print(volume_weighted_average(future_id))
            time.sleep(0.1)
        except Exception as e:
            print(f"An error occurred at the future loop: {e}")

    """
    for option_id, option in options.items():
        try:
            stock_value = volume_weighted_average(STOCK_ID)
            delta = overall_delta(STOCK_ID)

            #average_delta, total_delta, c, min_delta, max_delta = track_delta(total_delta, c, delta, min_delta, max_delta)
            
            theoretical_value = theoretical_option_value(expiry=option.expiry,
                                                               strike=option.strike,
                                                               option_kind=option.option_kind,
                                                               stock_value=stock_value,
                                                               interest_rate=0.03,
                                                               volatility=3.0)
            place_bid_ask_spread(option_id, option, theoretical_value, delta)
            
            time.sleep(0.2/len(options))
            
            
        except Exception as e:
            print(f"An error occurred at the for loop: {e}")
    
    """
        for future_id , future in futures.items():
            try:
                theoretical_value = theoretical_future_value(future, stock_value)
                delta = overall_delta(STOCK_ID)
                l = place_bid_ask_spread(future_id, future, theoretical_value, delta)
                time.sleep(0.2)
                #print(future_id)
                
                total_delta += delta
                min_delta = min(min_delta, delta)
                max_delta = max(max_delta, delta)
                c += 1
                print(average_delta)
                average_delta = (total_delta + delta)/c
                print(f"Average: {average_delta}    Delta: {delta}     C: {c}")
            except Exception as e:
                print(f"An error occurred at the for loop: {e}")
        print("the final delta was: ", delta, f"the min delta is {min_delta}, and the max delta is {max_delta}, the average_delta is {average_delta}")
        """

        

    
