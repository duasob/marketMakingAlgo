# Market Making Algorithm
- [Desctription](#description)
- [Strategy](#strategy)
- [Code](#code)
- [Things to Improve](#things-to-improve)

## Description
Algorithm created for Optiver's Trading Academy 2023. Out of 100+ participants, this algorithm ranked 3rd in the competition. 
<div style="text-align: center;">
    <img src="assets/certificate.jpg" width="600" height="400">
</div>


This `Readme` is not an exhaustive explanation of the code, which is in total more than 400 lines, but serves to give an understanding of the strategy taken, as well as a brief description of the important functions. 

## Strategy
The model has the capacity to take active arbitrage oportunities, but focuses on a passive strategy and maintains itself market neutral - which is the core concept of [Market Making](https://en.wikipedia.org/wiki/Market_maker) that we had to exemplify in the competition.


The idea is to estimate correctly, usign a combination of weighted averages from the current bids and aks, the price of the underlying stock. From that, we us the [Black Sholes Equation](https://en.wikipedia.org/wiki/Black–Scholes_model#:~:text=The%20Black–Scholes%20model%20assumes,market%2C%20cash%2C%20or%20bond.) to calculate the price of our futures. Multiple coefficients are used to calculate our *"confidence ratio"* and estimate the volume of our trades, limiting the exposure of our position at each instance. 

$$\frac12\sigma^2S^2\frac{\partial^2V}{\partial S^2}+rS\frac{\partial V}{\partial S}+\frac{\partial V}{\partial t}-rV=0$$

Another key aspect is the way we maintain the portfolio [Delta Neutral](https://en.wikipedia.org/wiki/Delta_neutral). Again, usign Black sholes we estimate our current Delta, but instead of actively acting to go back to neutrality, we take our delta into account when positioning further bids or asks, and adjust the volume accordingly. This ensures that we don't "waste" interactions actively trading, and we focus on constantly placing passive bets that we are confident to be profitable. 

## Code

Some of the functions in the code rely on *Optibook* library, but the core idea of the Strategy is fully interchangable to any other environment. The code is attached in the github repo as `algo.py`.


There are 2 main functions to take an action in a given orderbook: 

- `active_trade` that seeks for arbitrage oporunities and inmediately acts upon those. Arbitrage oportunities are scanned between `Dual`stocks, where there should be a 1:1 correlation between the prices

- `place_bid_ask_spread` is the leading passive strategy that accounts for the highest part of the performed trades. It is mostly based on 3 parameters:

    - **Portfolio's Delta:** we want our portfolio to remain delta neutral. We dynamically act to place the volume of our bets to move our delta in the desired direction. We calculate our portfoli's delta with `overall_delta` and the impact of the stock we are trading with `calculate_option_delta` (works also for futures).

    - **Total Position:** During the competition, each team had a limited exposure of 100 positions. This was very important, and to maximize our trades we wanted our position to remain around 0. To solve this, the approach is similar to the one for the delta , where we dinamically adjust the volume of our trades.

    - **Confidence Ratio:** from `volume_weighted_average` and using Black Sholes, we estimate the price of the stock we are trading. We derive a confidence ratio, for the space between the estimated price and the current price - to avoid being overly exposed to fast price fluctuations against our favour. 

<div style="text-align: center;">
    <img src="assets/strategy.png" width="600" height="400">
</div>

Other functions such as `track_delta` or `track_pnl` are used for monitoring purposes, to ensure that overtime we stay delta neutral, and to see the impact on how tweaking different components had an impact in our PNL. This was a key part in the optimazation of our stategy. 


<div style="text-align: center;">
    <img src="assets/pnl.jpg" width="500" height="400">
</div>

This graph measures the hourly PNL rate of each team. We where `team-028`, and you can clearly see the fastest growing gradient after implementing a change at `:15`, which had a positive impact on our performance.

## Things to Improve

Overall, the performance of this strategy was excellent. The 2 teams that had a higher position at the end of the competition were usign a similar strategy, but also trading indices. We were not aware that index trading was a part of the competition, but we should have spent more time on fully understanding all the possible options allowed.

Nevertheless, we this meant that we had the best strategy for purely trading options and futures, and if we had extrapolated the strategy to indices, we could have vastly improved our overall performance. 

Also, the active strategy could be improved by taking arbitrage oportunities between options futures and underlying stocks, taking Black Sholes as the relation between those. This was not done as active trading was a minimal part of our PNL, and choose to focus on improving the passive strategy.


<div style="text-align: center;">
    <img src="assets/graph.jpg" width="500" height="400">
</div>
