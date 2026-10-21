import {catalogCards, linkedIbiagSpecs, productVariants, cardIbiagSpecs, catalogSpecCode} from './catalogCards';

test('distinct pulp offers render independently without rewriting stored products', () => {
  const products = [{id:'acai',name:'Açaí Pulp'},{id:'guarana',name:'Guarana Powder'}];
  const offers = [8,12,14].map(percent => ({id:String(percent),product_id:'acai',form:`Açaí Pulp ${percent}%`,supplier_name:'Nossa Fruta'}));
  const before = JSON.stringify({products,offers});
  const cards = catalogCards(products,offers);
  expect(cards.map(card => card.cardName)).toEqual(['Açaí Pulp 8%','Açaí Pulp 12%','Açaí Pulp 14%','Guarana Powder']);
  expect(cards[1].cardOffer.id).toBe('12');
  expect(JSON.stringify({products,offers})).toBe(before);
});
test('never substitutes supplier originals or unrelated IBIAG files for linked IBIAG files', () => {
  const specs = [
    {id:'original',original_file_path:'supplier.pdf'},
    {id:'correct',ibiag_file_path:'ibiag.pdf'},
    {id:'other',ibiag_file_path:'other.pdf'},
    {id:'deleted',ibiag_file_path:'deleted.pdf',deleted_at:'2026-10-20'}
  ];
  expect(linkedIbiagSpecs({spec_ids:['original','correct','deleted']},specs).map(s => s.id)).toEqual(['correct']);
  expect(linkedIbiagSpecs(null,specs)).toEqual([]);
});

test('compound solids cards isolate each PDF binding and preserve source records',()=>{
 const products=[{id:'p',name:'Açaí Pulp (8%, 12%, 14% solids)'}];
 const offers=[{id:'o',product_id:'p',form:'',spec_ids:['old']}];
 const before=JSON.stringify({products,offers});
 const cards=catalogCards(products,offers);
 expect(cards.map(c=>c.cardName)).toEqual(['Açaí Pulp 8%','Açaí Pulp 12%','Açaí Pulp 14%']);
 const specs=[{id:'old',ibiag_file_path:'generic.pdf'},{id:'exact',code:catalogSpecCode(cards[1]),ibiag_file_path:'12.pdf'}];
 expect(cardIbiagSpecs(cards[0],specs)).toEqual([]);
 expect(cardIbiagSpecs(cards[1],specs).map(s=>s.id)).toEqual(['exact']);
 expect(JSON.stringify({products,offers})).toBe(before);
 expect(productVariants('Pulp (8%-14% solids)')).toEqual(['Pulp (8%-14% solids)']);
});

test('process-only forms preserve ingredient names and explicit imported spec distinctions',()=>{
 const products=[{id:'acerola',name:'Acerola Concentrate'},{id:'camu',name:'Camu Camu Powder'}];
 const offers=[
 {id:'a',product_id:'acerola',form:'Clarified / Conc.',notes:'Spec: Acerola Concentrate 65° Brix Clarified | Embalagem: Metal Drums'},
 {id:'b',product_id:'acerola',form:'Clarified / Conc.',notes:'Spec: Acerola Concentrate 50° Brix Cloudy | Embalagem: Metal Drums'},
 {id:'c',product_id:'camu',form:'Freeze Dried'}];
 expect(catalogCards(products,offers).map(c=>c.cardName)).toEqual(['Acerola Concentrate 65° Brix Clarified','Acerola Concentrate 50° Brix Cloudy','Camu Camu Powder · Freeze Dried']);
});

test('correcting a generic title preserves previously saved PDF binding keys',()=>{
 const card=catalogCards([{id:'p',name:'Acerola Powder'}],[{id:'o',product_id:'p',form:'Freeze Dried'}])[0];
 expect(card.cardName).toBe('Acerola Powder · Freeze Dried');
 expect(catalogSpecCode(card)).toBe('catalog:p:o:Freeze%20Dried');
});
