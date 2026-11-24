// Nexus-authored fixture (MIT).
import http from "node:http";
import { listCatalog } from "./catalog.js";
import { addToCart } from "./cart.js";

export function route(method, path, body, session) {
  if (method === "GET" && path === "/api/catalog") return { status: 200, json: listCatalog() };
  if (method === "POST" && path === "/api/cart") return { status: 200, json: addToCart(session.cart || {}, body.sku, body.quantity) };
  return { status: 404, json: { error: "NOT_FOUND" } };
}

export function start(port = 18797) {
  const sessions = new Map();
  return http.createServer((req, res) => {
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", () => {
      const session = sessions.get("default") || {};
      const out = route(req.method, req.url, raw ? JSON.parse(raw) : {}, session);
      if (out.json && out.json.cart) sessions.set("default", { cart: out.json.cart });
      res.writeHead(out.status, { "content-type": "application/json" });
      res.end(JSON.stringify(out.json));
    });
  }).listen(port, "127.0.0.1");
}
