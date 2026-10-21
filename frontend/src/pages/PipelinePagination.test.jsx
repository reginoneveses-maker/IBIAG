import React from 'react';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import Pipeline from './Pipeline';
import {api,useAuth} from '@/AuthContext';
jest.mock('@/AuthContext',()=>({api:{get:jest.fn()},useAuth:jest.fn()}));
jest.mock('@/i18n',()=>({useLang:()=>({t:key=>key})}));

test('sorts all fetched leads A-Z, paginates 15 at a time and resets on search',async()=>{
  useAuth.mockReturnValue({user:{role:'user'}});
  const leads=Array.from({length:31},(_,i)=>({id:String(i),company:`Company ${String(i).padStart(2,'0')}`,stage:'new_lead',industry:'beverage'})).reverse();
  api.get.mockResolvedValue({data:leads});
  render(<MemoryRouter><Pipeline/></MemoryRouter>);
  await screen.findByTestId('lead-card-0');
  expect(screen.getAllByTestId(/^lead-card-/)).toHaveLength(15);
  expect(screen.queryByTestId('lead-card-15')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Próxima página'}));
  expect(screen.getByTestId('lead-card-15')).toBeTruthy();
  expect(screen.queryByTestId('lead-card-0')).toBeNull();
  fireEvent.change(screen.getByTestId('search-leads-input'),{target:{value:'Company 30'}});
  await waitFor(()=>expect(screen.getByTestId('lead-card-30')).toBeTruthy());
  expect(screen.getAllByTestId(/^lead-card-/)).toHaveLength(1);
  expect(screen.getByLabelText('Página dos leads').value).toBe('1');
  fireEvent.change(screen.getByTestId('search-leads-input'),{target:{value:''}});
  fireEvent.change(screen.getByLabelText('Leads por página'),{target:{value:'50'}});
  await waitFor(()=>expect(screen.getAllByTestId(/^lead-card-/)).toHaveLength(31));
});
