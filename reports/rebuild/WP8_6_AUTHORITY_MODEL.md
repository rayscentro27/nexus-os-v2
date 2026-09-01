# WP8.6 Authority Model

Paper and live authority are separate. Research automation is enabled; Forex paper auto-trading is bounded in `OANDA_PRACTICE`; all live Forex/Crypto/Options authority is `NONE`. The execution chain is strategy evaluation → money management → risk → authority → broker adapter → Practice → reconciliation/journal. No strategy calls OANDA directly.
