# Seat 5: execution

The execution seat is code. No model sits here.

Its job: send exactly the order the desk approved, then check
that the broker's answer matches it.

It receives: the approved symbol, side, size and limit.

It returns: the order, with keys `symbol`, `side`, `qty` and
`limit_price`, and later the broker's order id and events.

Rules:
- It cannot change the symbol, the side, the size or the limit.
- It sends nothing without a signed mandate.
- A missing reply, a timeout or a mismatch means no order.
