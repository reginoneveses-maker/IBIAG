// Intentionally empty by default.
// Add Drizzle tables here when the site actually needs a database.
// See examples/d1/db/schema.ts for an opt-in example.
import {sqliteTable,text,integer,primaryKey,check,index} from 'drizzle-orm/sqlite-core';
import {sql} from 'drizzle-orm';
export const collections=sqliteTable('collections',{name:text('name').primaryKey(),payload:text('payload').notNull(),revision:integer('revision').notNull().default(0),updatedAt:text('updated_at').notNull(),updatedBy:text('updated_by').notNull()});
export const specs=sqliteTable('specs',{id:text('id').primaryKey(),productId:text('product_id').notNull(),kind:text('kind').notNull(),supplier:text('supplier').notNull(),filename:text('filename').notNull(),size:integer('size').notNull(),createdAt:text('created_at').notNull(),createdBy:text('created_by').notNull()});
export const crmFiles=sqliteTable('crm_files',{id:text('id').primaryKey(),opportunityId:text('opportunity_id').notNull(),filename:text('filename').notNull(),size:integer('size').notNull(),createdAt:text('created_at').notNull(),createdBy:text('created_by').notNull()},table=>[index('idx_crm_files_opportunity').on(table.opportunityId)]);
export const collectionChunks=sqliteTable('collection_chunks',{batchId:text('batch_id').notNull(),ordinal:integer('ordinal').notNull(),content:text('content').notNull()},table=>[primaryKey({columns:[table.batchId,table.ordinal]})]);
export const writeGuards=sqliteTable('write_guards',{id:text('id').primaryKey(),valid:integer('valid').notNull()},table=>[check('write_revision_guard',sql`${table.valid} = 1`)]);

export const sectorFiles=sqliteTable('sector_files',{id:text('id').primaryKey(),recordId:text('record_id').notNull(),filename:text('filename').notNull(),size:integer('size').notNull(),createdAt:text('created_at').notNull(),createdBy:text('created_by').notNull()},table=>[index('idx_sector_files_record').on(table.recordId)]);
export const auditEvents=sqliteTable('audit_events',{id:text('id').primaryKey(),at:text('at').notNull(),userId:text('user_id').notNull(),actor:text('actor').notNull(),action:text('action').notNull(),resourceType:text('resource_type').notNull(),resourceId:text('resource_id').notNull()},table=>[index('idx_audit_events_at').on(table.at)]);

export const workspaceMembers=sqliteTable('workspace_members',{userId:text('user_id').primaryKey(),email:text('email').notNull().unique(),role:text('role').notNull(),createdAt:text('created_at').notNull()});
