export function priceNumber(value, quantity = false) {
  if (typeof value === "number") return value;
  let text = String(value ?? "").trim().replace(/\s/g, "");
  if (!text) return 0;
  if (text.includes(",") && text.includes(".")) {
    text = text.lastIndexOf(",") > text.lastIndexOf(".") ? text.replace(/\./g, "").replace(",", ".") : text.replace(/,/g, "");
  } else if (text.includes(",")) text = text.replace(",", ".");
  else if (quantity && /^[1-9]\d{0,2}(?:\.\d{3})+$/.test(text)) text = text.replace(/\./g, "");
  return Number(text);
}
const round = (value, digits) => Math.round((value + Number.EPSILON) * 10 ** digits) / 10 ** digits;
export const priceMoney = (value, currency = "BRL", unit = false) => new Intl.NumberFormat("pt-BR", {
  style:"currency", currency, minimumFractionDigits:2, maximumFractionDigits:unit ? 4 : 2,
}).format(value);

export function computePrice(f) {
  const supplier = priceNumber(f.supplier_price), quantity = priceNumber(f.quantity ?? 1, true);
  const margin = priceNumber(f.margin_pct), rate = priceNumber(f.exchange_rate);
  const extraValues = (f.extras || []).map(x => priceNumber(x.value));
  const taxValues = (f.taxes || []).map(x => priceNumber(x.pct));
  const extras = extraValues.reduce((a,b)=>a+b,0), taxes = taxValues.reduce((a,b)=>a+b,0);
  let error = "";
  if (![supplier,quantity,margin,rate,...extraValues,...taxValues].every(Number.isFinite)) error = "Informe apenas valores numéricos válidos.";
  else if (quantity <= 0) error = "Informe uma quantidade maior que zero.";
  else if ([supplier,margin,rate,...extraValues,...taxValues].some(x=>x<0)) error = "Preços, custos e percentuais não podem ser negativos.";
  else if (taxes >= 100 || (f.margin_mode !== "markup" && margin + taxes >= 100)) error = "Impostos e margem precisam permitir um preço de venda válido (soma menor que 100%).";
  else if (f.currency === "USD" && rate <= 0) error = "Informe o câmbio para calcular em USD.";
  const cost = supplier + extras;
  const rawPrice = f.margin_mode === "markup" ? cost * (1 + margin/100) / (1 - taxes/100) : cost / (1 - (margin + taxes)/100);
  const price = error ? 0 : round(rawPrice,4), priceUsd = rate > 0 ? round(price/rate,4) : 0;
  const taxValue = price*taxes/100, profit = price-taxValue-cost;
  const supplierTotal = round(supplier*quantity,2), extrasTotal = round(extras*quantity,2), costTotal = round(cost*quantity,2);
  const saleTotal = round(price*quantity,2), saleTotalUsd = round(priceUsd*quantity,2), taxTotal = round(saleTotal*taxes/100,2);
  const profitTotal = round(saleTotal-taxTotal-costTotal,2);
  if (!error && ![price,priceUsd,supplierTotal,extrasTotal,costTotal,saleTotal,saleTotalUsd,taxTotal,profitTotal].every(Number.isFinite)) error = "Os valores informados são grandes demais para calcular.";
  return {error,supplier,quantity,rate,extras,taxes,cost,price,taxValue,profit,priceUsd,supplierTotal,extrasTotal,costTotal,saleTotal,saleTotalUsd,taxTotal,profitTotal,
    marginReal:price>0?profit/price*100:0,markupReal:cost>0?profit/cost*100:0};
}

export function savedPriceForm(p) {
  const oldUnit = String(p.unit || "kg").match(/^(kg|l|un|t)\s*([\d.,]+)$/i);
  return {...p, product_id:p.product_id||"",offer_id:p.offer_id||"",unit:oldUnit ? oldUnit[1].toLowerCase() : p.unit||"kg",
    quantity:oldUnit && (!p.quantity || p.quantity===1) ? priceNumber(oldUnit[2],true) : p.quantity??1,
    extras:p.extras?.length ? p.extras : p.extra_costs ? [{name:"Custos adicionais cadastrados",value:p.extra_costs}] : [],
    taxes:p.taxes?.length ? p.taxes : p.taxes_pct ? [{name:"Impostos cadastrados",pct:p.taxes_pct}] : []};
}
