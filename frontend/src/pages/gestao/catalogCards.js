// Display-only projection: retain original product and offer identities.
export function catalogCards(products, offers) {
  return products.flatMap(product => {
    const variants = offers.filter(offer => offer.product_id === product.id);
    return variants.length ? variants.map(offer => ({...product, cardKey:offer.id, cardOffer:offer, cardName:offer.form || product.name})) : [{...product, cardKey:product.id, cardName:product.name}];
  });
}

export function linkedIbiagSpecs(offer, specs) {
  return specs.filter(spec => (offer?.spec_ids || []).includes(spec.id) && !spec.deleted_at && spec.ibiag_file_path);
}
