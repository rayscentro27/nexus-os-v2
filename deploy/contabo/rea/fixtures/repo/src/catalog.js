// Nexus-authored fixture (MIT).
export const CATALOG = [
  { sku: "MUG-11OZ", title: "Reading mug", priceCents: 1999 },
  { sku: "ORN-HOME", title: "Home ornament", priceCents: 1499 },
];

export function listCatalog() {
  return CATALOG.map(({ sku, title, priceCents }) => ({ sku, title, price: priceCents / 100 }));
}

export function findItem(sku) {
  return CATALOG.find((item) => item.sku === sku) || null;
}
