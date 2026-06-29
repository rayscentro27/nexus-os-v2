const TAX_RATE = 0.08;

/**
 * Calculates the total price of the items in a cart.
 *
 * Set `includeTax` to `true` to add 8% tax. The result is rounded to the
 * nearest cent to avoid exposing floating-point artifacts in currency values.
 */
export function calculateCartTotal(
  prices: number[],
  includeTax = false,
): number {
  const subtotal = prices.reduce((total, price) => total + price, 0);
  const total = includeTax ? subtotal * (1 + TAX_RATE) : subtotal;

  return Math.round((total + Number.EPSILON) * 100) / 100;
}
