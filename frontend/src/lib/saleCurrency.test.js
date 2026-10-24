import {saleAmount,saleCurrency,saleMoney,saleTotals} from "./saleCurrency";
test("legacy USD and explicit denominations do not reinterpret values",()=>{
 expect(saleCurrency({total_usd:12.34})).toBe("USD");
 expect(saleAmount({total_usd:12.34})).toBe(12.34);
 for(const currency of ["BRL","EUR"]){
  const row={currency,total_amount:1234.56,total_usd:0};
  expect(saleAmount(row)).toBe(1234.56);
  expect(saleMoney(row)).toMatch(/1[.,]234[.,]56/);
 }
});
test("totals remain separate by denomination and use cents",()=>{
 expect(saleTotals([{total_usd:0.1},{total_usd:0.2},{currency:"EUR",total_amount:12,total_usd:0},{currency:"BRL",total_amount:30,total_usd:0}]))
 .toEqual([{currency:"BRL",total:30},{currency:"EUR",total:12},{currency:"USD",total:0.3}]);
 expect(saleMoney({currency:"EUR",total_usd:99})).toBe("Valor pendente de revisão");
 expect(saleTotals([{currency:"EUR",total_usd:99},{currency:"INVALID",total_amount:99},{total_usd:NaN}])).toEqual([]);
});
