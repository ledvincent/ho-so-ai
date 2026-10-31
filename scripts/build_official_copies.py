"""Materialize inspected appendix ranges and exact procedure attachment matches."""
import json
import sys
import unicodedata
from pathlib import Path
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.config import ROOT
from api.documents import store_document


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFD',value.casefold()) if c.isalnum())


# One-based PDF pages, including continuation pages and instructions.
SPECS = [
    ('CT01','CT01',None,'CT01','Tờ khai thay đổi thông tin cư trú','blank_form'),
    ('CT02-bundle','CT02',[3,4,5],'CT02','Tờ khai thay đổi thông tin cư trú dùng cho công dân Việt Nam định cư ở nước ngoài','blank_form'),
    ('marriage-declaration','marriage-declaration',None,'TKngkkthn','Tờ khai đăng ký kết hôn','blank_form'),
    ('marriage-electronic','marriage-electronic',None,'DDTTT','Nội dung mẫu hộ tịch điện tử tương tác đăng ký kết hôn','electronic_specification'),
    ('marital-status-declaration','marital-status-declaration',None,'TKcpGiyXNTTHN','Tờ khai cấp Giấy xác nhận tình trạng hôn nhân','blank_form'),
    ('marital-status-electronic','marital-status-electronic',None,'DTTT-CpgiyXNTThnnhn','Nội dung mẫu điện tử tương tác yêu cầu cấp Giấy xác nhận tình trạng hôn nhân','electronic_specification'),
    ('civil-extract-declaration','civil-extract-declaration',None,'TKyeucaubansaotrichluchotich','Tờ khai đề nghị cấp bản sao trích lục hộ tịch','blank_form'),
    ('civil-extract-electronic','civil-extract-electronic',None,'DTTT-CpBSkhaisinhTrchlcHT','Nội dung mẫu điện tử tương tác yêu cầu cấp bản sao Giấy khai sinh, bản sao Trích lục hộ tịch','electronic_specification'),
    ('LLTP-01','LLTP-01',None,'Mau_so_1','Tờ khai yêu cầu cấp Phiếu lý lịch tư pháp dành cho cá nhân','blank_form'),
    ('LLTP-02','LLTP-02',None,'Mau_so_2','Tờ khai yêu cầu cấp Phiếu lý lịch tư pháp dành cho người được ủy quyền hoặc cha mẹ của người chưa thành niên','blank_form'),
    ('LLTP-04','LLTP-04',None,'Mau_so_4','Tờ khai yêu cầu cấp Phiếu lý lịch tư pháp điện tử tương tác dành cho cá nhân','electronic_specification'),
    ('LLTP-05','LLTP-05',None,'Mau_so_5','Tờ khai yêu cầu cấp Phiếu lý lịch tư pháp điện tử tương tác dành cho người được ủy quyền hoặc cha mẹ','electronic_specification'),
    ('driving-exchange-XII','driving-exchange-XII',[122],'PhulucXII','Đề nghị đổi (cấp lại) giấy phép lái xe','blank_form'),
    ('passport-bundle','TK01',[6],'TK01 to','Tờ khai đề nghị cấp hộ chiếu phổ thông ở trong nước dành cho người từ 14 tuổi trở lên','blank_form'),
    ('passport-bundle','TK01a',[7],'TK01a to','Tờ khai đề nghị cấp hộ chiếu phổ thông ở trong nước dành cho người chưa đủ 14 tuổi','blank_form'),
    ('unemployment-text-bundle','unemployment-10',[25],'Mus10','Đề nghị hưởng trợ cấp thất nghiệp','blank_form'),
    ('unemployment-text-bundle','unemployment-11',[26],'Mus11','Đề nghị không hưởng trợ cấp thất nghiệp','blank_form'),
    ('DC02-bundle','DC02',[18,19],'DC02','Phiếu đề nghị giải quyết thủ tục về căn cước','blank_form'),
    ('BHYT-bundle','BHYT-01-TK',[1,2,3,4],'01-TK','Tờ khai đăng ký đóng, cấp thẻ bảo hiểm y tế trên Cổng dịch vụ công','electronic_specification'),
    ('BHYT-bundle','D03-TS',[5,6,7,8],'D03-TS','Danh sách người chỉ tham gia bảo hiểm y tế và hướng dẫn lập','blank_form'),
    ('BHYT-bundle','BHYT-Mau-2',[9],'so 2','Danh sách đối tượng tham gia bảo hiểm y tế','blank_form'),
    ('BHYT-bundle','C66a-HD',[12,13],'C66a-HD','Giấy thanh toán thù lao cho tổ chức làm đại lý và hướng dẫn lập','blank_form'),
    ('TK1-TS','TK1-TS',None,'TK1-TS','Tờ khai tham gia, điều chỉnh thông tin bảo hiểm xã hội, bảo hiểm y tế và hướng dẫn','blank_form'),
    ('BHYT-appendix-03','BHYT-appendix-03',None,'Phụ lục 03','Các loại giấy tờ làm căn cứ để cấp lại, ghi, điều chỉnh thẻ bảo hiểm y tế','supporting_guidance'),
    ('HKD-signed-bundle','HKD-III-1',[10,11,12],'Mauso1','Giấy đề nghị đăng ký hộ kinh doanh','blank_form'),
    ('birth-gazette-bundle','birth-linked-01',[26,27,28],'To khai','Tờ khai điện tử liên thông đăng ký khai sinh, đăng ký thường trú và cấp thẻ bảo hiểm y tế cho trẻ em dưới 6 tuổi','electronic_specification'),
    ('vehicle-bundle','DKX12',[63,64],'4.','Giấy khai đăng ký xe','blank_form'),
    ('vehicle-bundle','DKX13',[65],'5.','Giấy khai thu hồi đăng ký, biển số xe','blank_form'),
]


