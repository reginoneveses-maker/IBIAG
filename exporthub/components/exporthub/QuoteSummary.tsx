'use client';
import type {Quote} from '@/types/commercial';

const money=(value:number,currency:string)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency}).format(value);
const percent=(value:number)=>value.toLocaleString('pt-BR',{maximumFractionDigits:4})+'%';

function priceModelLabel(quote:Quote){
 const m=quote.pricingModel;
 if(!m)return 'Fórmula direta anterior (cotação criada antes da unificação com a planilha IBIAG)';
 return `Planilha IBIAG · indiretos ${percent(m.indirectRate*100)} · margem ${percent(m.marginPct)} · tributos sobre o preço ${percent(m.taxRate*100)} · comissões ${percent(m.feeRate*100)}`;
}

/** Cotação salva em modo leitura: mostra o que foi gravado, sem recalcular com a fórmula atual. */
export default function QuoteSummary({quote,onClose}:{quote:Quote;onClose:()=>void}){
 const l=quote.logistics,route=l?.routes[0];
 const rows:[string,string][]=[
  ['Produto',quote.product],['Fornecedor',quote.supplier],['Cliente',quote.customer||'—'],
  ['Condição de entrega',quote.incoterm+(l?.namedPlace?' · '+l.namedPlace:'')],
  ['Quantidade',quote.quantity.toLocaleString('pt-BR')+' kg'],
  ['Custo do produto',money(quote.costPerKg,'BRL')+' / kg'],
  ['Câmbio',quote.currency==='BRL'?'—':`R$ ${quote.rate.toLocaleString('pt-BR')} por ${quote.currency}`],
  ['Frete',money(quote.freight,'BRL')],['Seguro',money(quote.insurance,'BRL')],['Documentos e despacho',money(quote.documents,'BRL')],['Outros custos',money(quote.other,'BRL')],
  ['Margem',percent(quote.margin)],['Comissões e despesas',percent(quote.fees)],
  ['Tributos selecionados',(quote.taxes||[]).filter(t=>t.enabled).map(t=>t.name+(t.mode==='fixed'?' (valor fixo)':' '+percent(t.rate))).join(' · ')||'Nenhum'],
  ['Modelo de preço',priceModelLabel(quote)],
 ];
 if(l?.packaging)rows.push(['Embalagem',l.packaging.name+' · '+(l.paletized?'paletizado':'sem pallet')]);
 if(l)rows.push(['Destino de referência',l.destinationAddress||'—']);
 if(route)rows.push(['Frete baseado em',`${route.provider} · ref. ${route.reference} · validade ${route.validUntil}`]);
 return <section className="surface" aria-label="Cotação salva">
  <div className="section-title"><div><h2>Cotação salva · {quote.id}</h2><p>Somente leitura: valores gravados no momento da cotação, sem recálculo. Para uma nova versão, gere outra cotação no precificador ou no assistente.</p></div><button className="btn" onClick={onClose}>Voltar ao precificador</button></div>
  <div className="price-result"><span className="eyebrow">PREÇO GRAVADO</span><div className="unit-price">{money(quote.unitPrice,quote.currency)}<small>por kg · {quote.incoterm}</small></div><div className="total-price"><span>Valor total</span><strong>{money(quote.total,quote.currency)}</strong></div></div>
  <dl className="price-breakdown">{rows.map(([label,value])=><div key={label} style={{display:'contents'}}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
 </section>;
}
