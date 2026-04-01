# Sale Commission Period Tier

This module extends the functionality of sale commissions to add tiered commission rates based on periodic sales performance.

## Features

* Define commission tiers based on sales volume within a period
* Automatically calculate commission rates according to achieved sales targets
* Support for multiple period types (monthly, quarterly, yearly)
* Dynamic commission rates that adjust based on sales performance
* Integration with existing sale commission settlement process

## How it works

The module allows you to set up different commission rates that are applied based on the total sales amount achieved by a salesperson within a defined period. For example:

* Sales up to $10,000: 2% commission
* Sales from $10,001 to $20,000: 3% commission
* Sales above $20,000: 4% commission

When settlements are generated, the system automatically:
1. Calculates the total sales for the period
2. Determines the appropriate commission tier
3. Applies the corresponding commission rate

This encourages sales performance by offering higher commission rates as sales targets are achieved.
