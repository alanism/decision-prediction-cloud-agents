# Margin Safety

The margin engine uses manual position and broker-requirement assumptions only. It has no account or brokerage connection.

```text
equity = position_market_value - borrowed_amount
margin_ratio = equity / position_market_value
loan_to_value = borrowed_amount / position_market_value
required_equity = maintenance_requirement × position_market_value
call_price = borrowed_amount / (shares × (1 - maintenance_requirement))
liquidation_buffer = current_price - call_price
```

For each supplied price decline, the engine calculates stressed price, stressed market value, loss, remaining equity, stressed margin ratio, and whether that ratio reaches the supplied maintenance threshold.

The estimated call price does not model every broker rule, intraday policy, concentration add-on, interest charge, gap, or execution condition. All results are stress calculations under supplied requirement assumptions.

