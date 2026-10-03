import {computePrice,priceNumber,savedPriceForm} from './pricing';
const form={supplier_price:'17,50',quantity:'1000',extras:[],taxes:[{pct:'6'}],margin_pct:'15',margin_mode:'margin',currency:'BRL',exchange_rate:'5,2'};
test('1000 kg times 17,50 is 17500; selling, tax and profit totals remain separate',()=>{
 const r=computePrice(form);expect(r.error).toBe('');expect(r.supplierTotal).toBe(17500);expect(r.price).toBe(22.1519);expect(r.saleTotal).toBe(22151.90);expect(r.taxTotal).toBe(1329.11);expect(r.profitTotal).toBe(3322.79);expect(r.priceUsd).toBe(4.26);
});
test('fractional quantities, extras, markup and USD agree with the backend',()=>{
 const r=computePrice({...form,supplier_price:10,quantity:2.5,extras:[{value:'2,50'}],taxes:[{pct:10}],margin_pct:20,margin_mode:'markup',currency:'USD',exchange_rate:5});
 expect(r.costTotal).toBe(31.25);expect(r.price).toBe(16.6667);expect(r.saleTotal).toBe(41.67);expect(r.saleTotalUsd).toBe(8.33);
});
test.each(['',0,-1,'NaN','abc'])('invalid quantity %s produces an error',quantity=>expect(computePrice({...form,quantity}).error).toBeTruthy());
test.each([{margin_pct:94},{taxes:[{pct:100}]},{supplier_price:-1},{extras:[{value:-1}]},{currency:'USD',exchange_rate:0}])('invalid calculation is not presented as a valid sale',change=>expect(computePrice({...form,...change}).error).toBeTruthy());
test('Portuguese decimals, grouped quantities and legacy quantities are preserved',()=>{
 expect(priceNumber('17,50')).toBe(17.5);expect(priceNumber('1.234,56')).toBe(1234.56);expect(priceNumber('1,234.56')).toBe(1234.56);expect(priceNumber('1.000',true)).toBe(1000);expect(priceNumber('0.500',true)).toBe(.5);
 const legacy=savedPriceForm({unit:'kg 1000',supplier_price:17.5,taxes:[],taxes_pct:0,extras:[]});expect(legacy.quantity).toBe(1000);expect(legacy.unit).toBe('kg');expect(legacy.taxes).toEqual([]);
});
