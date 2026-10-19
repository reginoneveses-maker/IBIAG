import React from 'react';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import Precos from './Precos';
import {MemoryRouter} from 'react-router-dom';
import {api} from '@/AuthContext';
import {toast} from 'sonner';
jest.mock('@/AuthContext',()=>({api:{get:jest.fn(),post:jest.fn(),put:jest.fn(),delete:jest.fn()}}));
jest.mock('sonner',()=>({toast:{success:jest.fn(),error:jest.fn()}}));
jest.mock('@/components/ui/dialog',()=>({Dialog:({open,children})=>open?<div>{children}</div>:null,DialogContent:({children})=><div>{children}</div>,DialogHeader:({children})=><div>{children}</div>,DialogTitle:({children})=><h2>{children}</h2>,DialogFooter:({children})=><div>{children}</div>}));
afterEach(cleanup);beforeEach(()=>jest.clearAllMocks());
test('saving an existing calculation preserves quantity and removes the last extra/tax instead of reviving legacy flat values',async()=>{
 const saved={id:'old',product_name:'Açaí',supplier_id:'s',supplier_name:'Bona Fruit',quantity:1000,unit:'kg',supplier_price:17.5,extras:[],extra_costs:2,taxes:[],taxes_pct:6,margin_pct:15,margin_mode:'margin',currency:'BRL',exchange_rate:5.2,sell_price_brl:25,sell_price_usd:5};
 api.get.mockImplementation(path=>Promise.resolve({data:path==='/prices'?[saved]:path==='/suppliers'?[{id:'s',name:'Bona Fruit'}]:[]}));api.put.mockResolvedValue({data:{}});
 render(<Precos/>);fireEvent.click(await screen.findByTestId('edit-price-old'));
 expect(screen.getByLabelText('Quantidade').value).toBe('1000');
 fireEvent.click(screen.getByRole('button',{name:'Remover custo Custos adicionais cadastrados'}));fireEvent.click(screen.getByRole('button',{name:'Remover imposto Impostos cadastrados'}));
 fireEvent.change(screen.getByLabelText('Preço do fornecedor por unidade'),{target:{value:'17,50'}});
 fireEvent.click(screen.getByTestId('save-price-button'));
 await waitFor(()=>expect(api.put).toHaveBeenCalledWith('/prices/old',expect.objectContaining({quantity:1000,supplier_price:17.5,extras:[],extra_costs:0,taxes:[],taxes_pct:0})));
});

test('only a usable saved calculation offers explicit draft creation without writes',async()=>{
 const common={product_name:'Product',supplier_name:'Supplier',quantity:1000,unit:'kg',supplier_price:17.5,taxes_pct:0,margin_pct:15,sell_price_brl:22,sell_price_usd:4.26};
 const rows=[{...common,id:'valid',offer_id:'offer'},{...common,id:'manual'},{...common,id:'bad',offer_id:'offer',calculation_error:'Review'}];
 api.get.mockImplementation(path=>Promise.resolve({data:path==='/prices'?rows:[]}));
 render(<MemoryRouter><Precos/></MemoryRouter>);
 const link=await screen.findByTestId('price-order-valid');
 expect(link.getAttribute('href')).toBe('/prospects/orders?price=valid');
 expect(screen.queryByTestId('price-order-manual')).toBeNull();expect(screen.queryByTestId('price-order-bad')).toBeNull();
 expect(api.post).not.toHaveBeenCalled();expect(api.put).not.toHaveBeenCalled();
});

test('a referenced calculation cannot be deleted and the table remains visible',async()=>{
 const row={id:'used',product_name:'Product',quantity:1000,unit:'kg',supplier_price:17.5,taxes_pct:0,margin_pct:15,sell_price_brl:22,sell_price_usd:4.26};
 api.get.mockImplementation(path=>Promise.resolve({data:path==='/prices'?[row]:[]}));
 api.delete.mockRejectedValue({response:{status:409,data:{detail:'Cálculo vinculado a pedido não pode ser excluído.'}}});
 render(<MemoryRouter><Precos/></MemoryRouter>);
 fireEvent.click(await screen.findByTestId('delete-price-used'));
 await waitFor(()=>expect(toast.error).toHaveBeenCalledWith('Cálculo vinculado a pedido não pode ser excluído.'));
 expect(screen.getByTestId('price-row-used')).toBeTruthy();
});
