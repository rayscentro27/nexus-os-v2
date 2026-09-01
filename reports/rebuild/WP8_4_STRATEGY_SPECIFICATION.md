# WP8.4 Strategy Specification

Strategy `nexus_sma_cross_v1`, version `1.0`, tests EUR/USD H1 completed bars.
Entry is SMA10 crossing above SMA30; exit is cross below or 24-bar maximum
hold. Risk is fixed 1% paper risk with 0.015% transaction-cost assumption.
The strategy version is immutable and remains `CANDIDATE` after rejection.

The implementation uses only completed-bar history up to each decision index;
no future bars or model-generated signals are used.

