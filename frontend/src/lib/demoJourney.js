import {computePrice,priceNumber} from './pricing';
export const journeySteps=[
 {id:'crm',title:'Empresa e contatos',to:'/prospects/pipeline',text:'Confira país, contato e responsável. Use a mesma empresa durante toda a negociação.'},
 {id:'supplier',title:'Fornecedor e oferta',to:'/gestao/fornecedores',text:'Confira fornecedor, produto, moeda, unidade, preço e pedido mínimo. Preserve as fichas e certificados vinculados.'},
 {id:'product',title:'Produto e documentos',to:'/gestao/produtos',text:'Escolha a oferta correta do produto. Confira versão da ficha, embalagem e validade do certificado.'},
 {id:'price',title:'Calcular e salvar',to:'/gestao/precos',text:'Selecione fornecedor e produto. Confira kg × preço/kg, custos, tributos, câmbio e margem. Salve o cálculo.'},
 {id:'quote',title:'Cotação',to:'/gestao/cotacoes',text:'No cálculo salvo, use Criar cotação. Vincule a empresa, confira condições e validade e aprove internamente.'},
 {id:'order',title:'Pedido',to:'/gestao/pedidos',text:'Converta a cotação aprovada em pedido uma única vez. Confira quantidade, moeda e revisão de origem.'},
 {id:'invoice',title:'Commercial Invoice',to:'/gestao/invoices-comerciais',text:'Crie a partir do pedido. Confira comprador, produto, valores e revisão. Visualize o PDF antes da aprovação.'},
 {id:'packing',title:'Packing List',to:'/gestao/packing-lists',text:'Crie a partir do mesmo pedido. Confira volumes, peso líquido/bruto e embalagem; não confunda o peso com o valor comercial.'},
 {id:'shipment',title:'Embarque',to:'/gestao/embarques',text:'Registre o embarque manual a partir do pedido revisado. Confira transportador, destino, datas e documentos.'},
 {id:'dossier',title:'Conferência final',to:'/gestao/operacao',text:'Abra o dossiê pelo pedido para conferir cotação, Invoice, Packing List e embarque. Alterações de origem exigem revisão documental.'}
];
export function demoCalculation(quantity='1000',supplierPrice='87,50'){
 const result=computePrice({supplier_price:supplierPrice,quantity,extras:[{name:'Custos FCA por kg (fictícios)',value:12.5}],taxes:[],margin_pct:20,margin_mode:'margin',currency:'USD',exchange_rate:5});
 const kg=priceNumber(quantity,true),bags=Math.ceil(kg/25),gross=Number((kg+bags*0.2).toFixed(2));
 return {...result,bags,gross,net:kg,unitUsd:result.priceUsd,totalUsd:result.saleTotalUsd};
}
