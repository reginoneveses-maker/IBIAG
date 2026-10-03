import React from 'react';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import Precos from './Precos';
import {api} from '@/AuthContext';
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
