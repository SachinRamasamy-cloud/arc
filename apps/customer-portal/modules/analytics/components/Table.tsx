import React,{useState} from 'react';
import {useReactTable,getCoreRowModel,getSortedRowModel,flexRender,type ColumnDef,type SortingState} from '@tanstack/react-table';
import {ArrowUpDown} from 'lucide-react';
export function Table({data,columns}:{data:any[];columns:ColumnDef<any,any>[]}){
 const[sorting,setSorting]=useState<SortingState>([]);
 const table=useReactTable({data,columns,state:{sorting},onSortingChange:setSorting,getCoreRowModel:getCoreRowModel(),getSortedRowModel:getSortedRowModel()});
 return <div className="table-scroll"><table><thead>{table.getHeaderGroups().map(group=><tr key={group.id}>{group.headers.map(header=><th key={header.id}>{header.isPlaceholder?null:header.column.getCanSort()?<button className="table-sort" onClick={header.column.getToggleSortingHandler()}>{flexRender(header.column.columnDef.header,header.getContext())}<ArrowUpDown size={11}/></button>:flexRender(header.column.columnDef.header,header.getContext())}</th>)}</tr>)}</thead><tbody>{table.getRowModel().rows.map(row=><tr key={row.id}>{row.getVisibleCells().map(cell=><td key={cell.id}>{flexRender(cell.column.columnDef.cell,cell.getContext())}</td>)}</tr>)}</tbody></table></div>
}
export function DataTable({data,columns,empty='No records yet.'}:{data:any[];columns:ColumnDef<any,any>[];empty?:string}){return data.length?<Table data={data} columns={columns}/>:<div className="table-empty">{empty}</div>}
