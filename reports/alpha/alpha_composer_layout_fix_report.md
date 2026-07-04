# Alpha Composer Layout Fix

The conversation panel has a bounded responsive height. The transcript alone scrolls vertically; the composer is a non-shrinking sticky bottom region with textarea and action buttons. The two-column layout uses auto-fit/minmax so narrow screens stack without placing the provider panel over the input.
