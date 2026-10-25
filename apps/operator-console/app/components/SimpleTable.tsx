import React from "react";
export function SimpleTable({headings,rows}:{headings:string[];rows:React.ReactNode[][]}){return rows.length?<div className="table-scroll"><table><thead><tr>{headings.map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{rows.map((row,i)=><tr key={i}>{row.map((v,j)=><td key={j}>{v}</td>)}</tr>)}</tbody></table></div>:<div className="table-empty">No records.</div>}

