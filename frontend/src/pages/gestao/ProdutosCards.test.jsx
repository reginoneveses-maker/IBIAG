import React from 'react';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import Produtos from './Produtos';
import {api} from '@/AuthContext';
import {downloadDocument,documentPreview} from '@/lib/api';
jest.mock('@/AuthContext',()=>({api:{get:jest.fn()}}));
jest.mock('@/lib/api',()=>({downloadDocument:jest.fn(),documentPreview:jest.fn()}));

test('card downloads and previews linked IBIAG version, with both sending integrations disabled',async()=>{
  const branded='ibiag.pdf';
  const data={
    '/products':[{id:'p',name:'Açaí Pulp',certifications:[]}],
    '/product-offers':[{id:'o',product_id:'p',form:'Açaí Pulp 12%',spec_ids:['s'],supplier_name:'Nossa Fruta'}],
    '/specs':[{id:'s',product_name:'Açaí Pulp 12%',version:'1',original_file_path:'original.pdf',ibiag_file_path:branded,ibiag_file_name:'IBIAG.pdf'}]
  };
  api.get.mockImplementation(path=>Promise.resolve({data:data[path]||[]}));
  documentPreview.mockResolvedValue({kind:'pdf',url:'blob:test'});
  downloadDocument.mockResolvedValue();
  URL.revokeObjectURL=jest.fn();
  render(<MemoryRouter><Produtos/></MemoryRouter>);
  await screen.findByRole('heading',{name:'Açaí Pulp 12%'});
  expect(screen.getByRole('button',{name:/Enviar por e-mail/}).disabled).toBe(true);
  expect(screen.getByRole('button',{name:/Enviar por WhatsApp/}).disabled).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'Baixar PDF'}));
  await waitFor(()=>expect(downloadDocument).toHaveBeenCalledWith({file_path:branded,file_name:'IBIAG.pdf'}));
  fireEvent.click(screen.getByRole('button',{name:'Visualizar ficha IBIAG'}));
  await screen.findByRole('dialog',{name:'Visualização da ficha'});
  expect(api.get).toHaveBeenCalledWith('/files/ibiag.pdf',{responseType:'blob'});
  expect(api.get).not.toHaveBeenCalledWith('/files/original.pdf',expect.anything());
  fireEvent.click(screen.getByRole('button',{name:'Fechar ficha'}));
  expect(screen.queryByRole('dialog',{name:'Visualização da ficha'})).toBeNull();
});
