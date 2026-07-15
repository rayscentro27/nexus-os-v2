#!/usr/bin/env python3
"""Create deterministic, parser-shaped synthetic three-bureau PDFs without PII."""
from pathlib import Path
import argparse

ROOT=Path(__file__).resolve().parents[2]
def lines(kind,followup=False):
    if kind=='a':
      a_balance='1300' if followup else '1200';a_status='Current' if followup else 'Past Due'
      rows=['Bank Of America - Experian account ****4412 balance $1200 status: Current; opened: 01/01/2020 credit limit $5000','Bank of Amer - Equifax account ****4412 balance $1450 status: Current; opened: 01/01/2020 credit limit $5000',f'B Of A - TransUnion account ****4412 balance ${a_balance} status: {a_status}; opened: 01/01/2020 credit limit $5000','Stable Synthetic Card - Experian account ****7711 balance $100 status: Current; opened: 03/01/2019 credit limit $1000']
      if not followup: rows.insert(3,'Bank Of America - Experian account ****8821 balance $500 status: Current; opened: 02/01/2018 credit limit $3000')
      return ['Synthetic Credit File']+rows
    if kind=='b': return ['Synthetic Credit File','Similar Bank - Experian account ****1111 balance $200 status: Current opened: 01/01/2018','Similar Bank - Equifax account ****9999 balance $220 status: Current opened: 02/01/2022']
    return ['Synthetic Credit File','Original Synthetic Creditor - Experian account ****4433 balance $800 status: Collection; ownership: Original Creditor; opened: 01/01/2019','Synthetic Debt Purchaser - Equifax account ****4433 balance $800 status: Collection; ownership: Purchaser; original creditor: Original Synthetic Creditor; opened: 01/01/2019']
def make_pdf(text_lines):
    commands=['BT','/F1 10 Tf']
    for index,line in enumerate(text_lines):
        safe=line.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
        commands.extend([f'1 0 0 1 36 {760-index*16} Tm',f'({safe}) Tj'])
    stream=('\n'.join(commands)+'\nET\n').encode()
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'endstream',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    out=b'%PDF-1.4\n'; offsets=[0]
    for index,obj in enumerate(objects,1): offsets.append(len(out)); out+=f'{index} 0 obj\n'.encode()+obj+b'\nendobj\n'
    start=len(out); out+=f'xref\n0 {len(objects)+1}\n'.encode()+b'0000000000 65535 f \n'+b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])+f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode()
    return out
def main():
 p=argparse.ArgumentParser();p.add_argument('--persona',choices='abc',default='a');p.add_argument('--follow-up',action='store_true');p.add_argument('--out',type=Path,default=ROOT/'data/runtime/authenticated_credit_fixtures');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);path=a.out/f'synthetic_persona_{a.persona}_{"followup" if a.follow_up else "initial"}.pdf';path.write_bytes(make_pdf(lines(a.persona,a.follow_up)));print(path)
if __name__=='__main__':main()
