import base from './products.json';
import definitions from './product-variants.json';
import imageDefinitions from './product-photos.json';
type Variant={id:string;name:string;variantLabel:string;forms:string[];categories:string[]};
export type CatalogProduct=typeof base[number]&{parentId:string;legacyGroup:boolean;variantLabel:string;portugueseName:string};
const groups=definitions as Record<string,Variant[]>;
const sharedFormGroups=new Set(['IBIAG-003','IBIAG-006','IBIAG-007','IBIAG-028','IBIAG-029']);
const photos=imageDefinitions as Record<string,CatalogProduct['image']>;
export const legacyProducts:CatalogProduct[]=base.map(p=>({...p,portugueseName:p.name,name:p.originalName,image:Object.prototype.hasOwnProperty.call(photos,p.id)?photos[p.id]:p.image,parentId:'',legacyGroup:!!groups[p.id],variantLabel:''}));
const expandedProducts:CatalogProduct[]=legacyProducts.flatMap(parent=>groups[parent.id]?.map(v=>({...parent,...v,portugueseName:v.name,name:parent.originalName,parentId:parent.id,legacyGroup:false,originalName:parent.originalName,image:Object.prototype.hasOwnProperty.call(photos,v.id)?photos[v.id]:(sharedFormGroups.has(parent.id)?parent.image:null)}))??[parent]);
// Removed from the active catalog at the owner's request; keep its identifier for existing records.
const products=expandedProducts.filter(p=>p.id!=='IBIAG-009');
export const allProducts:CatalogProduct[]=[...legacyProducts.filter(p=>p.legacyGroup),...expandedProducts];
export default products;
