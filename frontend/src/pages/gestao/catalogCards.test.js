import {catalogCards, linkedIbiagSpecs} from './catalogCards';

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
