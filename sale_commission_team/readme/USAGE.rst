Usage
=====

To use this module:

1. Create a sales order or invoice
2. Select a sales team
3. The system will automatically assign commission agents based on the configured rules:
   * Rules are processed in order of their sequence (lowest number first)
   * Each agent is added only once, using the commission from the highest priority rule
   * If no rules are configured for the team, no commissions will be assigned
   * If no team is selected, standard commission behavior applies

Example:
--------

If you have these rules configured (in order):
1. Team Commission
2. Team and Partner Commission
3. Partner Commission
4. Salesman Commission

And an agent appears in multiple rules:
* The agent will appear only once in the final commission
* Their commission will be taken from the first rule where they appear