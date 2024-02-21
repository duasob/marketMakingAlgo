# Market Making Algorithm

## Description
Algorithm created for Optiver's Trading Academy 2023. Out of 100+ participants, this algorithm ranked 3rd in the competition. 

The model has the capacity to take active arbitrage oportunities, but focuses on a passive strategy and maintains itself marked neutral - which is the core concept of [Market Making](https://en.wikipedia.org/wiki/Market_maker).

The idea is to estimate correctly, usign a combination of weighted averages from the current bids and aks, the price of the underlying stock. From that, we us the [Black Sholes Equation](https://en.wikipedia.org/wiki/Black–Scholes_model#:~:text=The%20Black–Scholes%20model%20assumes,market%2C%20cash%2C%20or%20bond.) to calculate the price of our futures. Multiple coefficients are used to calculate our *"confidence ratio"* and estimate the volume of our trades, limiting exposuro of our position at each instance. 

$$\frac12\sigma^2S^2\frac{\partial^2V}{\partial S^2}+rS\frac{\partial V}{\partial S}+\frac{\partial V}{\partial t}-rV=0$$

Another key aspect is the way we maintain the portfolio [Delta Neutral](https://en.wikipedia.org/wiki/Delta_neutral). Again, usign Black sholes we estimate our current Delta, but intead of actively acting to go back to neutrality, we take our delta into account when positioning bids or asks, and adjust the volume accordingly. This 
