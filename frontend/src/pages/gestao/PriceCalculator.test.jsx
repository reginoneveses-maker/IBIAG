import React,{useState} from 'react';
import {render,screen,fireEvent,waitFor,cleanup,act} from '@testing-library/react';
import {PriceCalculator} from './PriceCalculator';
import {api} from '@/AuthContext';
jest.mock('@/AuthContext',()=>({api:{get:jest.fn()}}));
const suppliers=[{id:'s1',name:'Bona Fruit'},{id:'s2',name:'Outro fornecedor'}];
const offers=[{id:'o1',supplier_id:'s1',product_id:'p1',product_name:'Açaí liofilizado',unit:'kg',active:true},{id:'o2',supplier_id:'s2',product_id:'p2',product_name:'Manga',unit:'L',active:true}];
const initial={product_name:'',supplier_id:'',unit:'kg',quantity:1,supplier_price:0,extras:[],taxes:[{pct:6,name:'Taxa'}],margin_pct:15,margin_mode:'margin',currency:'BRL',exchange_rate:'5,2'};
function Host(){const [form,setForm]=useState(initial);return <PriceCalculator form={form} setForm={setForm} suppliers={suppliers}/>;}
afterEach(cleanup);beforeEach(()=>jest.clearAllMocks());
test('supplier selection limits products, clears the old price and multiplies comma-decimal prices',async()=>{
 api.get.mockImplementation((url,{params})=>Promise.resolve({data:offers.filter(o=>o.supplier_id===params.supplier_id)}));
 render(<Host/>);expect(screen.getByLabelText('Produto do fornecedor').disabled).toBe(true);
 fireEvent.change(screen.getByLabelText('Fornecedor'),{target:{value:'s1'}});
 await screen.findByRole('option',{name:'Açaí liofilizado'});expect(screen.queryByRole('option',{name:'Manga'})).toBeNull();
 fireEvent.change(screen.getByLabelText('Produto do fornecedor'),{target:{value:'o1'}});
 fireEvent.change(screen.getByLabelText('Quantidade'),{target:{value:'1000'}});
 fireEvent.change(screen.getByLabelText('Preço do fornecedor por unidade'),{target:{value:'17,50'}});
 expect(screen.getByTestId('price-supplier-total').textContent).toContain('17.500,00');expect(screen.getByTestId('price-sale-total').textContent).toContain('22.151,90');
 expect(screen.getByLabelText('Unidade').value).toBe('kg');expect(screen.getByLabelText('Unidade').disabled).toBe(true);
 fireEvent.change(screen.getByLabelText('Fornecedor'),{target:{value:'s2'}});
 await screen.findByRole('option',{name:'Manga'});expect(screen.queryByRole('option',{name:'Açaí liofilizado'})).toBeNull();
 expect(screen.getByLabelText('Produto do fornecedor').value).toBe('');expect(screen.getByLabelText('Preço do fornecedor por unidade').value).toBe('0');
 fireEvent.change(screen.getByLabelText('Produto do fornecedor'),{target:{value:'o2'}});expect(screen.getByLabelText('Unidade').value).toBe('L');
});
test('a slow previous supplier response cannot replace the new supplier products',async()=>{
 let resolveFirst;api.get.mockImplementation((url,{params})=>params.supplier_id==='s1'?new Promise(r=>{resolveFirst=r;}):Promise.resolve({data:[offers[1]]}));
 render(<Host/>);fireEvent.change(screen.getByLabelText('Fornecedor'),{target:{value:'s1'}});fireEvent.change(screen.getByLabelText('Fornecedor'),{target:{value:'s2'}});
 await screen.findByRole('option',{name:'Manga'});await act(async()=>resolveFirst({data:[offers[0]]}));
 expect(screen.queryByRole('option',{name:'Açaí liofilizado'})).toBeNull();expect(screen.getByRole('option',{name:'Manga'})).toBeTruthy();
});
test('offer loading failure has a retry and empty offers do not show another supplier',async()=>{
 api.get.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({data:[]});render(<Host/>);
 fireEvent.change(screen.getByLabelText('Fornecedor'),{target:{value:'s1'}});await screen.findByRole('button',{name:'Tentar novamente'});
 fireEvent.click(screen.getByRole('button',{name:'Tentar novamente'}));await screen.findByText(/não tem ofertas ativas/);expect(screen.getByLabelText('Produto do fornecedor').disabled).toBe(true);
});
