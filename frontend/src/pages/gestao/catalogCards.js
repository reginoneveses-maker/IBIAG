// Read-only display projection: preserve stored product/offer identities.
export function productVariants(name = '') {
  const match = name.match(/\(([^()]*)\)/);
  if (!match) return [name];
  const values = [...match[1].matchAll(/\d+(?:[.,]\d+)?\s*%/g)].map(m => m[0].replace(/\s/g,''));
  if (values.length < 2) return [name];
  // Split only an explicit list of percentages. Do not expand ranges or mixed descriptions.
  const remainder = match[1].replace(/\d+(?:[.,]\d+)?\s*%/g,'').replace(/\b(?:solids|sólidos|and|e)\b/gi,'').replace(/[,;/\s]/g,'');
  if (remainder) return [name];
  return [...new Set(values)].map(value => name.replace(match[0],value).replace(/\s+/g,' ').trim());
}
export function catalogSpecCode(card) {
  return 'catalog:' + encodeURIComponent(card.id) + ':' + encodeURIComponent(card.cardOffer?.id || '') + ':' + encodeURIComponent(card.cardName);
}
export function catalogCards(products, offers = []) {
  return products.flatMap(product => {
    const variants = offers.filter(offer => offer.product_id === product.id);
    return (variants.length ? variants : [null]).flatMap(offer => {
      const label = offer?.form || product.name;
      const names = productVariants(label);
      return names.map((name,index) => ({...product,cardKey:(offer?.id || product.id)+(names.length>1?':'+index:''),cardOffer:offer,cardName:name,isGroupedVariant:names.length>1}));
    });
  });
}
export function linkedIbiagSpecs(offer, specs) {
  return specs.filter(spec => (offer?.spec_ids || []).includes(spec.id) && !spec.deleted_at && spec.ibiag_file_path);
}
export function cardIbiagSpecs(card, specs) {
  const direct = specs.filter(s => s.code === catalogSpecCode(card) && !s.deleted_at && s.ibiag_file_path);
  return direct.length ? direct : card.isGroupedVariant ? [] : linkedIbiagSpecs(card.cardOffer,specs);
}
