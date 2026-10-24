import {operationalDay} from './operationalDay';
test('keeps the Fortaleza day during the first three UTC hours',()=>{
 expect(operationalDay(new Date('2026-10-24T00:00:00Z'))).toBe('2026-10-23');
 expect(operationalDay(new Date('2026-10-24T02:59:59Z'))).toBe('2026-10-23');
});
test('advances only at Fortaleza midnight',()=>{
 expect(operationalDay(new Date('2026-10-24T03:00:00Z'))).toBe('2026-10-24');
});
test('uses the same business day for an equivalent instant in another locale',()=>{
 expect(operationalDay(new Date('2026-10-24T10:00:00+09:00'))).toBe('2026-10-23');
});