def main():
    candidates=json.loads((ROOT/'data/forms/recovery.json').read_text(encoding='utf-8'))
    copies=[]
    for source_family,family,pages,label,summary,kind in SPECS:
        source=next(x for x in candidates if x['family']==source_family)
        item={k:source.get(k) for k in ('page_url','download_url','revision')}
        original=source['record']
        pdf=source.get('pdf_path') or original['raw_path']
        if pages:
            with pymupdf.open(ROOT/pdf) as out:
                out.select([n-1 for n in pages])
                # Page extraction retains appearance; never claim the excerpt is the signed original.
                record=store_document(out.tobytes(no_new_id=True,garbage=4,deflate=True),'',family+'.pdf')
            record.update(url=original['url'],fetched_at=original['fetched_at'])
            item.update(record=record,pdf_path=record['raw_path'],derivation=dict(
                method='pdf_page_extraction',pages=pages,original_sha256=original['sha256'],
                original_path=original['raw_path'],source_pdf_path=pdf))
        else:
            item.update(record=original,pdf_path=pdf,derivation=None)
        item.update(family=family,summary=summary,document_kind=kind,matches=[],
                    matching_basis='Inspected official document title/code and cited edition against the captured procedure requirements; alternate bytes are not claimed identical to the unavailable primary download.',
                    currency_note='Recovered source edition. Current legal applicability and field mapping are not approved.')
        if family=='HKD-III-1':
            item['currency_note']='2023 form matches the captured procedure legal basis, but the primary attachment is named Mẫu số 1. Exact requested revision remains ambiguous; do not present as a verified replacement.'
            item['candidate_only']=True
        for code in source['procedure_codes']:
            p=json.loads((ROOT/'data/procedures'/code/'procedure.json').read_text(encoding='utf-8'))
            for form in p['forms']:
                if normalized(label) in normalized(form['label']):
                    item['matches'].append(dict(procedure_code=code,source_url=form['source_url'],label=form['label']))
        if not item['matches']:raise ValueError('No target attachment: '+family)
        copies.append(item)
    (ROOT/'data/forms/official-copies.json').write_text(json.dumps(copies,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(len(copies),'forms;',sum(len(x['matches']) for x in copies),'attachment associations')


if __name__=='__main__':main()
