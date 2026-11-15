// Nexus-authored fixture (MIT).
import { findItem } from "./catalog.js";

export function addToCart(cart, sku, quantity = 1) {
  const item = findItem(sku);
  if (!item) throw new Error("UNKNOWN_SKU");
  if (!Number.isInteger(quantity) || quantity < 1 || quantity > 10) throw new Error("BAD_QUANTITY");
  const next = { ...cart, [sku]: (cart[sku] || 0) + quantity };
  return { cart: next, totalCents: Object.entries(next).reduce((sum, [s, q]) => sum + findItem(s).priceCents * q, 0) };
}
